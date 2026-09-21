#!/usr/bin/env python3
"""
converse_api_reference.py — the real boto3 calls for Amazon Bedrock's Converse
API, with a guard rail around them so this file is useful even on a laptop with
no AWS account.

HOW IT BEHAVES
--------------
  * boto3 missing, or no resolvable AWS credentials
        -> DRY-RUN MODE. Prints the exact request and response JSON for every
           pattern, annotated, and exits 0. Nothing is sent anywhere.
  * boto3 present and credentials resolvable
        -> LIVE MODE. Actually calls Converse / ConverseStream against
           BEDROCK_MODEL_ID in BEDROCK_REGION. This costs money.

  Force dry-run even with credentials:  BEDROCK_DRY_RUN=1 python converse_api_reference.py

THIS SCRIPT NEVER RAISES. Every failure path prints an explanation and returns
exit code 0, because a teaching file that crashes has taught you nothing.

PRIMARY SOURCES (verified 2026-09)
----------------------------------
  Converse API .... https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
  Tool use ........ https://docs.aws.amazon.com/bedrock/latest/userguide/tool-use.html
  Client-side tools https://docs.aws.amazon.com/bedrock/latest/userguide/tool-use-client-side.html
  Guardrails ...... https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-use-converse-api.html
  Prompt caching .. https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html
  Inference prof. . https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html
  Scaling/retries . https://docs.aws.amazon.com/bedrock/latest/userguide/scaling-throughput-best-practices.html
"""

from __future__ import annotations

import json
import os
import sys
import textwrap
from typing import Any

WIDTH = 78

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REGION = os.environ.get("BEDROCK_REGION", "us-east-1")

# MODEL IDs: two conventions coexist on Bedrock and both are real.
#
#   Foundation-model ID     anthropic.claude-sonnet-4-5-20250929-v1:0
#   Inference-profile ID    us.anthropic.claude-sonnet-4-5-20250929-v1:0
#                           eu.anthropic.claude-sonnet-4-5-20250929-v1:0
#                           global.anthropic.claude-opus-4-7
#
# The geography prefix (us. / eu. / apac. / global.) selects a cross-Region
# inference profile. Many newer models are ONLY reachable through a profile --
# calling the bare foundation-model ID returns a ValidationException telling
# you so. Prefer the profile: it gives you multi-Region capacity for free, and
# `global.` is documented as roughly 10% cheaper than a geographic profile.
#
# Never hardcode a model ID you have not verified. Run:
#     aws bedrock list-foundation-models --region us-east-1
#     aws bedrock list-inference-profiles --region us-east-1
MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")

FORCE_DRY_RUN = os.environ.get("BEDROCK_DRY_RUN", "") not in ("", "0", "false")


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def rule(title: str = "") -> None:
    if title:
        print(f"\n== {title} " + "=" * max(WIDTH - len(title) - 6, 0))
    else:
        print("=" * WIDTH)


def say(text: str) -> None:
    print(textwrap.fill(" ".join(text.split()), WIDTH))


def show(label: str, obj: Any) -> None:
    print(f"\n--- {label} " + "-" * max(WIDTH - len(label) - 5, 0))
    print(json.dumps(obj, indent=2, default=str))


# ---------------------------------------------------------------------------
# Environment probe
# ---------------------------------------------------------------------------

def probe_environment() -> tuple[bool, str]:
    """Return (live_mode, reason). Never raises."""
    if FORCE_DRY_RUN:
        return False, "BEDROCK_DRY_RUN is set."
    try:
        import boto3  # noqa: F401
        import botocore  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        return False, f"boto3/botocore not importable ({exc.__class__.__name__})."
    try:
        import boto3
        creds = boto3.Session().get_credentials()
        if creds is None:
            return False, "No AWS credentials resolved by the default chain."
        frozen = creds.get_frozen_credentials()
        if not frozen.access_key:
            return False, "Credential chain returned an empty access key."
    except Exception as exc:  # noqa: BLE001
        return False, f"Credential resolution failed ({exc.__class__.__name__}: {exc})."
    return True, f"Credentials resolved; region={REGION}, model={MODEL_ID}."


