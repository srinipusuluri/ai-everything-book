"""
tools_and_structured_output.py -- tool calling and typed output, offline.

RUNS WITH NO NETWORK AND NO API KEY. `ScriptedChatModel` replays a fixed transcript
of AIMessages, so the agent loop below is exercised deterministically -- you control
exactly when the "model" asks for a tool and when it answers.

    /Users/srinip/ai-all/.venv/bin/python tools_and_structured_output.py

The point of this file: tool calling is a five-line protocol, and every framework
(LangChain, the raw Anthropic/OpenAI SDKs, MCP) implements the same one:

    1. describe tools as JSON Schema and send them with the request
    2. model replies with an AIMessage carrying `.tool_calls`
    3. you execute each call yourself
    4. you append a ToolMessage per call, keyed by tool_call_id
    5. you call the model again with the extended history

Step 4 is where people get hurt: EVERY tool call in an AIMessage must get a matching
ToolMessage before the next model call, or the provider rejects the conversation.

Targets langchain-core 1.6.3 / langchain 1.4.0.
In production you would usually let `langchain.agents.create_agent` run this loop for
you -- but write it once by hand or you will never debug it. See notes/02.
"""

from __future__ import annotations

import json
from typing import Annotated, Literal

from fakes import ScriptedChatModel, rule
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import ToolException, tool
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import BaseModel, Field, ValidationError

# ---------------------------------------------------------------------------
# 1. Defining tools. The docstring is the prompt. The type hints are the schema.
# ---------------------------------------------------------------------------


@tool
def get_seat_count(aircraft: str) -> int:
    """Return the number of passenger seats on an aircraft model.

    Args:
        aircraft: ICAO-ish model code, e.g. "A320" or "B738".
    """
    table = {"A320": 180, "B738": 189, "E190": 100}
    if aircraft not in table:
        # ToolException is the polite failure: langchain-core turns it into a
        # ToolMessage the model can read and recover from, instead of a traceback
        # that kills the request. Raise it for *expected* failures only.
        msg = f"Unknown aircraft {aircraft!r}. Known: {', '.join(sorted(table))}."
        raise ToolException(msg)
    return table[aircraft]


@tool
def convert_units(
    value: float,
    from_unit: Annotated[Literal["km", "mi", "nm"], "source unit"],
    to_unit: Annotated[Literal["km", "mi", "nm"], "target unit"],
) -> float:
    """Convert a distance between kilometres, statute miles and nautical miles."""
    to_km = {"km": 1.0, "mi": 1.609344, "nm": 1.852}
    return round(value * to_km[from_unit] / to_km[to_unit], 3)


def demo_1_what_a_tool_actually_is() -> None:
    rule("1. A tool is a name + a JSON Schema + a callable")

    print("name       :", get_seat_count.name)
    print("description:", get_seat_count.description.splitlines()[0])
    print("args schema:")
    print(json.dumps(get_seat_count.args_schema.model_json_schema(), indent=2))

    # This is the exact payload shape shipped to an OpenAI-compatible endpoint.
    # Anthropic's differs slightly; the provider package handles the translation.
    wire = convert_to_openai_tool(convert_units)
    print("\non the wire:")
    print(json.dumps(wire, indent=2)[:520] + "\n  ...")

    print("\nDirect call (no model involved):", convert_units.invoke(
        {"value": 100, "from_unit": "km", "to_unit": "nm"}
    ))
    print("\nLesson: the docstring IS the prompt the model reads. A vague docstring")
    print("is a prompt bug, and it will show up as the model calling the wrong tool.")


# ---------------------------------------------------------------------------
# 2. The tool-calling loop, written by hand.
# ---------------------------------------------------------------------------

TOOLS = [get_seat_count, convert_units]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}


