---
marp: true
theme: default
paginate: true
style: |
  section h1 { color: #06B6D4; }
  section { font-size: 24px; }
---

# Large Language Models

### How they are built, and how to actually use them

**Module 04** · AI End-to-End Learning Track

---

## An LLM is Module 03, scaled

- A transformer, trained on 10-30 trillion tokens, then bent into an assistant
- Pretraining (months, $10M+) -> SFT (days) -> preference optimisation -> serving
- A BASE model completes text. An INSTRUCT model follows orders. Not the same thing
- Most 'why is it doing that' confusion is confusing the two

<!-- speaker note: Draw the four-box pipeline. Return to it at every stage of this deck. -->

---

## Pretraining: one objective, enormous consequences

- Objective: predict the next token. That is the entire loss function
- It is the cross-entropy from Module 01, applied at every position
- To predict well you must model syntax, facts, code, reasoning, style
- Data quality work moves benchmarks more than architecture tweaks
- FLOPs ~= 6 * N * D -- use this to sanity-check any training claim

<!-- speaker note: Dedup, quality filters, decontamination, domain mixing. Unglamorous and decisive. -->

---

## Scaling laws, and the correction to the correction

| Regime | Optimise for | Result |
|---|---|---|
| Kaplan 2020 | predictability | loss is a power law in N, D, C |
| Chinchilla 2022 | training compute | ~20 tokens per parameter |
| Production 2023+ | INFERENCE cost | overtrain small models: 100-2000 tok/param |


<!-- speaker note: Chinchilla optimises training. If you serve billions of requests, deliberately overtrain a smaller model. -->

---

## Post-training: format, then judgment

- SFT teaches FORMAT: curated (instruction, response) pairs, prompt loss masked
- Quality beats quantity -- LIMA: 1k curated beat 50k noisy
- Preference optimisation teaches JUDGMENT: which good answer is better
- RLHF: reward model + PPO + a KL penalty (without it: reward hacking)
- DPO: skip the reward model entirely. Simpler, cheaper, stabler -- now the default

<!-- speaker note: Reward hacking is Goodhart's law with a GPU budget. The KL penalty is the leash. -->

---

## Get the chat template right

- Post-training introduces special tokens for system/user/assistant turns
- Wrong template at inference = quality collapse that LOOKS like a dumb model
- Symptoms: rambling, ignoring the system prompt, never stopping
- Always use the tokenizer's apply_chat_template
- This is the single most common self-hosting bug

<!-- speaker note: Worth 30 seconds of stage time. It saves people days. -->

---

## The alignment bill

- Alignment tax: some raw capability traded for safety and format compliance
- Sycophancy: agreeing with the user scores well with human raters
- Over-refusal: the mirror failure, and it must be measured explicitly
- Constitutional AI / RLAIF: model critiques against written principles
- Those principles are an auditable document -- Module 12 cares about this

<!-- speaker note: Sycophancy is a direct consequence of optimising human approval. It is not a bug you can prompt away. -->

---

## Using them

*Decoding, adaptation, cost*


---

## Generation is a pipeline of knobs

- logits -> temperature -> penalties -> top-k / top-p / min-p -> softmax -> sample
- Temperature: T->0 greedy; T=1 native; T>1 flattened and incoherent
- top-p is ADAPTIVE: the candidate set shrinks when the model is confident
- min-p behaves better than top-p at high temperature
- Change ONE at a time. Most 'prompt regressions' are sampling regressions

<!-- speaker note: Run code/sampling_strategies.py live if you can. Seeing it beats reading it. -->

---

## Temperature by task

| Task | T |
|---|---|
| Extraction, classification, tool arguments, SQL | 0 |
| Factual Q&A, summarisation | 0 - 0.3 |
| General assistant chat | 0.5 - 0.8 |
| Brainstorming, creative writing | 0.8 - 1.2 |


<!-- speaker note: Never use a repetition penalty on code or JSON. Repeated braces and identifiers are required. -->

---

## Structured output

> **Mask the logits so only schema-valid tokens can be sampled. Malformed JSON becomes impossible, not merely unlikely.**

- Outlines, XGrammar, llama.cpp GBNF, provider JSON mode
- If you parse model output in production, use this
- Fallback: validate, then re-prompt with the validation error

---

## The adaptation decision, in cost order

| Approach | Setup | Best for | Bad for |
|---|---|---|---|
| Prompting | minutes | start here, always | strict style, private corpora |
| RAG | days | private/current knowledge, citations | teaching skills or style |
| LoRA fine-tune | days | style, format, narrow task, cost cuts | adding FACTS |
| Full fine-tune | weeks | deep domain adaptation | most teams |
| Continued pretraining | months | a new domain or language | virtually everyone |


<!-- speaker note: The rule that saves the most money: fine-tuning teaches BEHAVIOUR, retrieval supplies KNOWLEDGE. -->

---

## LoRA in one slide

- Freeze W. Learn a low-rank update dW = B A, with r much smaller than d
- Trains ~0.1-1% of parameters; merge at inference for zero added latency
- r = 8-16 for style/format; 32-64 for harder tasks; alpha ~ 2r to start
- QLoRA = LoRA on a 4-bit base -- fine-tune 70B on one GPU
- Hot-swap adapters to serve many fine-tunes from one base model

---

## Quantization

| Format | Bits | Quality loss |
|---|---|---|
| BF16 | 16 | baseline |
| FP8 / INT8 | 8 | very small |
| 4-bit (GPTQ, AWQ, NF4) | 4 | small to moderate, task-dependent |
| 2-3 bit | 2-3 | significant |


<!-- speaker note: A bigger model at 4-bit usually beats a smaller model at bf16 for the same memory. Always re-run evals after quantizing -- reasoning and code degrade first. -->

---

## The four serving numbers

- TTFT -- prefill, compute-bound, scales with prompt length
- TPOT -- decode, memory-bandwidth-bound, sequential
- Throughput -- what your cost per token depends on
- Concurrency -- capped by KV cache memory, not by weights
- Continuous batching is the single biggest real throughput win

<!-- speaker note: Speculative decoding: 2-3x faster decode with PROVABLY IDENTICAL output distribution. -->

---

## Cost facts that dominate real bills

- Output tokens cost 3-5x input tokens. 'Be concise' is a cost control
- Cached input is dramatically cheaper -- keep the prefix byte-identical
- RAG multiplies input: 20 chunks x 500 tokens = +10k tokens per request
- Agent loops resend a growing transcript: cost grows ~quadratically in turns
- Biggest lever: route the easy 80% to a small model

<!-- speaker note: Run code/llm_cost_calculator.py with their numbers. It ends architecture arguments faster than opinions do. -->

---

## Failure modes you design around

| Failure | Why | Mitigation |
|---|---|---|
| Hallucination | trained for plausible, not for knowing | RAG + citations, abstention, evals |
| Sycophancy | preference training rewards agreement | neutral framing, adversarial evals |
| Prompt sensitivity | tiny wording changes shift output | version prompts, regression-test |
| Context rot | irrelevant context degrades quality | retrieve harder, compact, shorten |
| Non-determinism | sampling + batching, even at T=0 | assert properties, never exact strings |


<!-- speaker note: Long context does NOT make RAG obsolete. Retrieval stays cheaper, fresher, more auditable. -->

---

## Exit check

- Write a one-page recommendation: which model, prompted or tuned, what context
- Include cost per 1000 requests and the top 3 failure modes
- Include how you will MEASURE those failure modes
- Run both code files; read code/prompt_patterns.md
- Next: Module 05 -- Generative AI beyond text

---

## Now go build

`code/` run it · `lab/EXERCISES.md` break it · `papers/` go deeper
