#!/usr/bin/env python3
"""
bedrock_simulator.py — a runnable, offline simulation of the Amazon Bedrock
Converse API loop.

WHY THIS EXISTS
---------------
You cannot learn an API's *shape* from prose, and you should not need an AWS
account (or a credit card) to learn it. This file implements a fake
`bedrock-runtime` client whose request validation and response envelopes match
what the real service returns, then drives it through the five things that
actually bite you in production:

    1. A plain Converse call                      -> stopReason "end_turn"
    2. A full tool-use round trip                 -> stopReason "tool_use"
    3. ConverseStream event ordering              -> messageStart .. metadata
    4. ThrottlingException + backoff with jitter  -> the retry loop you must own
    5. Token + cost accounting                    -> including prompt caching

NOTHING HERE TALKS TO AWS. No credentials, no network, no boto3 required.
Every JSON shape is copied from the Amazon Bedrock User Guide (URLs in the
docstrings below). The *numbers* (token counts, prices) are invented for the
worked example and are clearly labelled as such.

Run:  python bedrock_simulator.py
"""

from __future__ import annotations

import json
import random
import sys
import textwrap
from dataclasses import dataclass
from typing import Any, Callable, Iterator

# Deterministic output so the teaching example reads the same every run.
RNG = random.Random(20260915)

WIDTH = 78


# ---------------------------------------------------------------------------
# Presentation helpers
# ---------------------------------------------------------------------------

def rule(title: str = "") -> None:
    if title:
        pad = WIDTH - len(title) - 3
        print(f"\n== {title} " + "=" * max(pad - 3, 0))
    else:
        print("=" * WIDTH)


def say(text: str) -> None:
    print(textwrap.fill(text, WIDTH))


def show_json(label: str, obj: Any) -> None:
    print(f"\n--- {label} " + "-" * max(WIDTH - len(label) - 5, 0))
    print(json.dumps(obj, indent=2))


# ---------------------------------------------------------------------------
# Exceptions that mirror botocore's ClientError surface
# ---------------------------------------------------------------------------

class FakeClientError(Exception):
    """Mirrors botocore.exceptions.ClientError closely enough to teach with.

    Real code inspects `err.response["Error"]["Code"]`. Bedrock's retryable
    codes and HTTP statuses (per the troubleshooting guide):
        ThrottlingException   429  account quota exceeded       -> retry
        ServiceUnavailable    503  transient capacity           -> retry
        overloaded_error      529  model overloaded             -> retry
        ModelNotReadyException 429 model warming                -> retry
        ValidationException   400  your request is wrong        -> DO NOT retry
        AccessDeniedException 403  IAM / model access           -> DO NOT retry
    https://docs.aws.amazon.com/bedrock/latest/userguide/troubleshooting-api-error-codes.html
    """

    RETRYABLE = {
        "ThrottlingException",
        "ServiceUnavailable",
        "overloaded_error",
        "ModelNotReadyException",
        "InternalFailure",
    }

    def __init__(self, code: str, message: str, status: int):
        super().__init__(f"{code}: {message}")
        self.response = {
            "Error": {"Code": code, "Message": message},
            "ResponseMetadata": {"HTTPStatusCode": status, "RequestId": "sim-0000"},
        }

    @property
    def code(self) -> str:
        return self.response["Error"]["Code"]

    @property
    def retryable(self) -> bool:
        return self.code in self.RETRYABLE


# ---------------------------------------------------------------------------
# Token + cost accounting
# ---------------------------------------------------------------------------