def make_client() -> Any:
    """bedrock-runtime client with the retry behaviour you want in production.

    Defaults are not good enough:
      * botocore's default retry mode is "legacy". Use "standard" -- it does
        exponential backoff with full jitter and separates throttling delays
        from transient-network delays.
      * total_max_attempts INCLUDES the first request. 6 = 1 call + 5 retries.
      * read_timeout must exceed the model's worst-case generation time, or you
        will time out mid-answer, retry, and pay twice for the same tokens.
      * tcp_keepalive matters when egress goes through a NAT Gateway, an
        interface VPC endpoint, or an NLB -- all of which silently drop idle
        connections after 350 seconds.
    """
    import boto3
    from botocore.config import Config

    return boto3.client(
        "bedrock-runtime",
        region_name=REGION,
        config=Config(
            retries={"total_max_attempts": 6, "mode": "standard"},
            read_timeout=300,
            connect_timeout=10,
            tcp_keepalive=True,
        ),
    )


# ---------------------------------------------------------------------------
# Canonical shapes (used verbatim in both modes)
# ---------------------------------------------------------------------------

SYSTEM_BLOCKS = [
    {"text": "You are a precise assistant for a logistics company. "
             "Answer in at most three sentences. If you do not know, say so."},
    # A cachePoint marks the end of a cacheable prefix. Order of evaluation is
    # tools -> system -> messages, and the model's minimum token count is
    # CUMULATIVE across all three. Changing `tools` invalidates the `system`
    # and `messages` caches downstream of it.
    # {"cachePoint": {"type": "default"}},
]

INFERENCE_CONFIG = {
    # The four parameters every model on Bedrock understands. Anything
    # model-specific (top_k, reasoning budgets, ...) goes in
    # additionalModelRequestFields instead.
    "maxTokens": 512,
    "temperature": 0.2,
    "topP": 0.9,
    "stopSequences": [],
}

TOOL_CONFIG = {
    "tools": [{
        "toolSpec": {
            "name": "get_shipment_status",
            # The description is the prompt. This is the single highest-leverage
            # string in your tool definition -- the model decides whether to
            # call the tool based on it, not on the function name.
            "description": (
                "Look up the live status of a shipment by its tracking number. "
                "Use this whenever the user asks where a package is, whether it "
                "has been delivered, or when it will arrive."),
            "inputSchema": {"json": {
                "type": "object",
                "properties": {
                    "tracking_number": {
                        "type": "string",
                        "description": "Tracking number, e.g. 'ACM-4471-XZ'."},
                    "include_history": {
                        "type": "boolean",
                        "description": "Return all scan events, not just the latest."},
                },
                "required": ["tracking_number"],
            }},
        }
    }],
    # {"auto": {}} lets the model decide (default). {"any": {}} forces some
    # tool. {"tool": {"name": "..."}} forces a specific one. Support for the
    # forcing variants differs by model -- check the model card first.
    "toolChoice": {"auto": {}},
}


def get_shipment_status(tracking_number: str, include_history: bool = False) -> dict:
    """The tool implementation. In production: a Lambda, a DB, an internal API.

    Treat the arguments as untrusted input. They were produced by a language
    model that read text you do not control. Validate before you touch a
    database, and never interpolate them into a query or a shell command.
    """
    if not tracking_number.startswith("ACM-"):
        raise ValueError(f"Unknown tracking number format: {tracking_number!r}")
    record = {"tracking_number": tracking_number, "status": "in_transit",
              "last_scan": "2026-09-14T22:11:00Z", "location": "Memphis, TN",
              "eta": "2026-09-16"}
    if include_history:
        record["history"] = [
            {"at": "2026-09-12T08:02:00Z", "event": "picked_up"},
            {"at": "2026-09-14T22:11:00Z", "event": "arrived_at_hub"},
        ]
    return record


# ---------------------------------------------------------------------------
# Pattern 1 — Converse
# ---------------------------------------------------------------------------

