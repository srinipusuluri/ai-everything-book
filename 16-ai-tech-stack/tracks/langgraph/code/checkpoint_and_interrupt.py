"""
Persistence, human approval and time travel -- the three things a loop cannot do.

Runs COMPLETELY OFFLINE. No API key, no network, no LLM. A refund-approval
workflow stands in for a real agent: propose -> HUMAN GATE -> execute -> notify.

Targets LangGraph 1.x (verified against langgraph 1.2.11, langgraph-checkpoint 4.2.0,
langgraph-checkpoint-sqlite 3.1.1).

    /Users/srinip/ai-all/.venv/bin/pip install langgraph langgraph-checkpoint-sqlite
    /Users/srinip/ai-all/.venv/bin/python code/checkpoint_and_interrupt.py

Sections:
  1. A checkpointer + thread_id = a resumable conversation.
  2. interrupt() -- the graph stops mid-node and hands control to a human.
  3. Command(resume=...) -- approve, reject, or EDIT the proposed action.
  4. The re-execution trap: resuming re-runs the node from the top. Idempotency.
  5. get_state_history() + checkpoint_id -- time travel, and forking an alternate run.
  6. update_state() -- rewriting the past as if a node had written it.
  7. SqliteSaver -- the same thread surviving a fresh process.

Docs verified 2026-09:
  https://docs.langchain.com/oss/python/langgraph/persistence
  https://docs.langchain.com/oss/python/langgraph/interrupts
  https://docs.langchain.com/oss/python/langgraph/durable-execution
"""
from __future__ import annotations

import operator
import os
import tempfile
from typing import Annotated

from typing_extensions import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

rule = lambda t: print("\n" + "=" * 74 + f"\n{t}\n" + "=" * 74)

# A module-level list standing in for "something that touches the outside world":
# a Stripe call, an email, a row insert. Watch how many times it gets appended to.
SIDE_EFFECTS: list[str] = []


class RefundState(TypedDict):
    ticket: str
    claim: float
    proposed: float
    decision: str
    audit: Annotated[list[str], operator.add]


# ----------------------------------------------------------------------------
# NODES
# ----------------------------------------------------------------------------
def assess(state: RefundState) -> dict:
    """Policy engine (a model, in real life). Caps the refund at 200."""
    proposed = min(state["claim"], 200.00)
    return {"proposed": proposed,
            "audit": [f"assess: claim={state['claim']:.2f} -> proposed={proposed:.2f}"]}


def approval_gate(state: RefundState) -> dict:
    """The human-in-the-loop node.

    IMPORTANT: everything above the `interrupt()` call runs AGAIN when the graph
    resumes. LangGraph does not freeze a Python stack frame; it replays the node
    from the top and substitutes the resume value where interrupt() was raised.
    So the line below is a bug you can watch happen in section 4.
    """
    SIDE_EFFECTS.append(f"notified approver about {state['ticket']}")   # <- runs twice

    decision = interrupt({                      # execution stops HERE
        "question": "Approve this refund?",
        "ticket": state["ticket"],
        "proposed": state["proposed"],
        "options": ["approve", "reject", "edit"],
    })                                          # resumes with Command(resume=...)

    if isinstance(decision, dict) and decision.get("action") == "edit":
        amount = float(decision["amount"])
        return {"decision": "approved (edited)", "proposed": amount,
                "audit": [f"human EDITED {state['proposed']:.2f} -> {amount:.2f}"]}
    if decision == "approve":
        return {"decision": "approved", "audit": ["human approved as proposed"]}
    return {"decision": "rejected", "proposed": 0.0, "audit": ["human rejected"]}


def execute(state: RefundState) -> dict:
    if state["proposed"] <= 0:
        return {"audit": ["execute: nothing to pay"]}
    return {"audit": [f"execute: paid {state['proposed']:.2f} for {state['ticket']}"]}


def build(checkpointer):
    """
        START -> assess -> approval_gate -[interrupt]-> execute -> END
    """
    b = StateGraph(RefundState)
    b.add_node("assess", assess)
    b.add_node("approval_gate", approval_gate)
    b.add_node("execute", execute)
    b.add_edge(START, "assess")
    b.add_edge("assess", "approval_gate")
    b.add_edge("approval_gate", "execute")
    b.add_edge("execute", END)
    # No checkpointer -> no interrupts, no resume, no time travel. This one
    # argument is the difference between a script and a durable workflow.
    return b.compile(checkpointer=checkpointer)


