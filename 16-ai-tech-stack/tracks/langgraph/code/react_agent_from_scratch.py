"""
A ReAct agent built as an explicit LangGraph graph -- no prebuilt, no network.

Runs COMPLETELY OFFLINE. The "LLM" is `ScriptedModel`: a deterministic policy that
inspects the message list and emits tool calls, exactly like a real tool-calling
model would. Everything else -- message state, the add_messages reducer, the
agent/tools cycle, tool errors, parallel tool calls, the step guard -- is the real
LangGraph API, unchanged.

Targets LangGraph 1.x (verified against langgraph 1.2.11, langchain-core 1.6.3).

    /Users/srinip/ai-all/.venv/bin/pip install langgraph langchain-core
    /Users/srinip/ai-all/.venv/bin/python code/react_agent_from_scratch.py

The graph:

        START -> agent -> (tool calls?) -- yes --> tools --+
                   ^                                       |
                   +---------------------------------------+
                            |
                            no / budget spent
                            v
                           END

Why build it by hand when `create_agent` exists? Because the prebuilt is 40 lines
of this file, and the day you need an approval gate between `agent` and `tools`,
or a validator node, or a different model per step, you need to know where to cut.

Docs verified 2026-09:
  https://docs.langchain.com/oss/python/langgraph/graph-api
  https://docs.langchain.com/oss/python/langchain/agents
  ReAct paper: https://arxiv.org/abs/2210.03629
"""
from __future__ import annotations

import json
from typing import Annotated, Any, Literal

from typing_extensions import TypedDict

from langchain_core.messages import (AIMessage, AnyMessage, HumanMessage,
                                     SystemMessage, ToolMessage)
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

rule = lambda t: print("\n" + "=" * 74 + f"\n{t}\n" + "=" * 74)

MAX_TOOL_STEPS = 6          # the budget. An agent without one is a billing incident.


# ----------------------------------------------------------------------------
# STATE
# ----------------------------------------------------------------------------
# `add_messages` is the reducer that makes message-based agents work. It is not
# `operator.add`: it appends new messages, and it REPLACES an existing message
# when the update carries the same `id`. That is what lets you edit history
# (redact a message, patch a tool call) without rebuilding the list.
class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    tool_steps: int          # our own loop counter -- see route_from_agent


# ----------------------------------------------------------------------------
# TOOLS -- plain functions plus a hand-written schema
# ----------------------------------------------------------------------------
_ORDERS = {
    "A-1001": {"customer": "Acme Ltd", "subtotal": 240.00, "shipping": 12.50},
    "A-1002": {"customer": "Globex", "subtotal": 99.00, "shipping": 0.00},
}


def lookup_order(order_id: str) -> dict:
    """Raises on a bad id -- on purpose. Half of agent engineering is error paths."""
    if order_id not in _ORDERS:
        raise KeyError(f"no such order {order_id!r}; ids look like 'A-1001'")
    return _ORDERS[order_id]


def add_numbers(a: float, b: float) -> float:
    return round(float(a) + float(b), 2)


def tax_rate(country: str) -> float:
    return {"UK": 0.20, "DE": 0.19, "US": 0.00}.get(country.upper(), 0.0)


TOOLS = {"lookup_order": lookup_order, "add_numbers": add_numbers, "tax_rate": tax_rate}


