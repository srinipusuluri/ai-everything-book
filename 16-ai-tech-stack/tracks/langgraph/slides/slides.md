---
marp: true
theme: default
paginate: true
style: |
  section h1 { color: #2F6F4E; }
  section { font-size: 24px; }
---

# LangGraph

### Agents are graphs with state, not chains

**Module 16.4** · AI End-to-End Learning Track

---

## The thesis

- A chain is a DAG of prompts: fixed at authoring time, no going back
- Five things a DAG cannot express: loops, runtime branching, informed retries,
-   pausing for approval, resuming after a crash
- Everyone discovers this the same way: chain -> while loop -> step counter ->
-   try/except -> a dict of 'stuff so far' -> a bad workflow engine, homemade

<!-- speaker note: This progression is universal. Ask the room if anyone has written that homemade workflow engine -- most hands go up. -->

---

## The bet

> **Model your agent as a state machine whose transitions are explicit and whose state is persisted after every step.**

- Underneath: Pregel -- bulk-synchronous parallel graph execution
- Execution proceeds in SUPERSTEPS: all scheduled nodes run, writes merge, repeat
- That is why parallel branches join automatically
- And why recursion_limit counts supersteps, not node calls

<!-- speaker note: Pregel is Google's graph model. Knowing this explains three otherwise-mysterious LangGraph behaviors at once. -->

---

## State: the part that is actually hard

- Nodes are the easy part -- (state) -> dict. That's it
- Reducers decide how a node's write MERGES into existing state
- add_messages is the canonical reducer: appends instead of overwriting
- State should hold a plan, a budget, a scratchpad, a cursor -- not just messages
- If your graph misbehaves, the bug is in your reducers, not your nodes

<!-- speaker note: code/graph_basics.py demonstrates a custom reducer and a max-iteration guard together. -->

---

## Topology: the four ways to route

| Mechanism | Use it when |
|---|---|
| add_edge(a, b) | control flow is fixed; two edges out = parallel |
| add_conditional_edges | the routing decision is data |
| Command(update=, goto=) | the node itself knows where to go next |
| Send('worker', payload) | fan-out width is only known at runtime |


<!-- speaker note: Always pass the path_map to add_conditional_edges -- without it Studio cannot draw your cycle. -->

---

## Cycles: three ways they end, want the first two

- 1. A semantic exit -- no tool calls returned, or judge score >= threshold
- 2. A budget in state -- if attempts >= MAX: return END. Inspectable, explainable
- 3. recursion_limit (default 25 supersteps) raises GraphRecursionError
- That third one is a CIRCUIT BREAKER, not a design
- If it fires in production you already paid for 25 model calls

---

## The comparison you actually need

| Option | Choose it when |
|---|---|
| Plain while loop | single-turn tools, <5 steps, no approval needed |
| create_agent (prebuilt) | the ReAct tool-calling loop IS the product |
| LangGraph StateGraph | loops + approval + resume + multi-step state |
| Temporal / Airflow | the LLM is one step in a long business workflow |
| CrewAI / AutoGen | prototypes where the built-in pattern fits exactly |


<!-- speaker note: Default path: start with a plain loop. Move to StateGraph the first time someone asks 'can a human check this first' or 'what happened on run 4471'. -->

---

## When NOT to use LangGraph

> **If your state schema is {input: str, output: str}, you have written a function with extra steps.**

- A one-shot classification does not need a graph
- A genuinely linear RAG pipeline does not need a graph
- Use it when you can actually name what is in the state

---

## Persistence, approval, durability

*The four things that decide whether anyone lets you run this*


---

## Persistence: one argument, a different system

- compile(checkpointer=saver); invoke(..., thread_id='ticket-4471')
- Memory between turns -- the second invoke resumes from stored state
- Resume after a crash or deploy -- the thread lives in Postgres, not a process
- Interrupts need this -- no checkpointer means nowhere to pause TO
- Time travel: get_state_history() replays every superstep

<!-- speaker note: A thread is a lineage; a checkpoint is one immutable snapshot inside it. -->

---

## Human-in-the-loop: what makes agents deployable

- interrupt() stops the graph; invoke() RETURNS -- no blocked worker, no held socket
- Resume days later from a different process for zero ongoing cost
- Four patterns: approve/reject, edit the action, review a tool call, ask a question
- All four are the same primitive: interrupt() plus Command(resume=...)

<!-- speaker note: This is the single feature that turns a demo into something a regulated business can ship. -->

---

## The re-execution trap

> **Resuming re-runs the node from the top. LangGraph does not freeze a stack frame.**

- send_email() before interrupt() fires AGAIN on every resume
- Fix: put the side effect in its own node, or make it idempotent
- The same rule governs crash recovery -- a node that died is re-run WHOLE
- Design every node so running it twice is boring. The most important line here

<!-- speaker note: code/checkpoint_and_interrupt.py section 4 makes the notification fire twice on purpose -- watch it happen. -->

---

## Why governance cares

- An approval gate turns 'the model did something' into
-   'a named person authorised this at 14:32, and here is the exact state they saw'
- That is the difference between a demo and a regulated production system
- It is also a defence against prompt-injected tool calls reaching a side effect

<!-- speaker note: Cross-link ../../../12-ai-governance/ and ../../../13-ai-security/ explicitly. -->

---

## Multi-agent patterns

| Pattern | Good at | Fails at |
|---|---|---|
| Supervisor | traceability, per-worker limits | supervisor context bloat, +2 calls/hop |
| Hand-off / swarm | fewer hops, natural escalation | emergent control flow, real loops |
| Hierarchical teams | genuinely large task trees | latency and cost multiply |
| Router | cheap, predictable | no recovery from misclassification |


<!-- speaker note: The primitives are unremarkable on purpose: subgraphs plus Command(goto=, graph=PARENT). -->

---

## The honest advice

> **Most multi-agent systems should be one agent with better tools.**

- Each extra agent costs a round trip, a serialization boundary, a lossy hand-off
- Anthropic's own research system spent ~15x the tokens of a single chat
- Worth it there. Absurd for a support bot
- Do not split because the org chart has three teams

<!-- speaker note: Use multiple agents only when context genuinely does not fit, subtasks are independent and parallel, or you need per-role permissions/approval. -->

---

## Durable execution and streaming

- Retries at the node level need idempotency keys -- see the re-execution trap
- Streaming modes: values, updates, messages, custom -- pick what the UI needs
- Stream token-by-token for chat; stream 'updates' for a progress indicator
- Observability: LangSmith traces every node, every superstep -- see ../langsmith/

---

## Exit check

- Build a StateGraph with a typed reducer and a max-iteration guard
- Implement a ReAct agent as an explicit graph with tool-error handling
- Add a checkpointer, an interrupt/approval gate, and resume from it
- State, out loud, why most multi-agent systems should be one agent
- Next: ../langsmith/ -- see what the graph actually did

---

## Now go build

`code/` run it · `lab/EXERCISES.md` break it · `papers/` go deeper