def new_claim(ticket: str, claim: float) -> RefundState:
    return {"ticket": ticket, "claim": claim, "proposed": 0.0,
            "decision": "", "audit": []}


# ----------------------------------------------------------------------------
# 1 + 2 + 3. INTERRUPT, INSPECT, RESUME
# ----------------------------------------------------------------------------
def demo_interrupt_and_resume():
    rule("1. RUN UNTIL THE HUMAN GATE, THEN STOP")
    graph = build(InMemorySaver())
    cfg = {"configurable": {"thread_id": "ticket-4471"}}

    result = graph.invoke(new_claim("ticket-4471", 350.00), config=cfg)
    # An interrupted run RETURNS. It does not block a thread, hold a socket, or
    # keep a process alive. The pending question is in the result payload.
    payload = result["__interrupt__"][0].value
    print(f"  graph returned with __interrupt__: {payload}")

    snap = graph.get_state(cfg)
    print(f"  next node(s) to run : {snap.next}")
    print(f"  checkpoint id       : {snap.config['configurable']['checkpoint_id']}")
    print(f"  state so far        : proposed={snap.values['proposed']:.2f}")
    print("\n  The process could now exit. A week later, a different machine can"
          "\n  load thread 'ticket-4471' and continue. That is the whole pitch.")

    rule("2. RESUME WITH AN EDIT (approve / reject / edit are all one API)")
    done = graph.invoke(Command(resume={"action": "edit", "amount": 175.00}), config=cfg)
    for line in done["audit"]:
        print(f"    {line}")
    print(f"  decision: {done['decision']}  paid: {done['proposed']:.2f}")
    return graph, cfg


def demo_three_decisions():
    rule("3. THE SAME GATE, THREE DIFFERENT HUMANS (separate threads)")
    graph = build(InMemorySaver())
    for i, (resume_value, label) in enumerate([
        ("approve", "approve"),
        ("reject", "reject"),
        ({"action": "edit", "amount": 42.00}, "edit to 42.00"),
    ]):
        cfg = {"configurable": {"thread_id": f"t-{i}"}}
        graph.invoke(new_claim(f"ticket-90{i}", 500.00), config=cfg)
        out = graph.invoke(Command(resume=resume_value), config=cfg)
        print(f"  {label:<14} -> decision={out['decision']:<18} paid={out['proposed']:7.2f}")
    print("\n  Threads are isolated by thread_id. Two users, two threads, one graph"
          "\n  object, zero shared mutable state. Scale horizontally by thread.")


# ----------------------------------------------------------------------------
# 4. THE RE-EXECUTION TRAP
# ----------------------------------------------------------------------------
def demo_side_effects():
    rule("4. RESUMING RE-RUNS THE NODE FROM THE TOP (idempotency homework)")
    for line in SIDE_EFFECTS:
        print(f"    {line}")
    print(f"  'notify approver' fired {len(SIDE_EFFECTS)} times for 4 gate entries.")
    print("""
  Every line above `interrupt()` executes again on resume. Three fixes:
    - Move side effects BELOW the interrupt, or into their own node.
    - Make them idempotent: key on (thread_id, checkpoint_id, request_id).
    - Wrap them in @task (the functional API) so completed work is memoised
      against the checkpoint and not repeated.
  The same rule governs crash recovery: a node that died halfway is re-run
  whole. Design nodes so running one twice is boring.""")