@dataclass
class Ledger:
    """Accumulates Converse `usage` blocks and prices them.

    Field names are the real ones from the TokenUsage shape:
        inputTokens, outputTokens, totalTokens,
        cacheReadInputTokens, cacheWriteInputTokens

    CRITICAL, AND EASY TO GET WRONG: when prompt caching is active, the docs
    state that `inputTokens` counts ONLY the non-cached input tokens. The true
    total is:
        inputTokens + cacheReadInputTokens + cacheWriteInputTokens
    https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html
    """

    # ILLUSTRATIVE RATES ONLY -- dollars per 1,000,000 tokens. These are NOT
    # real Bedrock prices and will be wrong by the time you read this. Always
    # price from https://aws.amazon.com/bedrock/pricing/
    input_per_mtok: float = 3.00
    output_per_mtok: float = 15.00
    cache_read_per_mtok: float = 0.30      # typically a large discount
    cache_write_per_mtok: float = 3.75     # typically a premium over input

    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    def record(self, usage: dict[str, int]) -> None:
        self.calls += 1
        self.input_tokens += usage.get("inputTokens", 0)
        self.output_tokens += usage.get("outputTokens", 0)
        self.cache_read_tokens += usage.get("cacheReadInputTokens", 0)
        self.cache_write_tokens += usage.get("cacheWriteInputTokens", 0)

    @property
    def billed_input_equivalent(self) -> int:
        return self.input_tokens + self.cache_read_tokens + self.cache_write_tokens

    def cost(self) -> float:
        return (
            self.input_tokens / 1e6 * self.input_per_mtok
            + self.output_tokens / 1e6 * self.output_per_mtok
            + self.cache_read_tokens / 1e6 * self.cache_read_per_mtok
            + self.cache_write_tokens / 1e6 * self.cache_write_per_mtok
        )

    def report(self) -> None:
        print(f"\n  calls                 : {self.calls}")
        print(f"  inputTokens (uncached): {self.input_tokens:>8,}")
        print(f"  cacheReadInputTokens  : {self.cache_read_tokens:>8,}")
        print(f"  cacheWriteInputTokens : {self.cache_write_tokens:>8,}")
        print(f"  outputTokens          : {self.output_tokens:>8,}")
        print(f"  true total input      : {self.billed_input_equivalent:>8,}"
              "   <- inputTokens + cacheRead + cacheWrite")
        print(f"  estimated cost        : ${self.cost():.6f}   "
              "(ILLUSTRATIVE RATES -- see aws.amazon.com/bedrock/pricing/)")


# ---------------------------------------------------------------------------
# The fake client
# ---------------------------------------------------------------------------

