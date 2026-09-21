# 📄 Papers & Primary Sources — Large Language Models

arXiv links are canonical and stable. Read the three starred papers in order before anything else; the rest
are reference reading organised by the phase of the pipeline they cover.

## The canon (read in this order)

| # | Paper | Year | Why it matters | Link |
|---|-------|------|----------------|------|
| 1 | **Attention Is All You Need** — Vaswani et al. | 2017 | The transformer. You studied it in [Module 03](../../03-nlp/); reread it knowing what it becomes. | [arXiv:1706.03762](https://arxiv.org/abs/1706.03762) |
| 2 | ★ **Language Models are Few-Shot Learners** (GPT-3) — Brown et al. | 2020 | Scale turns next-token prediction into in-context learning. The paper that made this module necessary. | [arXiv:2005.14165](https://arxiv.org/abs/2005.14165) |
| 3 | ★ **Training Compute-Optimal LLMs** (Chinchilla) — Hoffmann et al. | 2022 | The 20-tokens-per-parameter rule, and the correction that reshaped every subsequent training run. | [arXiv:2203.15556](https://arxiv.org/abs/2203.15556) |
| 4 | ★ **Scaling Laws for Neural Language Models** — Kaplan et al. | 2020 | Loss as a power law in N, D, C. The reason labs bet $100M before a run starts. | [arXiv:2001.08361](https://arxiv.org/abs/2001.08361) |

## Post-training & alignment

| Paper | Year | One-line takeaway | Link |
|---|---|---|---|
| **Training language models to follow instructions** (InstructGPT) | 2022 | SFT + RLHF; the template every chat model still follows | [arXiv:2203.02155](https://arxiv.org/abs/2203.02155) |
| **Direct Preference Optimization** (DPO) | 2023 | Skip the reward model; a classification loss on preference pairs | [arXiv:2305.18290](https://arxiv.org/abs/2305.18290) |
| **Constitutional AI** — Bai et al. | 2022 | RLAIF: the model critiques itself against written principles | [arXiv:2212.08073](https://arxiv.org/abs/2212.08073) |
| **LIMA: Less Is More for Alignment** | 2023 | 1,000 curated examples beat 50k noisy ones; quality over quantity in SFT | [arXiv:2305.11206](https://arxiv.org/abs/2305.11206) |
| **Training a Helpful and Harmless Assistant with RLHF** — Anthropic | 2022 | The practical RLHF write-up: data collection, reward modelling, KL details | [arXiv:2204.05862](https://arxiv.org/abs/2204.05862) |

## Efficient inference & adaptation

| Paper | Year | One-line takeaway | Link |
|---|---|---|---|
| **LoRA: Low-Rank Adaptation** — Hu et al. | 2021 | Freeze W, learn dW = BA; the default fine-tuning method | [arXiv:2106.09685](https://arxiv.org/abs/2106.09685) |
| **QLoRA** — Dettmers et al. | 2023 | 4-bit base + LoRA: fine-tune 70B on one GPU | [arXiv:2305.14314](https://arxiv.org/abs/2305.14314) |
| **Fast Inference from Transformers via Speculative Decoding** — Leviathan et al. | 2022 | Draft-and-verify: 2-3x decode speedup with an unchanged output distribution | [arXiv:2211.17192](https://arxiv.org/abs/2211.17192) |
| **FlashAttention** — Dao et al. | 2022 | Exact attention, IO-aware tiling; made long context affordable | [arXiv:2205.14135](https://arxiv.org/abs/2205.14135) |
| **GQA: Grouped-Query Attention** — Ainslie et al. | 2023 | Shrink the KV cache 4-8x with negligible quality loss | [arXiv:2305.13245](https://arxiv.org/abs/2305.13245) |
| **Efficient Memory Management for LLM Serving with PagedAttention** (vLLM) | 2023 | KV cache as virtual memory; the throughput unlock in modern serving | [arXiv:2309.06180](https://arxiv.org/abs/2309.06180) |

## Failure modes & evaluation-adjacent

| Paper | Year | One-line takeaway | Link |
|---|---|---|---|
| **Lost in the Middle** — Liu et al. | 2023 | Long-context retrieval accuracy dips in the middle; position your evidence deliberately | [arXiv:2307.03172](https://arxiv.org/abs/2307.03172) |
| **The False Promise of Imitating Proprietary LLMs** — Gudibande et al. | 2023 | Why distilling from a chat model's outputs does not recover its capability | [arXiv:2305.15717](https://arxiv.org/abs/2305.15717) |
| **Holistic Evaluation of Language Models** (HELM) | 2022 | Multi-metric evaluation; the honest answer to "how good is this model" | [arXiv:2211.09110](https://arxiv.org/abs/2211.09110) |

## How to read an LLM paper (30 minutes, 3 passes)

1. **Pass 1 (5 min):** abstract, Figure 1/Table 1, conclusion. What's the claim, and at what scale?
2. **Pass 2 (15 min):** experimental setup, ablations, baseline fairness. Was the comparison compute-matched?
3. **Pass 3 (10 min):** limitations and what would break at a different scale. LLM results are notoriously
   scale-fragile in both directions.

Keep a one-paragraph note per paper. Prices, leaderboards and SOTA claims expire; mechanisms don't.