# ----------------------------------------------------------------------------
# 5 + 6. TIME TRAVEL
# ----------------------------------------------------------------------------
def demo_time_travel(graph, cfg):
    rule("5. TIME TRAVEL: get_state_history() + checkpoint_id")
    history = list(graph.get_state_history(cfg))
    print("  newest first:")
    for snap in history:
        cid = snap.config["configurable"]["checkpoint_id"][-12:]
        nxt = snap.next or ("END",)
        print(f"    ...{cid}  next={str(nxt):<20} "
              f"proposed={snap.values.get('proposed', 0):7.2f} "
              f"steps={len(snap.values.get('audit', []))}")

    head_cfg = history[0].config          # remember the real ending, see below
    pending = next(s for s in reversed(history) if s.next == ("approval_gate",))
    short = lambda c: "..." + c["configurable"]["checkpoint_id"][-12:]

    # REPLAY vs. FORK -- the distinction that costs people an afternoon.
    # Invoking AT an old checkpoint replays it, and a task that already completed
    # replays its RECORDED result. You get the same answer, deliberately:
    # that is how crash recovery avoids paying for the same LLM call twice.
    print(f"\n  replaying {short(pending.config)} with resume='reject':")
    replayed = graph.invoke(Command(resume="reject"), config=pending.config)
    print(f"    decision={replayed['decision']}  <- the RECORDED answer, not ours")

    # To genuinely change the past, fork first: update_state with no values
    # writes a fresh checkpoint at that point, without the recorded writes.
    fork_cfg = graph.update_state(pending.config, None)
    print(f"  forked to {short(fork_cfg)}, then resume='reject':")
    forked = graph.invoke(Command(resume="reject"), config=fork_cfg)
    print(f"    decision={forked['decision']}  paid={forked['proposed']:.2f}")
    original = graph.get_state(head_cfg).values
    print(f"  original branch {short(head_cfg)} still says: "
          f"decision={original['decision']} paid={original['proposed']:.2f}")
    print("""
  Both branches live on ONE thread; get_state(thread) returns the newest
  checkpoint, so hold on to checkpoint_ids if you care about a specific branch.
  This is what "debuggable agent" means in practice: replay from any step,
  change one input, compare outcomes. The checkpoint list is also the audit
  trail an auditor asks for -- see ../../../12-ai-governance/.""")

    rule("6. update_state(): editing history as if a node had written it")
    edit_cfg = graph.update_state(fork_cfg,
                                  {"audit": ["manual: reopened by ops"],
                                   "proposed": 60.00},
                                  as_node="assess")
    snap = graph.get_state(edit_cfg)
    print(f"  wrote a new checkpoint {short(edit_cfg)}")
    print(f"  next={snap.next}  proposed={snap.values['proposed']:.2f}")
    print(f"  audit tail: {snap.values['audit'][-1]}")
    print("  `as_node` decides WHICH edges fire next -- it is a write, not a patch.")


# ----------------------------------------------------------------------------
# 7. REAL DURABILITY
# ----------------------------------------------------------------------------
def demo_sqlite():
    rule("7. SqliteSaver: the thread outlives the graph object")
    path = os.path.join(tempfile.mkdtemp(), "refunds.sqlite")
    cfg = {"configurable": {"thread_id": "ticket-7788"}}

    with SqliteSaver.from_conn_string(path) as saver:     # "process A"
        g1 = build(saver)
        g1.invoke(new_claim("ticket-7788", 90.00), config=cfg)
        print(f"  process A: paused at {g1.get_state(cfg).next}, db={os.path.basename(path)}")
    del g1

    with SqliteSaver.from_conn_string(path) as saver:     # "process B", fresh objects
        g2 = build(saver)
        snap = g2.get_state(cfg)
        print(f"  process B: rehydrated thread, next={snap.next}, "
              f"proposed={snap.values['proposed']:.2f}")
        out = g2.invoke(Command(resume="approve"), config=cfg)
        print(f"  process B: resumed and finished -> {out['audit'][-1]}")
    print(f"""
  Swap SqliteSaver for PostgresSaver (`pip install langgraph-checkpoint-postgres`,
  then `saver.setup()` once) and this is a production deployment. Checkpointer
  choice, honestly:
    InMemorySaver  - tests and demos only; dies with the process
    SqliteSaver    - single-node apps, local agents, CLI tools
    PostgresSaver  - anything with more than one replica or an SLA
  Cost of persistence: one write per superstep. Tune it with
  `durability="exit" | "async" | "sync"` on invoke/stream -- "sync" is the safe
  default, "async" trades a crash window for latency, "exit" writes once at the
  end and gives up mid-run recovery.""")


if __name__ == "__main__":
    graph, cfg = demo_interrupt_and_resume()
    demo_three_decisions()
    demo_side_effects()
    demo_time_travel(graph, cfg)
    demo_sqlite()
    rule("TAKEAWAY")
    print("""  Persistence is not a feature you add later. It is the thing that turns
  "an LLM in a while loop" into a workflow you can pause, approve, audit,
  resume after a deploy, and explain to a regulator. If your agent touches
  money, health, or anything you would have to un-do, the approval gate is
  the product -- and `interrupt()` is four lines.""")