class FakeBedrockRuntime:
    """A stand-in for boto3.client("bedrock-runtime").

    Implements `converse` and `converse_stream` with the real request
    validation rules and the real response envelope:

        {"output": {"message": {...}},
         "stopReason": "...",
         "usage": {...},
         "metrics": {"latencyMs": N}}

    https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
    """

    def __init__(self, throttle_first_n: int = 0):
        self._throttles_remaining = throttle_first_n
        self._seen_system_prefix: str | None = None

    # -- validation ---------------------------------------------------------

    @staticmethod
    def _validate(model_id: str, messages: list[dict], **kw: Any) -> None:
        if not model_id:
            raise FakeClientError("ValidationException", "modelId is required", 400)
        if not messages:
            raise FakeClientError(
                "ValidationException", "messages must contain at least one entry", 400)
        for i, m in enumerate(messages):
            if m.get("role") not in ("user", "assistant"):
                raise FakeClientError(
                    "ValidationException",
                    f"messages[{i}].role must be 'user' or 'assistant'", 400)
            if not isinstance(m.get("content"), list):
                raise FakeClientError(
                    "ValidationException",
                    f"messages[{i}].content must be a list of ContentBlocks", 400)
        # The real service enforces this and the error is confusing the first
        # time you hit it: a toolResult must be sent back as a *user* message.
        for i, m in enumerate(messages):
            has_tool_result = any("toolResult" in b for b in m["content"])
            if has_tool_result and m["role"] != "user":
                raise FakeClientError(
                    "ValidationException",
                    f"messages[{i}]: toolResult blocks must be in a user message", 400)

    # -- converse -----------------------------------------------------------

    def converse(
        self,
        modelId: str,
        messages: list[dict],
        system: list[dict] | None = None,
        inferenceConfig: dict | None = None,
        toolConfig: dict | None = None,
        guardrailConfig: dict | None = None,
        **_: Any,
    ) -> dict:
        self._validate(modelId, messages)

        if self._throttles_remaining > 0:
            self._throttles_remaining -= 1
            raise FakeClientError(
                "ThrottlingException",
                "Too many requests, please wait before trying again.", 429)

        # --- prompt caching simulation ------------------------------------
        # A cachePoint block in `system` (or `tools`/`messages`) marks the end
        # of a cacheable prefix:  {"cachePoint": {"type": "default"}}
        # First call with a given prefix WRITES the cache; later identical
        # prefixes READ it.
        cache_read = cache_write = 0
        sys_blocks = system or []
        if any("cachePoint" in b for b in sys_blocks):
            prefix = json.dumps([b for b in sys_blocks if "cachePoint" not in b])
            prefix_tokens = 1_400  # invented, but above the 1,024 minimum
            if self._seen_system_prefix == prefix:
                cache_read = prefix_tokens
            else:
                self._seen_system_prefix = prefix
                cache_write = prefix_tokens

        last = messages[-1]
        wants_tool = (
            toolConfig is not None
            and not any("toolResult" in b for b in last["content"])
            and any("weather" in json.dumps(b).lower() for b in last["content"])
        )

        if guardrailConfig and self._blocked(messages):
            return self._guardrail_response(guardrailConfig)

        if wants_tool:
            return self._tool_use_response(toolConfig, cache_read, cache_write)

        return self._text_response(messages, inferenceConfig, cache_read, cache_write)

    # -- response builders --------------------------------------------------

    @staticmethod
    def _blocked(messages: list[dict]) -> bool:
        blob = json.dumps(messages).lower()
        return "wire me the routing number" in blob

    @staticmethod
    def _guardrail_response(guardrail_config: dict) -> dict:
        """stopReason 'guardrail_intervened' -- note usage is all zeros.

        The model was never invoked, so you pay for guardrail units, not for
        model tokens. The `trace` block appears only when trace is "enabled".
        https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-use-converse-api.html
        """
        resp = {
            "output": {"message": {"role": "assistant", "content": [
                {"text": "Sorry, I can't help with account transfer requests."}]}},
            "stopReason": "guardrail_intervened",
            "usage": {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0},
            "metrics": {"latencyMs": 318},
        }
        if guardrail_config.get("trace") == "enabled":
            resp["trace"] = {"guardrail": {"inputAssessment": {
                guardrail_config["guardrailIdentifier"]: {
                    "topicPolicy": {"topics": [
                        {"name": "Account transfers", "type": "DENY",
                         "action": "BLOCKED"}]},
                    "invocationMetrics": {
                        "guardrailProcessingLatency": 214,
                        "usage": {"topicPolicyUnits": 1, "contentPolicyUnits": 1,
                                  "wordPolicyUnits": 0,
                                  "sensitiveInformationPolicyUnits": 0,
                                  "contextualGroundingPolicyUnits": 0},
                        "guardrailCoverage": {
                            "textCharacters": {"guarded": 41, "total": 41}},
                    }}}}}
        return resp

    @staticmethod
    def _tool_use_response(tool_config: dict, cache_read: int, cache_write: int) -> dict:
        """stopReason 'tool_use' with a toolUse ContentBlock.

        Note that `input` is a decoded JSON object, not a string -- boto3 does
        the parsing for you. Note also that an assistant turn may contain BOTH
        a text block and one or more toolUse blocks; you must append the whole
        message back, not just the tool call.
        """
        name = tool_config["tools"][0]["toolSpec"]["name"]
        return {
            "output": {"message": {"role": "assistant", "content": [
                {"text": "Let me look that up."},
                {"toolUse": {
                    "toolUseId": "tooluse_S8kQmM2xQ0O1o4fFzZ2w",
                    "name": name,
                    "input": {"city": "Reykjavik", "unit": "celsius"},
                }},
            ]}},
            "stopReason": "tool_use",
            "usage": _usage(487, 62, cache_read, cache_write),
            "metrics": {"latencyMs": 941},
        }

    @staticmethod
    def _text_response(messages: list[dict], inference_config: dict | None,
                       cache_read: int, cache_write: int) -> dict:
        max_tokens = (inference_config or {}).get("maxTokens", 1024)
        saw_tool_result = any(
            "toolResult" in b for m in messages for b in m["content"])
        if saw_tool_result:
            text = ("It is -3 C in Reykjavik right now, with light snow. "
                    "Bring the coat you were hoping not to need.")
            out_tokens = 27
        else:
            text = ("Amazon Bedrock is a managed service that fronts many "
                    "foundation models behind one AWS-authenticated API.")
            out_tokens = 24

        # Demonstrate the truncation case that everyone forgets to handle.
        stop_reason = "end_turn"
        if max_tokens < out_tokens:
            out_tokens = max_tokens
            text = text[: max_tokens * 4] + "..."
            stop_reason = "max_tokens"

        return {
            "output": {"message": {"role": "assistant",
                                   "content": [{"text": text}]}},
            "stopReason": stop_reason,
            "usage": _usage(612, out_tokens, cache_read, cache_write),
            "metrics": {"latencyMs": 1175},
        }

    # -- converse_stream ----------------------------------------------------

    def converse_stream(self, modelId: str, messages: list[dict], **kw: Any) -> dict:
        """Returns {"stream": <iterator of event dicts>}, same as boto3.

        Event order, per the User Guide:
            messageStart
            [ contentBlockStart? contentBlockDelta+ contentBlockStop ]  x N
            messageStop        (carries stopReason)
            metadata           (carries usage + metrics)

        contentBlockStart appears for TOOL USE ONLY. Tool arguments arrive as
        partial JSON strings in contentBlockDelta.delta.toolUse.input and must
        be concatenated then json.loads()'d -- they are NOT valid JSON until
        contentBlockStop.
        """
        self._validate(modelId, messages)
        return {"stream": self._stream_events(kw.get("toolConfig") is not None)}

    @staticmethod
    def _stream_events(with_tool: bool) -> Iterator[dict]:
        yield {"messageStart": {"role": "assistant"}}

        for piece in ["Bedrock", " streams", " deltas", ",", " not",
                      " whole", " messages", "."]:
            yield {"contentBlockDelta": {"delta": {"text": piece},
                                         "contentBlockIndex": 0}}
        yield {"contentBlockStop": {"contentBlockIndex": 0}}

        if with_tool:
            yield {"contentBlockStart": {
                "start": {"toolUse": {"toolUseId": "tooluse_stream_01",
                                      "name": "get_weather"}},
                "contentBlockIndex": 1}}
            for frag in ['{"city"', ': "Reyk', 'javik", ', '"unit": ', '"celsius"}']:
                yield {"contentBlockDelta": {
                    "delta": {"toolUse": {"input": frag}},
                    "contentBlockIndex": 1}}
            yield {"contentBlockStop": {"contentBlockIndex": 1}}
            yield {"messageStop": {"stopReason": "tool_use"}}
        else:
            yield {"messageStop": {"stopReason": "end_turn"}}

        yield {"metadata": {
            "usage": {"inputTokens": 47, "outputTokens": 20, "totalTokens": 67},
            "metrics": {"latencyMs": 604.0}}}


