---
marp: true
theme: default
paginate: true
style: |
  section h1 { color: #1C3C3C; }
  section { font-size: 24px; }
---

# LangChain

### What it actually gives you, and when to skip it

**Module 16.3** · AI End-to-End Learning Track

---

## What LangChain is for

- A common interface (Runnable) over chat models, retrievers and tools
- LCEL: compose those interfaces with | instead of hand-wiring calls
- The value is the INTERFACE, not the chains -- that is why langchain-core is stable
- It rewrote itself twice while people were forming opinions about it
- This track teaches the current 1.x package layout

<!-- speaker note: Set the tone: opinionated and current, not a fan page. -->

---

## When NOT to use it -- read this twice

> **If your app is one prompt, one model, parse the answer: the provider SDK does it in ~10 lines with no release notes.**

- A framework around one API call buys a pip tree and an upgrade obligation
- Failing chains produce a traceback through 4 layers before your bug
- Opaque BY DEFAULT -- turning on a tracer is your job, not optional
- Worst outcome: a 5-layer RunnableSequence wrapping one messages.create()

<!-- speaker note: This is the single most important slide in the deck. Say it before anything else lands. -->

---

## The package split, and why it happened

- langchain-core: interfaces, Runnable, LCEL, messages -- ZERO heavy deps
- langchain: create_agent, middleware, init_chat_model (built on langgraph)
- langgraph: the runtime -- graphs, state, checkpointers, durable execution
- langchain-community: the long tail, community-maintained, uneven quality
- langchain-classic: v0 chains and retrievers -- frozen, a migration you owe yourself

<!-- speaker note: By mid-2024 the monolith had 700+ integrations; one broken dep bumped the whole ecosystem. The split gave langchain-core a real stability promise. -->

---

## The stability story, honestly stated

| Package | Stability | What it means for you |
|---|---|---|
| langchain-core | strong, major-version only | depend on it freely |
| langchain | strong since 1.0 | pin a major, read changelogs |
| provider packages | follows the provider | pin a minor if you care |
| langchain-community | weakest | read the source before shipping |
| langchain-classic | frozen-ish | a migration, not a home |


<!-- speaker note: v1 reduced langchain's namespace to agents/messages/tools/chat_models/embeddings. Verify with pkgutil.iter_modules yourself. -->

---

## Runnable: the one interface

- invoke / batch / stream / ainvoke / abatch / astream -- one contract
- Implement a BaseChatModel subclass and ALL of these work for free
- with_retry(), with_fallbacks(), configurable_fields() -- also free
- This is the actual value of the framework: write once, get 6 execution modes

<!-- speaker note: code/fakes.py implements this from scratch -- read it before the demos so the free behaviour isn't magic. -->

---

## LCEL: composition, not a DSL

- prompt | model | parser -- the pipe composes Runnables
- RunnableParallel -- fan out to several branches, merge the dict
- RunnablePassthrough.assign -- carry the original input alongside a derived field
- with_retry / with_fallbacks -- resilience as composition, not boilerplate
- Be precise: LCEL composes STEPS; it is not how you build agent CONTROL FLOW

<!-- speaker note: That last bullet is the boundary that sends people to LangGraph. Flag it early. -->

---

## Messages, prompts, parsers

- Messages: System / Human / AI / Tool -- one typed vocabulary across providers
- Prompt templates: parameterised, composable, testable in isolation
- Output parsers exist, but prefer with_structured_output() when you can
- Structured output uses the provider's native tool-calling under the hood
- A parser is a regression waiting to happen; a schema is a contract

---

## Tools: bind, call, handle failure

- bind_tools() attaches schemas; the model decides whether to call one
- Handle a HALLUCINATED tool name -- the model can invent one that doesn't exist
- Handle schema-invalid arguments -- validate before you execute
- Raise ToolException deliberately so the loop can recover, not crash
- code/tools_and_structured_output.py implements this loop by hand

<!-- speaker note: This is where 'the agent is unreliable' complaints actually originate -- in unhandled tool-call edge cases, not the model. -->

---

## Retrieval, assembled

- loader -> splitter -> embeddings -> vector store -> retriever -> prompt -> model
- Every stage is a Runnable; the whole chain composes with the same pipe operator
- code/mini_rag_chain.py builds this fully offline with a hash-based embedding
- It also demonstrates a GROUNDED-LOOKING hallucination on an out-of-corpus question
- Retrieval quality itself -- chunking, hybrid search, reranking -- is Module 08

<!-- speaker note: The demo hallucination is deliberate: confident wrong answers are the default failure mode of naive RAG, not an edge case. -->

---

## Running it in production

*Memory, streaming, cost, debugging*


---

## Memory: the part that aged worst

- Old ConversationBufferMemory-style classes are legacy -- state lives in your app now
- Four pitfalls: unbounded history, silent truncation, no summarisation strategy,
-   - confusing 'memory' (recall) with 'context' (what's in the prompt right now)
- Plan message-history storage and trimming yourself; do not expect a class to do it

---

## Streaming and cost accounting

- Measure time-to-first-token -- or don't bother measuring streaming at all
- Callbacks are how you get token counts and cost attribution mid-chain
- Caching means two different things: prompt/response cache vs. provider prompt caching
- Confusing the two produces a 'caching is on' bug report that caching cannot fix

---

## Failure modes and what they actually mean

| Symptom | Likely cause |
|---|---|
| Silent wrong answers | no tracer attached -- turn on set_debug or LangSmith |
| Cost 38x higher than expected | a model swap bundled with an unrelated prompt change |
| Works once, fails in a loop | unbounded history growing the prompt every turn |
| JSON parse errors intermittently | using a text parser instead of with_structured_output |
| Retries hang | with_retry without a fallback or a timeout |


<!-- speaker note: The debugging playbook in notes/02 walks each of these with the actual trace to look for. -->

---

## Security notes specific to this framework

- community loaders and tools run arbitrary code paths you did not write
- Read the source of any langchain-community integration before enabling it
- Untrusted retrieved text still shares a channel with your instructions
- Prompt injection risk is not solved by the framework -- see Module 13

<!-- speaker note: Cross-reference ../../../13-ai-security/ explicitly here. -->

---

## When to graduate to LangGraph

- You need a LOOP: retry, re-plan, or call an agent more than once per turn
- You need branching control flow the pipe operator cannot express
- You need persistence: pause, resume, human approval, time travel
- You are hand-rolling a while-loop around an LLM call -- that loop IS a graph
- LCEL for pipelines. LangGraph for anything with a cycle or a checkpoint

<!-- speaker note: This is the natural bridge to ../langgraph/. Say the decision rule out loud. -->

---

## A pre-ship checklist

- A tracer is attached in every environment, not just locally
- Every tool call handles a hallucinated name and invalid arguments
- Structured output uses with_structured_output, not a hand-rolled parser
- Message history has an explicit trimming/summarisation strategy
- You can answer: 'why LangChain and not the raw SDK?' for THIS feature

---

## Exit check

- Draw the package graph and say what you would pin, and to what
- Implement a BaseChatModel subclass; explain why .batch() works for free
- Diagnose a broken chain from a trace using the six failure modes
- Decide: LCEL, create_agent, or hand-written LangGraph -- with stated criteria
- Next: ../langgraph/ -- stateful, controllable agent orchestration

---

## Now go build

`code/` run it · `lab/EXERCISES.md` break it · `papers/` go deeper