def pattern_converse(client: Any | None) -> None:
    rule("Pattern 1 - Converse (single turn)")
    say("""Converse is the one request shape that works across every
        message-capable model on Bedrock. InvokeModel still exists and still
        works, but it takes a raw per-provider body: Anthropic wants
        anthropic_version and a messages array with typed content; Amazon Nova
        wants inferenceConfig inside the body; Meta wants a flat prompt string.
        Writing against InvokeModel means writing an adapter per provider and
        rewriting it when you swap models. Converse is what you should build
        on. Reach for InvokeModel only for a model-specific feature Converse
        does not surface.""")

    request = {
        "modelId": MODEL_ID,
        "system": SYSTEM_BLOCKS,
        "messages": [{"role": "user", "content": [
            {"text": "In one sentence: what does a cross-Region inference "
                     "profile buy me?"}]}],
        "inferenceConfig": INFERENCE_CONFIG,
        # Recorded verbatim in your model invocation logs. Use it. Filtering
        # a month of invocation logs by team and environment is the difference
        # between a cost investigation that takes an hour and one that takes a
        # week.
        "requestMetadata": {"team": "logistics", "environment": "dev",
                            "feature": "tracking-assistant"},
    }
    show("REQUEST  client.converse(**request)", request)

    if client is None:
        show("RESPONSE (canonical shape, from the User Guide)", {
            "output": {"message": {"role": "assistant", "content": [
                {"text": "It routes your request across several Regions in a "
                         "geography, which raises effective throughput without "
                         "you managing failover."}]}},
            "stopReason": "end_turn",
            "usage": {"inputTokens": 125, "outputTokens": 60, "totalTokens": 185},
            "metrics": {"latencyMs": 1175},
        })
        annotate_response_envelope()
        return

    try:
        resp = client.converse(**request)
    except Exception as exc:  # noqa: BLE001
        explain_client_error(exc)
        return
    show("RESPONSE", strip_metadata(resp))
    annotate_response_envelope()


def annotate_response_envelope() -> None:
    print(textwrap.dedent("""
      Reading the envelope:
        output.message.content   list of ContentBlocks -- text, toolUse,
                                 reasoningContent, image, document, video
        stopReason               BRANCH ON THIS, never on the text. Values you
                                 must handle: end_turn, max_tokens, tool_use,
                                 guardrail_intervened. (See the API reference
                                 for the complete enum before you write an
                                 exhaustive match.)
        usage                    inputTokens, outputTokens, totalTokens, plus
                                 cacheReadInputTokens / cacheWriteInputTokens
                                 when prompt caching is on
        metrics.latencyMs        server-side latency, excludes your network
    """).rstrip())


# ---------------------------------------------------------------------------
# Pattern 2 — ConverseStream
# ---------------------------------------------------------------------------

def pattern_stream(client: Any | None) -> None:
    rule("Pattern 2 - ConverseStream")
    say("""Streaming is a different response shape, not the same response in
        pieces. You get an event stream and you reassemble it. Two operational
        details people discover late: the usage numbers arrive only in the
        final metadata event, so abandoning the iterator loses your token
        accounting; and ConverseStream requires the
        bedrock:InvokeModelWithResponseStream IAM permission, not
        bedrock:InvokeModel -- a policy that only grants the latter fails at
        runtime, in production, on the streaming path only.""")

    request = {
        "modelId": MODEL_ID,
        "messages": [{"role": "user", "content": [
            {"text": "List three reasons to stream LLM output to a browser."}]}],
        "inferenceConfig": {"maxTokens": 300},
    }
    show("REQUEST  client.converse_stream(**request)", request)

    if client is None:
        print("\n--- EVENT SEQUENCE (from the User Guide) " + "-" * 36)
        for ev in [
            {"messageStart": {"role": "assistant"}},
            {"contentBlockDelta": {"delta": {"text": "1."}, "contentBlockIndex": 0}},
            {"contentBlockDelta": {"delta": {"text": " Perceived"}, "contentBlockIndex": 0}},
            {"contentBlockDelta": {"delta": {"text": " latency"}, "contentBlockIndex": 0}},
            "... many more contentBlockDelta events ...",
            {"contentBlockStop": {"contentBlockIndex": 0}},
            {"messageStop": {"stopReason": "end_turn"}},
            {"metadata": {"usage": {"inputTokens": 47, "outputTokens": 20,
                                    "totalTokens": 67},
                          "metrics": {"latencyMs": 100.0}}},
        ]:
            print("  " + (ev if isinstance(ev, str) else json.dumps(ev)))
        print(textwrap.dedent("""
          Ordering guarantee:
            messageStart
              for each content block, indexed by contentBlockIndex:
                contentBlockStart   (TOOL USE ONLY)
                contentBlockDelta+  (text | reasoningContent | toolUse)
                contentBlockStop
            messageStop   carries stopReason
            metadata      carries usage and metrics

          Tool arguments stream as PARTIAL JSON STRINGS in
          delta.toolUse.input. Concatenate across deltas for one
          contentBlockIndex, then json.loads() once contentBlockStop arrives.
          Parsing early throws.
        """).rstrip())
        return

    try:
        resp = client.converse_stream(**request)
        parts: list[str] = []
        for event in resp["stream"]:
            if "contentBlockDelta" in event:
                delta = event["contentBlockDelta"]["delta"]
                if "text" in delta:
                    parts.append(delta["text"])
                    print(delta["text"], end="", flush=True)
            elif "messageStop" in event:
                print(f"\n  stopReason={event['messageStop']['stopReason']}")
            elif "metadata" in event:
                print(f"  usage={event['metadata'].get('usage')}")
    except Exception as exc:  # noqa: BLE001
        explain_client_error(exc)


