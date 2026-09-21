---
marp: true
theme: default
paginate: true
style: |
  section h1 { color: #0F766E; }
  section { font-size: 24px; }
---

# LangSmith

### Tracing, evals and observability for LLM apps

**Module 16.5** · AI End-to-End Learning Track

---

## LLM apps break differently

- No stack trace for 'the answer got worse'
- Nondeterminism means the same input can pass today, fail tomorrow
- Cost and quality drift silently -- nothing crashes, it just gets worse
- Traces are the primary debugging artifact -- there is no other kind

<!-- speaker note: Your existing APM tools cannot see any of this. That gap is the whole reason this tooling category exists. -->

---

## The data model: six nouns

- RUN -- one unit of work: an LLM call, a retrieval, a tool, a parse
- TRACE -- the tree of runs for one top-level operation, one trace_id
- run_type -- llm / chain / tool / retriever / prompt: NOT cosmetic, drives the UI
- PROJECT -- one container per app per environment, not per team
- THREAD -- groups sibling traces into one conversation (the most-skipped field)

<!-- speaker note: code/minimal_tracer.py reimplements all six offline, in ~150 lines. Read it before touching a real account. -->

---

## The field everyone regrets skipping

> **Multi-turn bugs ('it forgot the order number from turn 2') are invisible one trace at a time.**

- thread_id in metadata groups sibling traces into a session
- Also put your git SHA / release version in metadata on day one
- Without it, 'when did this start' is unanswerable -- and it's always the first question

---

## Instrumenting code, in order of effort

| Mechanism | Effort |
|---|---|
| Wrap the provider client | 5 seconds, highest value |
| @traceable on your functions | one decorator per function |
| Automatic via LangChain/LangGraph | already wired if you use them |
| Manual run trees | for the awkward cases only |


<!-- speaker note: Decide sampling and PII redaction BEFORE production, not after the first incident. -->

---

## PII: redact at the boundary or not at all

- Redaction at the SDK boundary is the only kind that counts
- Scrubbing server-side means the PII already left your systems
- code/minimal_tracer.py shows this: process_inputs runs BEFORE anything is recorded
- Decide sampling rate and redaction rules before your first production trace

<!-- speaker note: Cross-link ../../../13-ai-security/ and ../../../12-ai-governance/ here. -->

---

## The operating loop

*Everything else is an implementation detail of this diagram*


---

## Trace to ship: the loop

- PRODUCTION (traced) -> filter by thumbs-down/errors/low judge score
- -> FIND THE FAILURE, read the run tree, name the cause
- -> ANNOTATION QUEUE (human labels it) -> ADD TO DATASET
- -> FIX -> EVALUATE against baseline -> gate: pass? -> SHIP -> keep tracing
- Your eval set is a museum of your outages, not a document written in a meeting

<!-- speaker note: Three mistakes: starting at 'evaluate' before you have traces, stopping at 'ship', and skipping the human calibration step. -->

---

## The mistake everyone makes first

> **They write an eval set in a meeting, before they have a single trace.**

- That set reflects what the team imagined users would ask
- It is never what users actually ask
- Start at production (or your own dogfooding) and harvest from there

---

## evaluate(): the API

- Dataset of examples + a function under test + one or more evaluators
- Evaluator taxonomy: deterministic (exact match, schema, regex) first
- Then rubric-based LLM-as-judge for the subjective remainder
- Run it in CI on every prompt or model change -- a prompt is code

---

## LLM-as-judge: the rubric IS the product

> **'Rate this 1-10' produces a number with no construct validity.**

- Binary criteria beat 1-10 scales -- models can't reliably tell a 6 from a 7
- Ask for reasoning BEFORE the score -- improves judgments, lets you read why
- grounded / complete / concise / safe -- named, checkable, each 0 or 1

---

## Three biases that will burn you

| Bias | Looks like | Mitigation |
|---|---|---|
| Position bias | prefers A over B by ORDER alone | randomize_order, score both ways |
| Verbosity bias | longer reads as more helpful | explicit concision criterion |
| Self-preference | a model rates its own family higher | judge with a DIFFERENT family |


<!-- speaker note: eval_harness.py reproduces verbosity bias deterministically: a naive judge scores a padded answer +0.61 when the real effect is +0.11 coverage and -0.41 concision. Run it live. -->

---

## Calibrate the judge, or it is measuring nothing

- Score the same 20 examples with a human AND the judge
- Compute agreement -- if it's low, fix the rubric before trusting a single score
- Leniency drift: judges cluster at the top of any scale, destroying resolution
- Pairwise comparison beats absolute scoring when scores are all clustered high

---

## Human feedback: the ground truth

- Thumbs up/down plumbing feeds annotation queues
- Annotation queues turn raw traces into labeled, rubric-scored examples
- Every automated judge in the world is calibrated against human labels
- ...or it is calibrated against nothing

---

## Alternatives -- choose X when

| Tool | Choose it when |
|---|---|
| LangSmith | one tool for the whole loop, you are shipping not evaluating vendors |
| Langfuse | self-hosting is a hard requirement, or the seat bill is the blocker |
| Arize Phoenix | OTel-first, or doing embedding/drift analysis |
| Braintrust | evals are the main event, CI-gated release workflow |
| OTel + GenAI conventions | you already run serious observability, refuse a 2nd vendor |


<!-- speaker note: Defensible default: instrument with OTel semantics, ship to LangSmith or Langfuse. You get the product now and an exit later. -->

---

## The honest baseline

> **For one non-agentic LLM call, plain logging is fine.**

- The moment you have a chain, a tool, or a retriever -- three spans and a loop --
- the tree view pays for itself in one debugging session
- That is the threshold. Not team size, not company size

---

## Exit check

- Instrument a function with @traceable and read the resulting run tree
- Write a rubric-based judge and demonstrate verbosity bias on it
- Build a dataset from simulated 'production failures' and gate on it in CI
- State the operating loop from memory: trace -> find -> annotate -> fix -> eval -> ship
- Next: ../aws-bedrock/ -- running these systems on managed infrastructure

---

## Now go build

`code/` run it · `lab/EXERCISES.md` break it · `papers/` go deeper