def _usage(inp: int, out: int, cache_read: int = 0, cache_write: int = 0) -> dict:
    u = {"inputTokens": inp, "outputTokens": out, "totalTokens": inp + out}
    if cache_read:
        u["cacheReadInputTokens"] = cache_read
    if cache_write:
        u["cacheWriteInputTokens"] = cache_write
    return u


# ---------------------------------------------------------------------------
# The retry wrapper you are expected to own
# ---------------------------------------------------------------------------

def call_with_backoff(fn: Callable[[], dict], *, max_attempts: int = 6,
                      base_delay: float = 1.0, cap: float = 20.0,
                      sleep: Callable[[float], None] | None = None) -> dict:
    """Exponential backoff with FULL JITTER.

    The AWS SDKs implement this for you in "standard" retry mode:

        from botocore.config import Config
        cfg = Config(retries={"total_max_attempts": 6, "mode": "standard"})

    Note that botocore's `total_max_attempts` INCLUDES the first request, so 6
    means one call plus five retries. Delay formula used by the SDK:

        delay = random(0, 1) * min(cap_ms, base_delay * 2 ** attempt)

    Full jitter (random *between zero and* the backoff) rather than
    "backoff + a bit of noise" is what actually decorrelates a thundering
    herd. Do not retry ValidationException or AccessDeniedException -- those
    will fail identically forever and just burn your quota.
    https://docs.aws.amazon.com/bedrock/latest/userguide/scaling-throughput-best-practices.html
    """
    slept: list[float] = []
    sink = sleep or slept.append
    for attempt in range(max_attempts):
        try:
            resp = fn()
            if slept:
                print(f"    succeeded on attempt {attempt + 1} after "
                      f"{sum(slept):.2f}s of backoff "
                      f"({', '.join(f'{s:.2f}s' for s in slept)})")
            return resp
        except FakeClientError as err:
            if not err.retryable or attempt == max_attempts - 1:
                raise
            delay = RNG.uniform(0, min(cap, base_delay * (2 ** attempt)))
            print(f"    attempt {attempt + 1}: {err.code} (HTTP "
                  f"{err.response['ResponseMetadata']['HTTPStatusCode']}) "
                  f"-> sleeping {delay:.2f}s")
            sink(delay)
    raise RuntimeError("unreachable")