# ----------------------------------------------------------------------------
# THE MODEL -- deterministic, offline, and honest about being a fake
# ----------------------------------------------------------------------------
class ScriptedModel:
    """A tool-calling 'model' whose policy is a lookup on what it has already seen.

    A real model returns an AIMessage with `.tool_calls` populated; so does this.
    Substituting `ChatAnthropic(...).bind_tools(tools)` changes this class and
    nothing else in the file -- which is the point of the exercise.
    """

    def __init__(self) -> None:
        self.calls = 0

    @staticmethod
    def _last_tool_results(messages: list[AnyMessage]) -> list[ToolMessage]:
        out: list[ToolMessage] = []
        for m in reversed(messages):
            if isinstance(m, ToolMessage):
                out.append(m)
            elif isinstance(m, AIMessage):
                break
        return list(reversed(out))

    def invoke(self, messages: list[AnyMessage]) -> AIMessage:
        self.calls += 1
        results = self._last_tool_results(messages)
        seen = {m.name for m in messages if isinstance(m, ToolMessage)}
        errored = [m for m in results if m.status == "error"]

        # Turn 1: no observations yet -> plan and call a tool. Note the typo:
        # the model guesses an order id and gets it wrong, like models do.
        if not results:
            return self._call("lookup_order", {"order_id": "A-100"},
                              think="I need the order before I can total it.")

        # Turn 2: the tool failed. A real model reads the error text and retries.
        # This only works if your tools node RETURNS the error instead of raising.
        if errored:
            return self._call("lookup_order", {"order_id": "A-1001"},
                              think="That id was wrong. The error shows the format.")

        # Turn 3: two independent facts -> ask for both in ONE assistant turn.
        # Parallel tool calls halve your latency and your model spend.
        if "add_numbers" not in seen:
            order = json.loads(results[0].content)
            return AIMessage(
                content="Summing the line items and fetching the rate in parallel.",
                tool_calls=[
                    {"name": "add_numbers",
                     "args": {"a": order["subtotal"], "b": order["shipping"]},
                     "id": f"call_{self.calls}_a"},
                    {"name": "tax_rate", "args": {"country": "UK"},
                     "id": f"call_{self.calls}_b"},
                ],
            )

        # Turn 4: enough observations -> answer, with NO tool_calls. An AIMessage
        # without tool calls is the only thing that ends a ReAct loop.
        by_name = {m.name: m.content for m in results}
        net = float(by_name["add_numbers"])
        rate = float(by_name["tax_rate"])
        total = round(net * (1 + rate), 2)
        return AIMessage(
            content=(f"Order A-1001 (Acme Ltd): goods + shipping = {net:.2f}, "
                     f"UK VAT at {rate:.0%} -> total {total:.2f}.")
        )

    def _call(self, name: str, args: dict[str, Any], *, think: str) -> AIMessage:
        return AIMessage(content=think,
                         tool_calls=[{"name": name, "args": args,
                                      "id": f"call_{self.calls}"}])


# ----------------------------------------------------------------------------
# NODES
# ----------------------------------------------------------------------------
def make_agent_node(model: ScriptedModel):
    def agent(state: AgentState) -> dict:
        reply = model.invoke(state["messages"])
        return {"messages": [reply]}        # add_messages appends it
    return agent


def tools_node(state: AgentState) -> dict:
    """Execute every tool call on the last AIMessage. Never let a tool raise.

    The contract that matters: one ToolMessage per tool_call_id, always. If you
    drop one, the next model call fails schema validation at the provider. If you
    let the exception propagate, the graph dies and the agent loses the chance to
    recover from a mistake it is perfectly capable of fixing.
    """
    last = state["messages"][-1]
    out: list[ToolMessage] = []
    for call in last.tool_calls:
        try:
            result = TOOLS[call["name"]](**call["args"])
            out.append(ToolMessage(content=json.dumps(result), name=call["name"],
                                   tool_call_id=call["id"]))
        except Exception as exc:                       # deliberate blanket catch
            out.append(ToolMessage(
                content=f"{type(exc).__name__}: {exc}",
                name=call["name"], tool_call_id=call["id"],
                status="error",                        # the model can see this
            ))
    return {"messages": out, "tool_steps": state["tool_steps"] + 1}


def route_from_agent(state: AgentState) -> Literal["tools", "__end__"]:
    """The whole 'agent loop' is this function. Three exits, not one."""
    last = state["messages"][-1]
    if not getattr(last, "tool_calls", None):
        return END                                     # the model is done
    if state["tool_steps"] >= MAX_TOOL_STEPS:
        return END                                     # the budget is done
    return "tools"


def build_agent(model: ScriptedModel):
    b = StateGraph(AgentState)
    b.add_node("agent", make_agent_node(model))
    b.add_node("tools", tools_node)
    b.add_edge(START, "agent")
    b.add_conditional_edges("agent", route_from_agent, ["tools", END])
    b.add_edge("tools", "agent")          # <- the cycle. A DAG cannot express this.
    return b.compile()