# ---------------------------------------------------------------------------
# Pattern 3 — tool use
# ---------------------------------------------------------------------------

def pattern_tool_use(client: Any | None) -> None:
    rule("Pattern 3 - Tool use (the full loop)")
    say("""Bedrock does not call your tool. It returns stopReason 'tool_use'
        and a toolUse ContentBlock. You execute, then send the result back as a
        USER message containing a toolResult block that echoes the toolUseId,
        and call converse again. Three rules that are load-bearing: append the
        ENTIRE assistant message (a turn can carry text alongside the toolUse);
        return one toolResult per toolUse, all in a single user message, since
        models can request several tools in parallel; and on failure return
        status 'error' rather than raising, so the model can recover instead of
        the conversation dying.""")

    messages: list[dict] = [{"role": "user", "content": [
        {"text": "Where is shipment ACM-4471-XZ right now?"}]}]

    if client is None:
        show("STEP 1 REQUEST", {"modelId": MODEL_ID, "messages": messages,
                                "toolConfig": TOOL_CONFIG})
        assistant = {"role": "assistant", "content": [
            {"text": "Let me check that tracking number."},
            {"toolUse": {"toolUseId": "tooluse_kZJMlvQmRJ6eAyJE5GeI",
                         "name": "get_shipment_status",
                         "input": {"tracking_number": "ACM-4471-XZ"}}}]}
        show("STEP 2 RESPONSE  stopReason='tool_use'", {
            "output": {"message": assistant},
            "stopReason": "tool_use",
            "usage": {"inputTokens": 487, "outputTokens": 62, "totalTokens": 549},
            "metrics": {"latencyMs": 941}})

        result = get_shipment_status("ACM-4471-XZ")
        tool_msg = {"role": "user", "content": [{"toolResult": {
            "toolUseId": "tooluse_kZJMlvQmRJ6eAyJE5GeI",
            "content": [{"json": result}],
            "status": "success"}}]}
        show("STEP 3 YOUR toolResult MESSAGE (role MUST be 'user')", tool_msg)
        show("STEP 3b THE ERROR VARIANT", {"role": "user", "content": [
            {"toolResult": {"toolUseId": "tooluse_kZJMlvQmRJ6eAyJE5GeI",
                            "content": [{"text": "Unknown tracking number "
                                                 "format: 'XYZ-1'"}],
                            "status": "error"}}]})
        show("STEP 4 REQUEST  (full transcript replayed)", {
            "modelId": MODEL_ID,
            "messages": messages + [assistant, tool_msg],
            "toolConfig": TOOL_CONFIG})
        show("STEP 5 RESPONSE  stopReason='end_turn'", {
            "output": {"message": {"role": "assistant", "content": [
                {"text": "ACM-4471-XZ is in transit, last scanned in Memphis, "
                         "TN on 14 September, with an estimated delivery of "
                         "16 September."}]}},
            "stopReason": "end_turn",
            "usage": {"inputTokens": 664, "outputTokens": 41, "totalTokens": 705},
            "metrics": {"latencyMs": 812}})
        print(textwrap.dedent("""
          Note the cost shape: a one-tool answer costs TWO model calls, and the
          second replays the whole transcript including the tool output. A
          five-hop agent is not five times a chat message -- it is closer to
          fifteen, because context grows on every hop. This is exactly where
          prompt caching and a bounded hop limit earn their keep.
        """).rstrip())
        return

    try:
        for hop in range(1, 6):  # ALWAYS bound the loop.
            resp = client.converse(modelId=MODEL_ID, messages=messages,
                                   toolConfig=TOOL_CONFIG,
                                   inferenceConfig={"maxTokens": 1024})
            assistant = resp["output"]["message"]
            messages.append(assistant)
            print(f"\n  hop {hop}: stopReason={resp['stopReason']!r} "
                  f"usage={resp['usage']}")
            if resp["stopReason"] != "tool_use":
                show("FINAL", assistant)
                break
            blocks = []
            for block in assistant["content"]:
                if "toolUse" not in block:
                    continue
                tu = block["toolUse"]
                try:
                    out = get_shipment_status(**tu["input"])
                    blocks.append({"toolResult": {
                        "toolUseId": tu["toolUseId"],
                        "content": [{"json": out}], "status": "success"}})
                except Exception as exc:  # noqa: BLE001
                    blocks.append({"toolResult": {
                        "toolUseId": tu["toolUseId"],
                        "content": [{"text": str(exc)}], "status": "error"}})
            messages.append({"role": "user", "content": blocks})
        else:
            print("  hop limit reached -- stopping. Always have a hop limit.")
    except Exception as exc:  # noqa: BLE001
        explain_client_error(exc)