# ---------------------------------------------------------------------------
# The tool the model is allowed to call
# ---------------------------------------------------------------------------

TOOL_CONFIG = {
    "tools": [{
        "toolSpec": {
            "name": "get_weather",
            "description": (
                "Get the current weather for a city. Use this whenever the "
                "user asks about weather, temperature, or conditions."),
            "inputSchema": {"json": {
                "type": "object",
                "properties": {
                    "city": {"type": "string",
                             "description": "City name, e.g. 'Reykjavik'."},
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"],
                             "description": "Temperature unit."},
                },
                "required": ["city"],
            }},
        }
    }],
    # toolChoice is optional: {"auto": {}} (default), {"any": {}} (must call
    # some tool), {"tool": {"name": "..."}} (must call this one). Support
    # varies by model -- check the model card before relying on forcing.
    "toolChoice": {"auto": {}},
}


def get_weather(city: str, unit: str = "celsius") -> dict:
    """The actual tool. In production this is a Lambda, an RDS query, an API."""
    table = {"reykjavik": (-3, "light snow"), "cairo": (31, "clear")}
    temp, cond = table.get(city.lower(), (15, "unknown"))
    if unit == "fahrenheit":
        temp = round(temp * 9 / 5 + 32)
    return {"city": city, "temperature": temp, "unit": unit, "conditions": cond}


# ---------------------------------------------------------------------------
# Demos
# ---------------------------------------------------------------------------

MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"


def demo_plain_converse(client: FakeBedrockRuntime, ledger: Ledger) -> None:
    rule("1. Plain Converse")
    say("One request shape works across every message-capable model on "
        "Bedrock. `system` is a list of blocks, not a string. `messages[].content` "
        "is a list of ContentBlocks, not a string. Get those two wrong and you "
        "will spend an afternoon reading ValidationException messages.")

    request = {
        "modelId": MODEL_ID,
        "system": [{"text": "You are terse. Two sentences maximum."}],
        "messages": [{"role": "user",
                      "content": [{"text": "What is Amazon Bedrock?"}]}],
        "inferenceConfig": {"maxTokens": 512, "temperature": 0.2, "topP": 0.9,
                            "stopSequences": []},
    }
    show_json("REQUEST", request)
    resp = client.converse(**request)
    show_json("RESPONSE", resp)
    ledger.record(resp["usage"])
    print(f"\n  stopReason={resp['stopReason']}  "
          f"latencyMs={resp['metrics']['latencyMs']}")


