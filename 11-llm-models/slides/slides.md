---
marp: true
theme: default
paginate: true
style: |
  section h1 { color: #EF4444; }
  section { font-size: 24px; }
---

# The LLM Model Landscape

### Selecting, comparing and migrating -- not memorizing a leaderboard

**Module 11** · AI End-to-End Learning Track

---

## This module teaches a framework, not a snapshot

- The model landscape changes on a timescale of weeks
- Any specific number in this deck will be stale by the time you read it
- What survives: how to choose, how to read a benchmark, how to migrate
- One dated snapshot table IS included -- clearly labeled, verify before trusting it

<!-- speaker note: Say this out loud before anything else. It's the module's whole thesis. -->

---

## The tier structure every provider converges on

| Tier | Trade-off |
|---|---|
| Frontier/flagship | max capability, max cost, max latency |
| Mid/balanced | the workhorse for most production traffic |
| Small/fast | cheap, low-latency, high-volume or simple tasks |
| Reasoning variant | trades latency for quality on hard problems |


<!-- speaker note: Every major provider has converged on roughly this shape. Recognizing it transfers across vendors. -->

---

## Proprietary vs. open-weights: the real trade-offs

| Axis | Consideration |
|---|---|
| Data residency | self-hosting gives full control; API means trusting the provider |
| Customization depth | full fine-tuning vs. API-level adaptation only |
| Cost at scale | self-hosting break-even depends on utilization -- see Module 04's calculator |
| Support/liability | who do you call when it's wrong |
| Licensing | 'open weights' does NOT mean unrestricted use of outputs |


<!-- speaker note: The licensing nuance surprises people constantly -- a model being downloadable doesn't settle the legal question. Module 14 has the depth. -->

---

## The selection framework

> **Define your accuracy bar, latency budget, cost budget, and compliance constraints FIRST.**

- THEN evaluate candidates against YOUR eval set
- NEVER against a public leaderboard alone
- A leaderboard builds your shortlist. Your eval set makes the decision

<!-- speaker note: code/model_selection_scorer.py implements exactly this workflow -- run it live with the audience's own numbers if possible. -->

---

## Benchmark literacy: read the number, then distrust it

- MMLU has documented label errors and is approaching saturation
- SWE-bench and GPQA are the current harder differentiators -- for now
- Chatbot Arena's Elo has its own biases: style and length preference
- A single score answers neither 'is this real' nor 'is this reproducible'

---

## Two things a single benchmark number hides

- CONTAMINATION: did this exact problem leak into training data?
- code/benchmark_literacy_demo.py constructs held-out variants to expose this
- VARIANCE: is a 2-point gap a real capability difference or sampling noise?
- Check both before letting a benchmark move a real decision

<!-- speaker note: This is the Module 01 test-set-leakage lesson, replayed at the scale of an entire industry's shared benchmarks. -->

---

## Context window as a selection axis

- Advertised context and USABLE context are different numbers
- 'Lost in the middle' and context rot apply here too -- see Module 04
- Match context needs to the actual task; don't default to the biggest number
- A bigger context window is not free -- cost and latency scale with it

---

## Specialization: when smaller wins

- General-purpose frontier models are not always the right tool
- A domain-fine-tuned model (code, medical, legal) can beat a larger generalist
- Smaller + specialized often wins on cost, latency, AND accuracy for a narrow task
- Test this explicitly -- don't assume bigger is always better

---

## Multi-model strategy: don't marry one provider

- Design your app with an abstraction layer -- the gateway pattern from Module 10
- What breaks when you swap models: prompt sensitivity, tool-call format quirks,
-   different default verbosity, subtly different refusal behavior
- A migration is a project with a checklist, not a config change

---

## Versioning and deprecation: an ongoing obligation

- Providers deprecate model versions on a timeline -- this doesn't stop
- Pin versions deliberately; know what 'latest' aliases actually resolve to
- A provider updating 'latest' under you IS a silent model change
- Your eval suite (Module 15) is what catches the regression when that happens

---

## Snapshot: frontier families (dated, verify before use)

| Family | Typical strength/fit |
|---|---|
| Anthropic Claude | agentic coding, long-running tool-use, consistent tool-calling |
| OpenAI GPT | broad general-purpose, large ecosystem, frequent reasoning releases |
| Google Gemini | very large context across the whole tier line |
| Meta Llama / Mistral / DeepSeek / Qwen | open-weights: control, self-hosting, cost at scale |


<!-- speaker note: As of September 2026 -- say this explicitly every time this slide is shown. Link to official pricing pages, never quote a price as fact. -->

---

## Exit check

- Run code/model_selection_scorer.py with your own real task profile
- Run code/benchmark_literacy_demo.py and explain contamination vs. variance
- State the selection framework from memory: constraints first, leaderboard never
- Name three things that break in a naive model migration
- Next: Module 12 -- AI Governance

---

## Now go build

`code/` run it · `lab/EXERCISES.md` break it · `papers/` go deeper
