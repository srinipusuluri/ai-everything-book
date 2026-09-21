"""
LangGraph fundamentals: typed state, reducers, conditional edges, loops, streaming.

Runs COMPLETELY OFFLINE. No API key, no network, no LLM. Every "model" here is a
deterministic Python function, because the point of this file is the *graph*, not
the model. Swap in a real chat model later and nothing about the topology changes.

Targets LangGraph 1.x (verified against langgraph 1.2.11, langchain-core 1.6.3).

    /Users/srinip/ai-all/.venv/bin/pip install langgraph langchain-core
    /Users/srinip/ai-all/.venv/bin/python code/graph_basics.py

What it demonstrates, in order:
  1. A typed state schema (TypedDict) and why the schema IS the API of your graph.
  2. Reducers: `operator.add` to append, plain overwrite by default.
  3. A conditional edge that routes on a value the graph itself computed.
  4. A cycle (draft -> critique -> draft) with an explicit max-iteration guard,
     plus what `recursion_limit` does when you forget the guard.
  5. Streaming: `updates` vs `values` vs `custom`, i.e. what you show a UI.
  6. Parallel branches -> the InvalidUpdateError you WILL hit in week one.
  7. The Send API for map-reduce fan-out over a list of unknown length.

Docs verified 2026-09:
  https://docs.langchain.com/oss/python/langgraph/graph-api
  https://docs.langchain.com/oss/python/langgraph/streaming
"""
from __future__ import annotations

import operator
from typing import Annotated, Literal

from typing_extensions import TypedDict

from langgraph.config import get_stream_writer
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

rule = lambda t: print("\n" + "=" * 74 + f"\n{t}\n" + "=" * 74)

MAX_REVISIONS = 3
GOOD_ENOUGH = 0.80


# ----------------------------------------------------------------------------
# 1. STATE — the part people under-invest in
# ----------------------------------------------------------------------------
# State design is the real design work. Before you draw a single edge, ask:
# "what does every node need to read, and what is it allowed to write?"
# A node returns a PARTIAL dict; LangGraph merges it into state one channel at a
# time. Each key is a channel, and each channel has a reducer.
#
#   no Annotated  -> LastValue channel: the update REPLACES the old value
#   Annotated[T, fn] -> fn(old, update) decides the merge
#
# Getting this wrong is the #1 source of "why did my list get clobbered".
class DraftState(TypedDict):
    topic: str                                  # read-only in practice
    draft: str                                  # overwritten every revision
    score: float                                # overwritten every critique
    revisions: int                              # overwritten (we count manually)
    critiques: Annotated[list[str], operator.add]   # APPENDED, never replaced


# ----------------------------------------------------------------------------
# 2. NODES — plain functions: state in, partial state out
# ----------------------------------------------------------------------------
# A node is `(state) -> dict`. That is the whole contract. It is not a Runnable,
# not a class, not an agent. Keep them small and pure; the graph is the control
# flow, the node is the work.

_FILLER = ["It depends.", "Broadly speaking.", "In many ways."]


def draft(state: DraftState) -> dict:
    """Deterministic stand-in for 'call the LLM to write a draft'."""
    writer = get_stream_writer()          # custom stream channel; see section 5
    n = state["revisions"]
    writer({"stage": "draft", "attempt": n + 1})

    # Each revision strips one filler phrase and adds one concrete sentence.
    body = [f"{state['topic']} matters because state outlives a single call."]
    body += _FILLER[n:]                                    # fewer each round
    body += [f"Evidence #{i + 1}: measured, not vibed." for i in range(n)]
    return {"draft": " ".join(body), "revisions": n + 1}


def critique(state: DraftState) -> dict:
    """Deterministic 'judge'. Real version: an LLM-as-judge (see ../../../15-ai-evals/)."""
    writer = get_stream_writer()
    text = state["draft"]
    filler_hits = sum(text.count(f) for f in _FILLER)
    evidence = text.count("Evidence #")
    score = round(max(0.0, min(1.0, 0.45 + 0.25 * evidence - 0.12 * filler_hits)), 2)
    note = f"attempt {state['revisions']}: score={score:.2f} filler={filler_hits} evidence={evidence}"
    writer({"stage": "critique", "score": round(score, 2)})
    # `critiques` is appended (operator.add reducer); `score` is overwritten.
    return {"score": score, "critiques": [note]}