# ---------------------------------------------------------------------------
# Pattern 4 — guardrails, caching, model-specific fields
# ---------------------------------------------------------------------------

def pattern_extras() -> None:
    rule("Pattern 4 - Guardrails, caching, model-specific fields")

    say("""A guardrail attaches to the request, not to the model. Same call,
        one extra key. When it fires, stopReason is 'guardrail_intervened' and
        usage is zeros -- the model was never invoked. Important limitation for
        agents: with tool use, the guardrail does NOT evaluate toolResult
        content, tool descriptions, or the arguments the model generates. If
        untrusted data enters through a tool result, a Converse-attached
        guardrail will not see it -- call ApplyGuardrail on that text yourself.""")
    show("guardrailConfig (Converse)", {
        "guardrailIdentifier": "gr-abc123", "guardrailVersion": "2",
        "trace": "enabled"})
    show("guardrailConfig (ConverseStream adds streamProcessingMode)", {
        "guardrailIdentifier": "gr-abc123", "guardrailVersion": "2",
        "trace": "enabled",
        # "sync" = finish the guardrail assessment before emitting chunks.
        # "async" = stream now, assess in the background. async is faster and
        # can let a few offending tokens reach the user before the block lands.
        "streamProcessingMode": "sync"})
    show("Scoping a guardrail to part of a message with guardContent", [
        {"role": "user", "content": [
            {"text": "Only answer with a list of depots."},
            {"guardContent": {"text": {"text": "Where should I route ACM-4471?"}}}]}])
    print("  Once ANY guardContent block appears, the guardrail evaluates ONLY\n"
          "  guardContent blocks. Everything else is skipped entirely.")
    show("Contextual grounding: qualifiers mark source vs query", [
        {"role": "user", "content": [
            {"guardContent": {"text": {
                "text": "<retrieved passages from your knowledge base>",
                "qualifiers": ["grounding_source"]}}},
            {"guardContent": {"text": {
                "text": "What is our returns window?",
                "qualifiers": ["query"]}}}]}])
    print("  Grounding and relevance are scored 0..0.99 against these. This is\n"
          "  the closest thing Bedrock gives you to a managed hallucination\n"
          "  check for RAG, and it only evaluates the OUTPUT.")

    print()
    say("""Prompt caching: a cachePoint block ends a cacheable prefix. Put it
        after the stable content -- tool definitions, the system prompt, the
        long policy document -- and before anything that varies per request.""")
    show("cachePoint in system", [
        {"text": "<1,024+ tokens of stable instructions>"},
        {"cachePoint": {"type": "default"}}])
    show("cachePoint in tools, with an explicit TTL", {
        "tools": [{"toolSpec": {"name": "...", "description": "...",
                                "inputSchema": {"json": {}}}},
                  {"cachePoint": {"type": "default", "ttl": "1h"}}]})
    print("  Minimum prefix size and max checkpoint count are PER MODEL (512 /\n"
          "  1,024 / 4,096 tokens depending on the model; typically 4\n"
          "  checkpoints). Below the minimum the request still succeeds and\n"
          "  silently does not cache -- verify with cacheReadInputTokens, not\n"
          "  with hope. Prompt caching is not supported for batch inference.")

    print()
    say("""Anything a single provider supports but Converse has not
        standardised goes in additionalModelRequestFields, and anything a
        provider returns that Converse normalises away can be pulled back with
        additionalModelResponseFieldPaths (JSON Pointers).""")
    show("additionalModelRequestFields", {"top_k": 200})
    show("additionalModelResponseFieldPaths", ["/stop_sequence"])
    show("serviceTier -- latency/cost tier selection", {
        "serviceTier": {"type": "default"}})
    print("  Documented types: reserved | priority | default | flex.\n"
          "  flex trades latency variance for cost on work that can wait.")