def demo_tool_loop(client: FakeBedrockRuntime, ledger: Ledger) -> None:
    rule("2. Tool use: the full round trip")
    say("The model never calls your tool. It asks. You execute. You send the "
        "result back as a *user* message containing a toolResult block, echoing "
        "the toolUseId. Then you call converse again. That is the whole "
        "protocol, and it is identical for every model that supports tools.")

    messages: list[dict] = [{"role": "user", "content": [
        {"text": "What's the weather in Reykjavik? Use celsius."}]}]

    for turn in range(1, 5):
        resp = call_with_backoff(
            lambda: client.converse(modelId=MODEL_ID, messages=messages,
                                    toolConfig=TOOL_CONFIG,
                                    inferenceConfig={"maxTokens": 1024}))
        ledger.record(resp["usage"])
        assistant = resp["output"]["message"]
        stop = resp["stopReason"]
        print(f"\n  turn {turn}: stopReason={stop!r}")

        # ALWAYS append the entire assistant message, including any text block
        # that came alongside the toolUse. Dropping it corrupts the transcript.
        messages.append(assistant)

        if stop != "tool_use":
            show_json(f"FINAL ASSISTANT MESSAGE (turn {turn})", assistant)
            break

        show_json(f"ASSISTANT MESSAGE WITH toolUse (turn {turn})", assistant)

        tool_result_blocks = []
        for block in assistant["content"]:
            if "toolUse" not in block:
                continue
            tu = block["toolUse"]
            try:
                result = get_weather(**tu["input"])
                tool_result_blocks.append({"toolResult": {
                    "toolUseId": tu["toolUseId"],
                    "content": [{"json": result}],
                    "status": "success",
                }})
            except Exception as exc:  # noqa: BLE001 - teaching the error path
                # Returning status "error" lets the model recover. Raising
                # here instead just strands the conversation.
                tool_result_blocks.append({"toolResult": {
                    "toolUseId": tu["toolUseId"],
                    "content": [{"text": f"Tool failed: {exc}"}],
                    "status": "error",
                }})

        user_turn = {"role": "user", "content": tool_result_blocks}
        show_json(f"YOUR toolResult MESSAGE (turn {turn})", user_turn)
        messages.append(user_turn)
    else:
        print("\n  Hit the turn cap. ALWAYS have one -- a model that keeps "
              "asking for tools will otherwise bill you until you notice.")

    print(f"\n  final transcript length: {len(messages)} messages "
          "(user, assistant+toolUse, user+toolResult, assistant)")


def demo_streaming(client: FakeBedrockRuntime) -> None:
    rule("3. ConverseStream event ordering")
    say("Streaming is not 'the same response, in pieces'. It is a different "
        "shape: an event stream you must reassemble. Text deltas are easy. "
        "Tool-use deltas are partial JSON *strings* that are invalid JSON until "
        "the block stops -- accumulate, then parse.")

    resp = client.converse_stream(modelId=MODEL_ID,
                                  messages=[{"role": "user", "content": [
                                      {"text": "Explain streaming."}]}],
                                  toolConfig=TOOL_CONFIG)

    text_parts: list[str] = []
    tool_json_parts: dict[int, list[str]] = {}
    tool_names: dict[int, str] = {}
    print()
    for event in resp["stream"]:
        (kind,) = event.keys()
        body = event[kind]
        if kind == "messageStart":
            print(f"  messageStart      role={body['role']}")
        elif kind == "contentBlockStart":
            idx = body["contentBlockIndex"]
            tu = body["start"]["toolUse"]
            tool_names[idx] = tu["name"]
            tool_json_parts[idx] = []
            print(f"  contentBlockStart idx={idx} toolUse name={tu['name']!r} "
                  f"id={tu['toolUseId']!r}")
        elif kind == "contentBlockDelta":
            idx = body["contentBlockIndex"]
            delta = body["delta"]
            if "text" in delta:
                text_parts.append(delta["text"])
                print(f"  contentBlockDelta idx={idx} text={delta['text']!r}")
            elif "toolUse" in delta:
                frag = delta["toolUse"]["input"]
                tool_json_parts[idx].append(frag)
                print(f"  contentBlockDelta idx={idx} toolUse.input={frag!r}"
                      "   <- partial JSON, not parseable yet")
        elif kind == "contentBlockStop":
            print(f"  contentBlockStop  idx={body['contentBlockIndex']}")
        elif kind == "messageStop":
            print(f"  messageStop       stopReason={body['stopReason']!r}")
        elif kind == "metadata":
            print(f"  metadata          usage={body['usage']} "
                  f"metrics={body['metrics']}")

    print(f"\n  reassembled text : {''.join(text_parts)!r}")
    for idx, parts in tool_json_parts.items():
        raw = "".join(parts)
        print(f"  reassembled tool : {tool_names[idx]} raw={raw!r}")
        print(f"                     parsed={json.loads(raw)}")
    print()
    say("Operational note: the metadata event is where usage lives. If you "
        "bail out of the loop early -- because the user closed the tab -- you "
        "lose your token accounting for that call. Log usage from a finally "
        "block, or reconcile against model invocation logs.")