def publish(state: DraftState) -> dict:
    return {"draft": state["draft"] + "  [PUBLISHED]"}


# ----------------------------------------------------------------------------
# 3. THE ROUTER — a conditional edge is just a function returning a node name
# ----------------------------------------------------------------------------
# Two independent stopping conditions. The quality gate is the one you want;
# the iteration guard is the one that saves your bill at 3am when the judge
# never says yes. ALWAYS ship both.
def route_after_critique(state: DraftState) -> Literal["draft", "publish"]:
    if state["score"] >= GOOD_ENOUGH:
        return "publish"
    if state["revisions"] >= MAX_REVISIONS:      # the guard. Non-negotiable.
        return "publish"
    return "draft"


def build_writer_graph():
    """
        START -> draft -> critique --(score>=0.8 or revisions>=3)--> publish -> END
                   ^                                |
                   +--------------(else)------------+
    """
    b = StateGraph(DraftState)
    b.add_node("draft", draft)
    b.add_node("critique", critique)
    b.add_node("publish", publish)

    b.add_edge(START, "draft")
    b.add_edge("draft", "critique")
    # The 3rd arg is the path map: it is optional for execution but it is what
    # makes `graph.get_graph()` (and the LangGraph Studio picture) show the
    # cycle instead of a mystery edge. Write it.
    b.add_conditional_edges("critique", route_after_critique, ["draft", "publish"])
    b.add_edge("publish", END)
    return b.compile()


# ----------------------------------------------------------------------------
# 4. PARALLEL BRANCHES — the error everyone hits once
# ----------------------------------------------------------------------------
class FanState(TypedDict):
    tally: Annotated[list[str], operator.add]   # safe under concurrency
    winner: str                                 # NOT safe under concurrency


def _branch(name: str, safe: bool):
    def node(state: FanState) -> dict:
        return {"tally": [name]} if safe else {"tally": [name], "winner": name}
    return node


def build_fanout_graph(safe: bool):
    b = StateGraph(FanState)
    b.add_node("a", _branch("a", safe))
    b.add_node("b", _branch("b", safe))
    b.add_node("join", lambda s: {"tally": ["join"]})
    b.add_edge(START, "a")          # two edges out of START = they run in the
    b.add_edge(START, "b")          # SAME superstep, in parallel
    b.add_edge("a", "join")
    b.add_edge("b", "join")         # join waits for both (Pregel barrier)
    b.add_edge("join", END)
    return b.compile()


# ----------------------------------------------------------------------------
# 5. SEND — fan out over a list whose length you only learn at runtime
# ----------------------------------------------------------------------------
class MapState(TypedDict):
    chunks: list[str]
    summaries: Annotated[list[str], operator.add]


class ChunkState(TypedDict):          # the per-worker state, a different schema
    chunk: str


def dispatch(state: MapState) -> list[Send]:
    """Returns N Sends -> N parallel copies of `summarize`, each with its own state."""
    return [Send("summarize", {"chunk": c}) for c in state["chunks"]]


def summarize(state: ChunkState) -> dict:
    return {"summaries": [f"{state['chunk'][:12]!r} -> {len(state['chunk'])} chars"]}


def build_map_reduce_graph():
    b = StateGraph(MapState)
    b.add_node("summarize", summarize, input_schema=ChunkState)
    b.add_conditional_edges(START, dispatch, ["summarize"])
    b.add_edge("summarize", END)     # the reducer on `summaries` IS the reduce step
    return b.compile()