def run_tool_loop(model, messages: list, max_turns: int = 6) -> list:
    """The ~20 lines that `create_agent` and every ToolNode wrap.

    Returns the full message history so you can inspect what happened.
    """
    bound = model.bind_tools(TOOLS)
    for turn in range(max_turns):
        ai: AIMessage = bound.invoke(messages)
        messages.append(ai)

        if not ai.tool_calls:
            print(f"  turn {turn}: final answer -> {ai.content}")
            return messages

        print(f"  turn {turn}: model requested {len(ai.tool_calls)} tool call(s)")
        for call in ai.tool_calls:
            name = call["name"]
            print(f"    - {name}({call['args']}) id={call['id']}")
            target = TOOLS_BY_NAME.get(name)
            if target is None:
                # Hallucinated tool name. Do NOT crash -- tell the model.
                messages.append(
                    ToolMessage(
                        content=f"Error: no tool named {name!r}. Available: "
                        f"{', '.join(TOOLS_BY_NAME)}.",
                        tool_call_id=call["id"],
                        status="error",
                    )
                )
                continue
            try:
                # Passing the whole call dict makes langchain-core build the
                # ToolMessage for you, tool_call_id included. Do this, not
                # `tool.invoke(call["args"])` -- that returns a bare value and you
                # have to remember the id yourself.
                messages.append(target.invoke(call))
            except ToolException as exc:
                messages.append(
                    ToolMessage(content=f"Error: {exc}", tool_call_id=call["id"], status="error")
                )
            except ValidationError as exc:
                # Malformed arguments: the model produced JSON that does not match
                # the schema. Same treatment -- hand the error back as context.
                messages.append(
                    ToolMessage(
                        content=f"Invalid arguments: {exc.error_count()} validation error(s). "
                        f"Re-read the schema and try again.",
                        tool_call_id=call["id"],
                        status="error",
                    )
                )
    print("  hit max_turns -- this is your runaway-loop guard, and you need one")
    return messages


def demo_2_happy_path() -> None:
    rule("2. The tool-calling loop: model -> tool -> model")

    model = ScriptedChatModel(
        script=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "get_seat_count", "args": {"aircraft": "A320"},
                     "id": "call_1", "type": "tool_call"},
                    {"name": "convert_units",
                     "args": {"value": 3200, "from_unit": "km", "to_unit": "nm"},
                     "id": "call_2", "type": "tool_call"},
                ],
            ),
            AIMessage(content="An A320 seats 180 and 3200 km is 1727.86 nm."),
        ]
    )
    history = run_tool_loop(
        model,
        [
            SystemMessage("You are a flight-ops assistant."),
            HumanMessage("How many seats on an A320, and what is 3200 km in nautical miles?"),
        ],
    )
    print("\n  final history:")
    for m in history:
        label = type(m).__name__
        body = (str(m.content) or "<empty, carries tool_calls>")[:64]
        print(f"    {label:14s} {body}")
    print("\n  Note the two ToolMessages -- one per tool_call_id. Drop either one and")
    print("  the next request is rejected by the provider as a malformed conversation.")


def demo_3_failure_paths() -> None:
    rule("3. When the model gets it wrong -- three failure modes, three recoveries")

    model = ScriptedChatModel(
        script=[
            # (a) a tool that does not exist
            AIMessage(content="", tool_calls=[
                {"name": "lookup_weather", "args": {"city": "LHR"},
                 "id": "c1", "type": "tool_call"}]),
            # (b) a real tool, but arguments the tool rejects
            AIMessage(content="", tool_calls=[
                {"name": "get_seat_count", "args": {"aircraft": "CONCORDE"},
                 "id": "c2", "type": "tool_call"}]),
            # (c) arguments that do not match the schema at all
            AIMessage(content="", tool_calls=[
                {"name": "convert_units", "args": {"value": "a lot", "from_unit": "km",
                                                   "to_unit": "parsecs"},
                 "id": "c3", "type": "tool_call"}]),
            AIMessage(content="I could not answer that with the tools I have."),
        ]
    )
    history = run_tool_loop(model, [HumanMessage("Do something impossible.")])

    print("\n  what the model was told each time:")
    for m in history:
        if isinstance(m, ToolMessage):
            flag = getattr(m, "status", "success")
            print(f"    [{flag}] {str(m.content)[:88]}")

    print("\n  The rule: a tool failure is CONTEXT, not an exception. Feed the error")
    print("  back as a ToolMessage and let the model retry or give up gracefully.")
    print("  Crashing on a bad tool call turns a recoverable turn into a 500.")