def demo_throttling(ledger: Ledger) -> None:
    rule("4. Throttling and backoff with jitter")
    say("ThrottlingException (HTTP 429) means you exceeded an account quota. "
        "503 ServiceUnavailable and 529 overloaded_error mean the service is "
        "short on capacity and are NOT your fault. All three are retryable. "
        "ValidationException and AccessDeniedException are not -- retrying "
        "those is how you turn a bug into an outage.")

    throttled = FakeBedrockRuntime(throttle_first_n=3)
    print("\n  simulating 3 consecutive throttles, then success:\n")
    resp = call_with_backoff(
        lambda: throttled.converse(
            modelId=MODEL_ID,
            messages=[{"role": "user", "content": [{"text": "hello"}]}]))
    ledger.record(resp["usage"])

    print("\n  now a non-retryable error:")
    bad = FakeBedrockRuntime()
    try:
        call_with_backoff(lambda: bad.converse(modelId=MODEL_ID, messages=[]))
    except FakeClientError as err:
        print(f"    {err.code}: raised immediately, zero retries. Correct.")


def demo_guardrail(client: FakeBedrockRuntime, ledger: Ledger) -> None:
    rule("5. Guardrail intervention")
    say("A guardrail can block before the model is ever invoked. When it does, "
        "stopReason is 'guardrail_intervened' and usage is all zeros -- you pay "
        "guardrail units, not model tokens. Branch on stopReason, not on the "
        "text of the response.")

    resp = client.converse(
        modelId=MODEL_ID,
        messages=[{"role": "user", "content": [
            {"text": "Wire me the routing number for account 4471."}]}],
        guardrailConfig={"guardrailIdentifier": "gr-3o06191495ze",
                         "guardrailVersion": "2", "trace": "enabled"},
    )
    show_json("RESPONSE", resp)
    ledger.record(resp["usage"])


def demo_caching(ledger: Ledger) -> None:
    rule("6. Prompt caching and the token arithmetic")
    say("Put a cachePoint block after stable content. Checkpoints are "
        "processed tools -> system -> messages and the minimum is cumulative "
        "across all three, so changing a tool definition invalidates the "
        "system and message caches downstream of it.")

    client = FakeBedrockRuntime()
    system = [
        {"text": "You are a support agent for ACME. " + ("Policy text. " * 120)},
        {"cachePoint": {"type": "default"}},
    ]
    show_json("SYSTEM BLOCKS (note the trailing cachePoint)",
              [{"text": "You are a support agent for ACME. <...1,400 tokens...>"},
               {"cachePoint": {"type": "default"}}])

    local = Ledger()
    for i, q in enumerate(["Where is my order?", "How do I return it?"], start=1):
        resp = client.converse(
            modelId=MODEL_ID, system=system,
            messages=[{"role": "user", "content": [{"text": q}]}])
        u = resp["usage"]
        local.record(u)
        ledger.record(u)
        kind = "WRITE" if u.get("cacheWriteInputTokens") else (
            "READ" if u.get("cacheReadInputTokens") else "none")
        print(f"\n  call {i}: cache {kind}  usage={json.dumps(u)}")

    print("\n  Ledger for these two calls:")
    local.report()
    print()
    say("The trap: `inputTokens` alone under-reports your real prompt size "
        "whenever caching is on. Dashboards built on inputTokens will quietly "
        "show a 60% drop in 'usage' on the day you enable caching, and someone "
        "will believe it.")


