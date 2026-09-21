# 🕸️ Module 07 — Agentic AI Systems

> **Where you are:** Stop 7 of 16. **Time:** ~18–22 hours · **Prereq:** [Module 06 — AI Agents](../06-ai-agents/) — non-negotiable.

Module 06 gave a single agent a loop, a set of tools, and a memory. This module asks the next question:
what happens when one loop isn't enough — when you put two or more agents in a system together? Multi-agent
systems are not "Module 06 but bigger." They are a different design problem: topology, communication,
coordination failure, and a cost curve that punishes you for reaching for them by reflex. This module covers
the theory of *how* agents should be arranged and *when* they should be arranged at all — the mechanics of
any specific framework (LangGraph, CrewAI, AutoGen) live in [Module 16](../16-ai-tech-stack/).

---

## Learning objectives

By the end of this module you can:

1. Place any system on the autonomy spectrum (single call → tool agent → multi-agent → autonomous
   long-runner) and argue for the *least* autonomous point that solves the problem.
2. Draw and evaluate the five core multi-agent topologies — supervisor, peer hand-off, hierarchical,
   debate/vote, pipeline — and name each one's specific failure mode from memory.
3. Quantify the token-cost multiplier of multi-agent systems and defend, with numbers, when it's worth paying.
4. Explain the three communication patterns (blackboard, message passing, shared state) and where A2A-style
   protocols sit relative to MCP.
5. Diagnose the five coordination failure modes unique to multi-agent systems (deadlock, information loss,
   hallucination poisoning, redundant work, debate thrashing) from a trace.
6. Choose a human-in-the-loop vs. human-on-the-loop oversight posture for a given autonomy level, with a
   concrete trigger condition.
7. Apply a decision framework to classify a real request as single-agent, multi-agent, or a deterministic
   pipeline with an LLM step — and defend the call.

## Suggested path

| # | Do this | File | Time |
|---|---|---|---|
| 1 | Autonomy spectrum + the five topologies | [notes/01-autonomy-spectrum-and-topologies.md](notes/01-autonomy-spectrum-and-topologies.md) | 4h |
| 2 | Cost, protocols, failure modes, control, evals | [notes/02-coordination-control-and-evaluation.md](notes/02-coordination-control-and-evaluation.md) | 5h |
| 3 | Run and read the topology simulator | [code/topology_simulator.py](code/topology_simulator.py) | 2h |
| 4 | Run and read the hand-off information-loss demo | [code/handoff_information_loss.py](code/handoff_information_loss.py) | 1h |
| 5 | Slides | [slides/](slides/) | 1h |
| 6 | Lab exercises | [lab/EXERCISES.md](lab/EXERCISES.md) | 6h |
| 7 | Papers | [papers/PAPERS.md](papers/PAPERS.md) | 3h |

## The 18 terms you must own

`autonomy spectrum` · `orchestrator-worker (supervisor)` · `peer hand-off / swarm` · `hierarchical
teams-of-teams` · `debate / parallel-then-vote` · `pipeline (assembly-line)` · `context isolation` ·
`hand-off summarization loss` · `blackboard / scratchpad` · `structured message passing` · `shared state
(channels)` · `A2A (Agent2Agent)` · `deadlock / livelock` · `hallucination poisoning` · `human-in-the-loop
(HITL)` · `human-on-the-loop (HOTL)` · `goal drift` · `budget governor`

## Exit check ✅

Given a real (or realistic) automation request, you can produce a one-page decision memo: where it sits on
the autonomy spectrum, which topology (if any) fits the problem shape, the token-cost estimate versus a
single-agent baseline, the two most likely coordination failure modes and how you'd detect them, and whether
the system needs HITL or HOTL oversight — with a named trigger condition for escalation.