# ----------------------------------------------------------------------------
# DEMOS
# ----------------------------------------------------------------------------
def pretty(m: AnyMessage) -> str:
    if isinstance(m, HumanMessage):
        return f"human     | {m.content}"
    if isinstance(m, SystemMessage):
        return f"system    | {m.content}"
    if isinstance(m, ToolMessage):
        flag = "ERROR" if m.status == "error" else "ok   "
        return f"tool  {flag}| {m.name}: {m.content}"
    calls = getattr(m, "tool_calls", None)
    if calls:
        rendered = ", ".join(f"{c['name']}({json.dumps(c['args'])})" for c in calls)
        return f"ai (act)  | {m.content}\n          |   -> {rendered}"
    return f"ai (final)| {m.content}"


def demo_run() -> None:
    rule("1. ONE FULL ReAct RUN, streamed as it happens")
    model = ScriptedModel()
    graph = build_agent(model)
    init: AgentState = {
        "messages": [
            SystemMessage(content="You are a billing assistant. Use tools; do not guess."),
            HumanMessage(content="What does Acme owe on order A-1001, VAT included?"),
        ],
        "tool_steps": 0,
    }
    for m in init["messages"]:
        print("  " + pretty(m))
    # Stream both modes: `updates` to narrate, `values` to keep the final state
    # without paying for a second run.
    final: AgentState = init
    for mode, payload in graph.stream(init, stream_mode=["updates", "values"]):
        if mode == "values":
            final = payload
            continue
        for node, update in payload.items():
            for m in update.get("messages", []):
                print(f"  [{node:<5}] " + pretty(m))

    print(f"\n  model calls : {model.calls}")
    print(f"  tool steps  : {final['tool_steps']} of a {MAX_TOOL_STEPS} budget")
    print(f"  messages    : {len(final['messages'])}")
    print("  Four model calls, three tool steps, one recovered error, zero orchestration"
          "\n  code outside the graph. That ratio is the reason this framework exists.")


def demo_error_recovery() -> None:
    rule("2. WHY THE tools NODE MUST SWALLOW EXCEPTIONS")
    bad = AIMessage(content="", tool_calls=[{"name": "lookup_order",
                                             "args": {"order_id": "NOPE"},
                                             "id": "x1"}])
    out = tools_node({"messages": [bad], "tool_steps": 0})
    print("  returned to the model instead of crashing the graph:")
    print("    " + pretty(out["messages"][0]))
    print("""
  Three ways to handle a failing tool, worst to best:
    (a) let it raise           -> the run dies; the user sees a 500
    (b) retry_policy=RetryPolicy(...) on add_node -> right for FLAKY tools
                                  (timeouts, 502s) and useless for wrong ARGUMENTS
    (c) return the error as a ToolMessage(status="error") -> the model fixes its
        own argument, which is the failure mode you actually see in production
  Use (b) and (c) together. They solve different problems.""")


def demo_no_budget() -> None:
    rule("3. THE STEP BUDGET, REMOVED")
    print("""  Set MAX_TOOL_STEPS = 0 and route_from_agent returns END on the first
  tool request: the agent answers with whatever it has. Set it to 10**6 and a
  model that keeps re-calling a broken tool loops until `recursion_limit`
  (default 25 supersteps) stops it -- with 25 model calls already billed.

  The budget belongs in STATE, not in recursion_limit, because state is the
  thing you can inspect, log, and show to the user: "stopped after 6 tool calls".""")


if __name__ == "__main__":
    demo_run()
    demo_error_recovery()
    demo_no_budget()
    rule("WHEN TO USE THE PREBUILT INSTEAD")
    print("""  `langchain.agents.create_agent(model, tools)` builds this exact graph for you
  (and in LangGraph 1.x it supersedes the deprecated
  `langgraph.prebuilt.create_react_agent`). Reach for the prebuilt when the loop
  IS the application. Hand-roll -- this file -- as soon as you need any of:

    - an approval interrupt between `agent` and `tools`   (see checkpoint_and_interrupt.py)
    - a validation / policy node that can reject a tool call before it runs
    - a different model per node (cheap router, expensive executor)
    - state that is not just `messages` (a plan, a budget, a scratchpad, a cursor)
    - deterministic pre/post steps you do not want the model to be able to skip

  The prebuilt is a starting point, not a ceiling. Everything it does is edges.""")