def demo_cost_model(ledger: Ledger) -> None:
    rule("7. Worked cost estimate (assumptions stated, numbers invented)")
    print(textwrap.dedent("""
      ASSUMPTIONS -- change every one of these for your workload:
        - 50,000 chat requests per day
        - 2,000 input tokens per request (1,600 of them a stable system prefix)
        - 400 output tokens per request
        - prompt caching on, 85% cache-hit rate on the stable prefix
        - ILLUSTRATIVE rates per 1M tokens: input $3.00, output $15.00,
          cache read $0.30, cache write $3.75

      These rates are made up for arithmetic practice. Real Bedrock prices vary
      by model, Region, service tier, and change over time. Price from
      https://aws.amazon.com/bedrock/pricing/ and from Cost Explorer, never
      from a tutorial -- including this one.
    """).strip())

    reqs = 50_000
    stable, variable, out = 1_600, 400, 400
    hit_rate = 0.85

    naive_in = reqs * (stable + variable)
    naive = naive_in / 1e6 * 3.00 + reqs * out / 1e6 * 15.00

    reads = reqs * hit_rate * stable
    writes = reqs * (1 - hit_rate) * stable
    uncached_in = reqs * variable
    cached = (uncached_in / 1e6 * 3.00 + reads / 1e6 * 0.30
              + writes / 1e6 * 3.75 + reqs * out / 1e6 * 15.00)

    print(f"\n  no caching        : ${naive:>9,.2f}/day   ${naive * 365:>11,.0f}/yr")
    print(f"  with caching      : ${cached:>9,.2f}/day   ${cached * 365:>11,.0f}/yr")
    print(f"  saving            : ${naive - cached:>9,.2f}/day "
          f"({(naive - cached) / naive:.0%})")

    print("\n  Then ask the three questions that actually move the number:")
    print("    1. Right-size the model. A Haiku-class model on the 70% of")
    print("       traffic that is routing and extraction usually beats every")
    print("       other optimisation combined.")
    print("    2. Can any of this be batch? Batch inference is discounted and")
    print("       runs against S3 JSONL -- but it does not support tool use.")
    print("    3. Is output length bounded? maxTokens is a cost control, not")
    print("       just a safety net. Output tokens are the expensive ones.")


def main() -> int:
    rule()
    print("Amazon Bedrock Converse API -- OFFLINE SIMULATOR".center(WIDTH))
    rule()
    say("No AWS credentials, no network, no boto3. Every JSON shape below "
        "matches the Amazon Bedrock User Guide; every token count and dollar "
        "figure is invented for teaching and labelled as such.")

    ledger = Ledger()
    client = FakeBedrockRuntime()

    demo_plain_converse(client, ledger)
    demo_tool_loop(client, ledger)
    demo_streaming(client)
    demo_throttling(ledger)
    demo_guardrail(client, ledger)
    demo_caching(ledger)
    demo_cost_model(ledger)

    rule("Session ledger (all simulated calls)")
    ledger.report()

    rule("What to do next")
    print(textwrap.dedent("""
      - Read code/converse_api_reference.py for the real boto3 calls.
      - Read code/iam_and_guardrails_examples.md for the IAM and guardrail JSON.
      - Then break this file: change a role to "system", drop a toolUseId,
        set maxTokens to 5. The ValidationExceptions are the lesson.
    """).strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
