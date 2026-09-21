---
marp: true
theme: default
paginate: true
style: |
  section h1 { color: #8B5CF6; }
  section { font-size: 24px; }
---

# AI Evaluation

### Knowing whether it actually works, and keeping knowing that

**Module 15** · AI End-to-End Learning Track

---

## LLM eval inherits Module 01, then breaks it

- Classical eval: fixed label set, check equality, done
- LLM output is open-ended text -- equality checks stop working fast
- The grader is often itself a model, with its own failure modes
- Benchmarks decay: fame leaks them into the next model's training data
- Same discipline (Module 01), three new structural problems

<!-- speaker note: Set up the whole module in one slide: this is Module 01's evaluation chapter, plus three genuinely new problems. -->

---

## Problem 1: the output space is unbounded

- A classifier emits one of k labels. exact_match works
- An LLM emits any token sequence -- many are correct, differently phrased
- So you reach for a GRADER: text mapped to a score
- The grader's reliability becomes half of your evaluation problem
- This is why 'LLM-as-judge' exists, and why it needs its own rigor

<!-- speaker note: Motivate graders as a necessity, not a shortcut. -->

---

## Problem 2: the eval is itself a model

- Judge an LLM with an LLM: you import its failure modes into your ruler
- Position bias, verbosity bias, leniency drift, self-preference
- A biased ruler biased in the SAME direction as the system is worst-case
- It doesn't look like noise. It looks like false confidence
- Treat judge reliability as an engineering problem, not a footnote

<!-- speaker note: This is the core thesis of the judge_bias_and_calibration.py script coming up. -->

---

## Problem 3: benchmarks have an expiration date

- A benchmark is only informative if the model hasn't seen the answers
- Popular benchmarks leak into pretraining data via blogs, mirrors, aggregators
- Contamination: score stops measuring capability, starts measuring memorization
- You can't control this by controlling your pipeline -- it's the vendor's data
- Response: build your OWN eval set from your OWN production failures

<!-- speaker note: Contamination is the LLM-era analogue of leakage, but you don't own the pipeline this time. -->

---

## Benchmark literacy: know the fine print

| Benchmark | Measures | Known weakness |
|---|---|---|
| MMLU | 57-subject multiple choice | Answer-shortcut exploits, label errors, saturated |
| HumanEval | 164 Python functions | Small enough to memorize; toy-function synthesis only |
| SWE-bench | Real GitHub issues, real repos | Narrow to ~12 popular Python repos |
| GPQA | PhD-level science Q&A | Only ~450 questions; a few items move the score a lot |
| Chatbot Arena | Crowd pairwise preference | Preference is not correctness; voter population skew |


<!-- speaker note: Every benchmark is a proxy. Every proxy gets gamed once it becomes a target. Read the limitations section before quoting the number. -->

---

## Start from real failures, not a conference room

- Most common mistake: design the suite before you have any users
- That suite tests what the team IMAGINES goes wrong -- almost never what does
- Correct order: ship rough -> harvest real failures -> build the taxonomy
- Turn each distinct FAILURE CAUSE into a rule or rubric criterion
- Synthetic/adversarial cases supplement coverage; they don't replace this

<!-- speaker note: Same habit as Module 01's 'read your worst 100 predictions', renamed 'failure taxonomy'. -->

---

## The eval pyramid

- Deterministic: exact match, schema valid, code executes and passes tests -- nearly free
- LLM-as-judge: subjective quality, no fixed reference -- expensive, needs calibration
- Human: ground truth, calibration, high-stakes calls -- very expensive
- Climb the pyramid only when the layer below can't answer the question
- Routing 'is this valid JSON' through a judge wastes a month debugging it

<!-- speaker note: Draw it as a literal pyramid. Reach for the cheapest layer that actually answers the question. -->

---

## Golden dataset sizing is a power question, not a vibe

| Size | Good for | Can't do |
|---|---|---|
| 10-20 | Smoke test | Detect anything short of catastrophic regression |
| 50-100 | Directional signal, judge calibration | Distinguish a 2-point delta from noise |
| 200-500 | Reliable 5+ point regression detection | Resolve 1-2 point deltas confidently |
| 1000-2000+ | Resolve small deltas, support slicing | --  |


<!-- speaker note: Compute it, don't guess it -- exactly what the stats script demonstrates next. -->

---

## An eval score is a sample statistic, not a fact

- 50 examples at 72% is a POINT ESTIMATE with real sampling noise
- Wilson score interval beats the naive Wald interval at small n and extreme p_hat
- McNemar's test: the correct PAIRED test for two prompts, one eval set
- Paired bootstrap: same idea for continuous rubric/judge scores
- All four formulas checked against hand-solved reference values in code

<!-- speaker note: Run the script live here if possible. Point at the self-check asserts as proof of correctness. -->

---

## 72% vs 74%: same true gap, opposite verdict

| n | Verdict at alpha=0.05 |
|---|---|
| 50 | NOT statistically distinguishable |
| 2000 | Statistically SIGNIFICANT difference |


<!-- speaker note: Identical underlying accuracies both rows. The only thing that changed is n. This is the numerically undeniable point of the whole section. -->

---

## p-hacking your own eval set

> **Re-run 40 IDENTICAL-quality prompt variants against one fixed 50-example set and some will look like wins purely from noise.**

- Same overfitting pathology as tuning against a small validation set (Module 01)
- Fix: a locked test slice touched rarely, a wider eval set, correction for multiple comparisons
- Distrust any p-value that came from a search over many candidates

<!-- speaker note: This is exactly what iterating a prompt against one fixed small eval set until the number goes up amounts to. -->

---

## The rubric is the product

- BAD: 'Rate helpfulness 1 to 10' -- a number with no construct validity
- GOOD: named, checkable, BINARY criteria (grounded / complete / concise / safe)
- Neither models nor humans reliably distinguish a 6 from a 7
- Ask for reasoning BEFORE the score -- improves judgments, gives you something to read
- A rubric change is a prompt change: version it, review it, re-calibrate after it

<!-- speaker note: This is the single highest-leverage design decision in the whole judge-building process. -->

---

## The bias catalog

| Bias | Looks like | Mitigation |
|---|---|---|
| Position | Prefers whichever answer shown first | Randomize order, average both |
| Verbosity | Longer scores higher, same content | Explicit concise criterion |
| Leniency drift | Scores cluster at 0.8+, no resolution | Track pass-rate on known negatives |
| Self-preference | Judge rates its own model family higher | Judge with a different family |


<!-- speaker note: Every one of these shows up in the first real calibration run most teams do. Budget time for it. -->

---

## The headline result: binary rubric beats 1-10 Likert

- Same simulated answers, same judge biases, scored two ways
- Binary rubric (AND of 4 criteria): Cohen's kappa ~0.5 -- MODERATE agreement
- Holistic 1-10 score, exact-match kappa ~0.08-0.09 -- SLIGHT agreement
- Quadratic-weighted kappa flatters Likert (~0.7) but answers a different question
- CI gates should use the unweighted, decision-relevant number

<!-- speaker note: State the actual kappa numbers from the script output. This is the quantitative core of the module. -->

---

## Calibrating a judge against humans

- 1. Score 50-100 real examples with a human, using YOUR exact rubric
- 2. Run the judge on the same examples at temperature 0
- 3. Compute Cohen's kappa (self-checked formula, not a library black box)
- 4. Below ~0.6-0.7: fix the RUBRIC PROMPT first, not the model
- 5. Re-check quarterly and after every judge-model upgrade

<!-- speaker note: An uncalibrated judge is a random number generator with good manners. Write the kappa number down somewhere permanent. -->

---

## Online evaluation: the production half

- Offline needs references. Production has none -- reference-free judges on live traffic
- Filter: which runs get judged. Sample: what fraction. Cap: an actual weekly spend limit
- Guardrail metrics (PII, policy) alert immediately; quality metrics are a trend, not a pager
- A/B testing an LLM change is still A/B testing -- same paired-comparison discipline applies

<!-- speaker note: Cross-reference the LangSmith track for the concrete tool-level implementation of this. -->

---

## Human evaluation, spent deliberately

- Structured rubric beats freeform 'any thoughts?' -- freeform doesn't aggregate
- Measure INTER-ANNOTATOR agreement, not just the average score
- Two humans disagreeing as much as the judge means the rubric is ambiguous
- Spend scarce human attention on disagreement and uncertainty, not on re-checking easy wins

<!-- speaker note: Human eval is the most expensive tier and the one everything else calibrates against. -->

---

## Eval-driven development: the capstone workflow

- Production failure -> add to golden dataset, tagged by failure taxonomy
- Fix -> re-run full pyramid -> paired test against a PINNED baseline
- CI gate: absolute floor AND regression delta, both required
- The dataset only grows and is versioned -- a ratchet, not a report
- Evals are a living asset with a named owner, or they decay too

<!-- speaker note: This is the diagram to leave on screen. Everything in this module is a part; this is the assembly. -->

---

## Where this module hands off

| Topic | Owned by |
|---|---|
| RAG-specific metrics (RAGAS) | ../08-rag/ |
| Agent trajectory evaluation | ../06-ai-agents/ |
| Red-team / adversarial suites | ../13-ai-security/ |
| Audit trails for eval results | ../12-ai-governance/ |
| The tooling implementation | ../16-ai-tech-stack/tracks/langsmith/ |


<!-- speaker note: This module is the theory. Reference these modules instead of re-deriving them; the LangSmith track is the tooling that implements everything just covered. -->

---

## Now go build

`code/` run it · `lab/EXERCISES.md` break it · `papers/` go deeper