# ---------------------------------------------------------------------------
# 4. Structured output.
# ---------------------------------------------------------------------------


class IncidentReport(BaseModel):
    """A structured summary of an operational incident."""

    service: str = Field(description="Name of the affected service")
    severity: Literal["sev1", "sev2", "sev3"] = Field(description="Declared severity")
    minutes_to_detect: int = Field(ge=0, description="Minutes from onset to detection")
    root_cause: str = Field(description="One sentence, no blame")
    customer_impacting: bool


def demo_4_structured_output() -> None:
    rule("4. with_structured_output -- tool calling wearing a nicer hat")

    model = ScriptedChatModel(
        script=[
            AIMessage(content="", tool_calls=[{
                "name": "IncidentReport",
                "args": {
                    "service": "checkout-api",
                    "severity": "sev2",
                    "minutes_to_detect": 14,
                    "root_cause": "A connection pool was exhausted by a retry storm.",
                    "customer_impacting": True,
                },
                "id": "so_1", "type": "tool_call"}]),
        ]
    )
    structured = model.with_structured_output(IncidentReport)
    report = structured.invoke("Summarise last night's checkout outage.")

    print("returned type:", type(report).__name__)
    print("severity     :", report.severity)
    print("as dict      :", report.model_dump())
    print("\n  Under the hood `with_structured_output(Schema)` on a tool-calling model")
    print("  = bind_tools([Schema], tool_choice=Schema) | PydanticToolsParser.")
    print("  It is tool calling. That is why it fails the same ways tool calling does.")


def demo_5_when_structured_output_lies() -> None:
    rule("5. The failure everyone hits: valid JSON, invalid semantics")

    model = ScriptedChatModel(
        script=[
            AIMessage(content="", tool_calls=[{
                "name": "IncidentReport",
                "args": {
                    "service": "checkout-api",
                    "severity": "catastrophic",   # not in the Literal
                    "minutes_to_detect": -5,      # violates ge=0
                    "root_cause": "unknown",
                    "customer_impacting": "maybe",
                },
                "id": "so_2", "type": "tool_call"}]),
        ]
    )
    try:
        model.with_structured_output(IncidentReport).invoke("Summarise the outage.")
    except ValidationError as exc:
        print(f"  pydantic rejected the model output ({exc.error_count()} errors):")
        for err in exc.errors():
            print(f"    - {'.'.join(str(p) for p in err['loc']):20s} {err['msg']}")

    print("\n  Three things to take away:")
    print("  1. Constraints in the schema (Literal, ge, max_length) are enforced by")
    print("     pydantic AFTER generation, not by the model during it.")
    print("  2. So structured output can and does raise at runtime. Catch it, and")
    print("     decide: retry with the error in the prompt, or degrade.")
    print("  3. `with_structured_output(..., include_raw=True)` returns")
    print("     {'raw', 'parsed', 'parsing_error'} instead of raising -- use it when")
    print("     you want the token usage and the failure in the same object.")

    # Same model, include_raw=True: no exception, you inspect and decide.
    model2 = ScriptedChatModel(script=model.script)
    out = model2.with_structured_output(IncidentReport, include_raw=True).invoke("again")
    print("\n  include_raw=True keys:", sorted(out))
    print("  parsed:", out["parsed"], "| error type:", type(out["parsing_error"]).__name__)


if __name__ == "__main__":
    demo_1_what_a_tool_actually_is()
    demo_2_happy_path()
    demo_3_failure_paths()
    demo_4_structured_output()
    demo_5_when_structured_output_lies()
    rule("Done")
    print("Next: mini_rag_chain.py.")
