# 📚 Module 04 — Large Language Models

> **Where you are:** Stop 4 of 16. **Time:** ~25 hours · **Prereq:** [Module 03](../03-nlp/) — non-negotiable.

A large language model is the Module 03 transformer, scaled, trained on most of the public internet, and
then bent into a helpful assistant by post-training. This module covers the three phases of that pipeline
(pretraining → alignment → inference), the decoding knobs you actually control, and the failure modes you
will spend your career designing around.

---

## Learning objectives

1. Describe the full lifecycle: pretraining → SFT → preference optimisation (RLHF/DPO) → deployment.
2. Use **scaling laws** to reason about compute, data and parameter trade-offs — and explain what Chinchilla changed.
3. Control generation deliberately: temperature, top-k, top-p, min-p, repetition penalty, and structured decoding.
4. Choose correctly between **prompting → RAG → fine-tuning → continued pretraining**, and defend the choice on cost.
5. Explain quantization, LoRA/QLoRA, distillation, and speculative decoding well enough to size a deployment.
6. Name the real failure modes — hallucination, sycophancy, context rot, prompt sensitivity — and mitigate each.

## Suggested path

| # | Do this | File | Time |
|---|---|---|---|
| 1 | How an LLM is built | [notes/01-how-llms-are-built.md](notes/01-how-llms-are-built.md) | 5h |
| 2 | Using them well | [notes/02-inference-and-adaptation.md](notes/02-inference-and-adaptation.md) | 5h |
| 3 | Sampling, felt not read | [code/sampling_strategies.py](code/sampling_strategies.py) | 2h |
| 4 | Cost & capacity model | [code/llm_cost_calculator.py](code/llm_cost_calculator.py) | 2h |
| 5 | Prompt patterns that work | [code/prompt_patterns.md](code/prompt_patterns.md) | 2h |
| 6 | Slides | [slides/](slides/) | 1h |
| 7 | Lab | [lab/EXERCISES.md](lab/EXERCISES.md) | 6h |
| 8 | Papers | [papers/PAPERS.md](papers/PAPERS.md) | 5h |

## The 16 terms you must own

`pretraining` · `SFT` · `RLHF` · `DPO` · `scaling law` · `context window` · `temperature` · `top-p` ·
`logits` · `perplexity` · `in-context learning` · `chain-of-thought` · `LoRA` · `quantization` ·
`speculative decoding` · `hallucination`

## Exit check ✅

Given a use case, you can produce a defensible one-page recommendation: which model, prompted or fine-tuned,
at what context length, what it will cost per 1,000 requests, what its top-3 failure modes are, and how
you'd measure them.