# ----------------------------------------------------------------------------
# DEMOS
# ----------------------------------------------------------------------------
def demo_loop_and_streaming() -> None:
    rule("1. A LOOP WITH A GUARD  (stream_mode='updates' -- what a UI wants)")
    graph = build_writer_graph()
    init: DraftState = {"topic": "Durable agents", "draft": "", "score": 0.0,
                        "revisions": 0, "critiques": []}

    # `updates` yields {node_name: partial_update} after every node finishes.
    # This is the cheap, high-signal stream: it is the diff, not the whole world.
    for step, chunk in enumerate(graph.stream(init, stream_mode="updates"), 1):
        for node, update in chunk.items():
            shown = {k: (v[:48] + "..." if isinstance(v, str) and len(v) > 48 else v)
                     for k, v in update.items()}
            print(f"  step {step:>2}  {node:<9} {shown}")

    rule("2. THE SAME RUN AS 'values' (full state) AND 'custom' (your own events)")
    # Ask for several modes at once and you get (mode, payload) tuples back.
    for mode, payload in graph.stream(init, stream_mode=["values", "custom"]):
        if mode == "custom":
            print(f"  custom  {payload}")
        else:
            print(f"  values  revisions={payload['revisions']} score={payload['score']:.2f}")

    final = graph.invoke(init)
    print(f"\n  final score : {final['score']:.2f} after {final['revisions']} revisions")
    print(f"  critiques   : {len(final['critiques'])} appended (reducer worked)")
    for c in final["critiques"]:
        print(f"      - {c}")
    print(f"  draft       : {final['draft'][:72]}...")
    print("\n  Note `score` was OVERWRITTEN each round while `critiques` GREW.")
    print("  That difference is one word of Annotated. That is channel semantics.")


def demo_recursion_limit() -> None:
    rule("3. WHAT HAPPENS WITHOUT A GUARD: recursion_limit")
    # Same graph, but we lie about the guard by demanding a score nobody reaches.
    b = StateGraph(DraftState)
    b.add_node("draft", draft)
    b.add_node("critique", critique)
    b.add_edge(START, "draft")
    b.add_edge("draft", "critique")
    b.add_conditional_edges("critique", lambda s: "draft", ["draft"])   # never exits
    runaway = b.compile()
    init: DraftState = {"topic": "x", "draft": "", "score": 0.0,
                        "revisions": 0, "critiques": []}
    try:
        runaway.invoke(init, config={"recursion_limit": 8})
    except GraphRecursionError as exc:
        print(f"  GraphRecursionError: {str(exc).splitlines()[0]}")
    print("  recursion_limit counts SUPERSTEPS, not tokens and not node calls.")
    print("  It is a circuit breaker, not a design. Put a counter in your state.")


def demo_parallel_conflict() -> None:
    rule("4. PARALLEL BRANCHES: reducer vs. no reducer")
    ok = build_fanout_graph(safe=True).invoke({"tally": [], "winner": ""})
    print(f"  with reducer only        -> tally={ok['tally']}")
    try:
        build_fanout_graph(safe=False).invoke({"tally": [], "winner": ""})
    except Exception as exc:                       # InvalidUpdateError
        print(f"  two writes to 'winner'   -> {type(exc).__name__}: "
              f"{str(exc).splitlines()[0]}")
    print("  Fix = give the channel a reducer, or make only one branch own it.")


def demo_send() -> None:
    rule("5. MAP-REDUCE WITH Send (fan-out width decided at runtime)")
    docs = ["retrieval augmented generation", "graphs beat chains", "state is the product"]
    out = build_map_reduce_graph().invoke({"chunks": docs, "summaries": []})
    for s in out["summaries"]:
        print(f"  {s}")
    print("  Send(node, state) creates one task per item with its OWN state schema.")
    print("  The reduce step is just the reducer on the parent's channel.")


if __name__ == "__main__":
    demo_loop_and_streaming()
    demo_recursion_limit()
    demo_parallel_conflict()
    demo_send()
    rule("TAKEAWAY")
    print("""  A LangGraph app is three decisions, in this order:
    1. What is in state, and what is each channel's reducer?
    2. Which node is allowed to write which channel?
    3. Where does control branch, and what STOPS it?
  Nodes are the easy part. If your graph misbehaves, the bug is in 1 or 3.""")
