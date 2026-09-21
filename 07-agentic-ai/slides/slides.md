---
marp: true
theme: default
paginate: true
style: |
  section h1 { color: #84CC16; }
  section { font-size: 24px; }
---

# Agentic AI Systems

### Topology, autonomy, and the cost of coordination

**Module 07** · AI End-to-End Learning Track

---

## The spectrum of autonomy

- A single LLM call -> a tool-using agent (Module 06) -> multi-agent -> fully autonomous
- Each point is appropriate for a different task shape, not a maturity ladder
- More autonomy is not the goal -- the RIGHT autonomy for the task is the goal
- Warning: reflexively maximizing autonomy adds cost and failure surface for nothing

<!-- speaker note: Set the tone early: this module argues for restraint, not for building the most agentic thing possible. -->

---

## Five multi-agent topologies

| Topology | Fits | Failure mode |
|---|---|---|
| Supervisor/worker | clean sub-task decomposition | supervisor becomes a context bottleneck |
| Peer hand-off (swarm) | conversational triage/escalation | hand-off loops, no central trace |
| Hierarchical teams | org-chart-shaped task trees | cost/latency compound with depth |
| Debate / vote | high-stakes single decisions | thrashing, expensive for simple tasks |
| Pipeline | fixed stage order, known upfront | no recovery if a stage assumption breaks |


<!-- speaker note: Each has a diagram in notes/01 section 2. Draw the supervisor one live -- it's the one people default to. -->

---

## The token-cost multiplication

> **Anthropic's own multi-agent research system used roughly 15x the tokens of a single chat.**

- Worth it there: the task was genuinely parallelizable, high-value research
- Absurd for a support bot answering 'what are your hours'
- Every extra agent is a round trip, a serialization boundary, a place to lose information

<!-- speaker note: This number does the most work in the whole module. Say it early and often. -->

---

## The honest position

- Most 'multi-agent' systems should be one agent with better tools
- Use multiple agents only when at least one is true:
-   - one agent's context genuinely does not fit
-   - subtasks are independent and parallelizable
-   - different agents need different permissions or data residency
- Do NOT split because the org chart has three teams

<!-- speaker note: Cognition's 'Don't Build Multi-Agents' is the dissenting essay worth reading alongside Anthropic's write-up -- link in resources. -->

---

## Context isolation vs. hand-off loss

- The benefit you're paying for: each agent's context stays small and focused
- The cost you don't see coming: what gets DROPPED when state is summarized for hand-off
- code/handoff_information_loss.py makes this concrete: a critical detail buried in
-   paragraph 3 of a support ticket vanishes in the hand-off summary
- Neither agent knows it happened -- the receiving agent doesn't know what it wasn't told

<!-- speaker note: Run the demo script live if possible. This is the single most viscerally convincing argument in the module. -->

---

## Communication: MCP vs. A2A

- Shared scratchpad, structured message passing, or shared state (a graph's channels)
- MCP (Module 09) connects an agent to TOOLS and DATA
- A2A-style protocols connect AGENT to AGENT -- a different problem
- Don't confuse a tool-calling interface with an inter-agent communication protocol

<!-- speaker note: This distinction is one people get wrong constantly. Say it plainly. -->

---

## Coordination failure modes unique to multi-agent

| Failure | What it looks like |
|---|---|
| Deadlock / livelock | two hand-off agents pass the task back and forth forever |
| Information loss | a hand-off summary drops the fact that mattered |
| Poisoned downstream | one agent's hallucination becomes another's 'fact' |
| Redundant work | two agents solve the same sub-problem independently |
| Debate thrashing | agents disagree and never converge on a vote |


---

## Autonomy vs. controllability

- As autonomy increases, predictability decreases -- a fundamental tension
- This tension is exactly what governance frameworks exist to manage (Module 12)
- Human-IN-the-loop: a person approves before an action executes
- Human-ON-the-loop: a person monitors and can intervene, but doesn't gate every step
- Pick the posture based on reversibility and blast radius, not by default

---

## Long-running autonomous agents

- Continuous operation needs checkpointing and resumability (mechanics: Module 16 LangGraph)
- Goal drift over long horizons is real -- re-anchor to the original objective periodically
- A budget/resource governor is a REQUIRED safety mechanism, not an optimization
- An agent with no spend ceiling is an agent with no ceiling, period

---

## Evaluating agentic systems

- System-level task success, not just per-agent step accuracy
- Simulation environments and sandboxed evals let you test without real-world side effects
- Multi-agent eval is a genuinely open research problem -- say so honestly
- See Module 15 for the statistical rigor this needs and usually doesn't get

---

## The decision framework

> **Single-agent, multi-agent, or a deterministic pipeline with one LLM step?**

- Fixed stage order known upfront -> deterministic pipeline. Cheaper AND more robust
- One agent, richer tools, bigger context -> single agent
- Genuinely independent parallel subtasks or hard permission splits -> multi-agent
- Check the fixed-pipeline option FIRST -- it's the one everyone skips

<!-- speaker note: notes/02 section 7 has the full flowchart. This is the slide people should photograph. -->

---

## Exit check

- Run code/topology_simulator.py -- compare cost/latency/success across all 5 topologies
- Run code/handoff_information_loss.py -- explain why the bug is structural, not a prompt fix
- Apply the decision framework to a real task you're considering building
- State, from memory, when multi-agent is worth its cost and when it isn't
- Next: Module 08 -- Retrieval-Augmented Generation

---

## Now go build

`code/` run it · `lab/EXERCISES.md` break it · `papers/` go deeper