# ---------------------------------------------------------------------------
# Error explanation
# ---------------------------------------------------------------------------

ERROR_HELP = {
    "AccessDeniedException": (
        "403. Either your IAM principal lacks bedrock:InvokeModel on this "
        "resource, or model access is not enabled. For Anthropic models the "
        "one-time use-case form (PutUseCaseForModelAccess) must be submitted "
        "for the account or org before the first invocation."),
    "ValidationException": (
        "400. Your request shape is wrong, or the model requires an inference "
        "profile and you passed a bare foundation-model ID. Read the message "
        "text -- it is unusually specific. Do NOT retry."),
    "ThrottlingException": (
        "429. Account quota exceeded. Retry with exponential backoff and "
        "jitter, then consider cross-Region inference, a quota increase, or "
        "Provisioned Throughput."),
    "ServiceUnavailable": (
        "503. Transient capacity, not your quota. Retry with backoff; if it "
        "persists, stop ramping and try another Region."),
    "ResourceNotFound": (
        "404. Bad model ID, or the model is not available in this Region. "
        "Check with `aws bedrock list-foundation-models --region <r>`."),
    "ExpiredTokenException": (
        "403. Your temporary credentials expired. Refresh them."),
}


def explain_client_error(exc: Exception) -> None:
    code = ""
    try:
        code = exc.response["Error"]["Code"]  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    print(f"\n  Call failed: {exc.__class__.__name__}: {exc}")
    if code and code in ERROR_HELP:
        print(f"  {code} -> " + textwrap.fill(ERROR_HELP[code], WIDTH - 4,
                                              subsequent_indent="      "))
    print("  Continuing in explanation mode; this script never crashes.")


def strip_metadata(resp: dict) -> dict:
    return {k: v for k, v in resp.items() if k != "ResponseMetadata"}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    rule()
    print("Amazon Bedrock Converse API -- annotated boto3 reference".center(WIDTH))
    rule()

    live, reason = probe_environment()
    print(f"\nMode  : {'LIVE (calls AWS, costs money)' if live else 'DRY RUN'}")
    print(f"Reason: {reason}")
    if not live:
        say("""Dry-run mode prints the exact JSON that would go over the wire
            and the exact JSON the service returns. That is the part worth
            memorising; the boto3 call is a one-liner around it. To run for
            real: install boto3, configure credentials, enable model access,
            and set BEDROCK_MODEL_ID / BEDROCK_REGION.""")

    client = None
    if live:
        try:
            client = make_client()
        except Exception as exc:  # noqa: BLE001
            print(f"\n  Could not build a client ({exc}). Falling back to dry run.")
            client = None

    for fn in (pattern_converse, pattern_stream, pattern_tool_use):
        try:
            fn(client)
        except Exception as exc:  # noqa: BLE001
            print(f"\n  [{fn.__name__} raised {exc.__class__.__name__}: {exc}]")
            print("  Swallowed on purpose -- see the module docstring.")

    try:
        pattern_extras()
    except Exception as exc:  # noqa: BLE001
        print(f"\n  [pattern_extras raised {exc}]")

    rule("Checklist before you ship this")
    print(textwrap.dedent("""
      [ ] modelId is an inference profile ID, not a bare foundation model
      [ ] botocore Config: mode="standard", total_max_attempts=6, read_timeout
          longer than worst-case generation, tcp_keepalive=True
      [ ] every code path branches on stopReason, including max_tokens and
          guardrail_intervened
      [ ] the tool loop has a hop limit and returns status:"error" on failure
      [ ] usage is logged per call, including cacheRead/cacheWrite
      [ ] requestMetadata carries team / environment / feature
      [ ] IAM grants BOTH InvokeModel and InvokeModelWithResponseStream, scoped
          to specific model and inference-profile ARNs
      [ ] model invocation logging is enabled and pointed at CloudWatch or S3
    """).rstrip())
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - the whole point
        print(f"\nUnexpected error: {exc.__class__.__name__}: {exc}")
        print("Exiting 0 anyway -- this file is documentation that happens to run.")
        sys.exit(0)
