# 📄 Papers — NLP & Transformers

`bash ../_tools/fetch_papers.sh 03-nlp` downloads these into this folder.

## Read #1 twice. Then read it again in a month.

| # | Paper | Year | Why | Link |
|---|---|---|---|---|
| 1 | **Attention Is All You Need** — Vaswani et al. | 2017 | The transformer. Eight pages that redirected the field. Read alongside *The Annotated Transformer*. | [arXiv:1706.03762](https://arxiv.org/abs/1706.03762) |
| 2 | **BERT** — Devlin et al. | 2018 | Bidirectional pretraining + fine-tuning; created the "pretrain then adapt" era | [arXiv:1810.04805](https://arxiv.org/abs/1810.04805) |
| 3 | **Improving Language Understanding by Generative Pre-Training (GPT-1)** — Radford et al. | 2018 | The decoder-only bet | [PDF](https://cdn.openai.com/research-covers/language-unsupervised/language_understanding_paper.pdf) |
| 4 | **Neural Machine Translation by Jointly Learning to Align and Translate** — Bahdanau et al. | 2014 | Where attention was actually invented | [arXiv:1409.0473](https://arxiv.org/abs/1409.0473) |

## Tokenization
| Paper | Takeaway | Link |
|---|---|---|
| Neural Machine Translation of Rare Words with Subword Units (BPE) — Sennrich et al., 2015 | BPE for NLP | [arXiv:1508.07909](https://arxiv.org/abs/1508.07909) |
| SentencePiece — Kudo & Richardson, 2018 | Language-agnostic, no whitespace pre-tokenization | [arXiv:1808.06226](https://arxiv.org/abs/1808.06226) |
| Subword Regularization — Kudo, 2018 | The unigram LM tokenizer | [arXiv:1804.10959](https://arxiv.org/abs/1804.10959) |

## Architecture & efficiency
| Paper | Takeaway | Link |
|---|---|---|
| RoFormer (RoPE) — Su et al., 2021 | Rotary position embeddings; in almost every modern LLM | [arXiv:2104.09864](https://arxiv.org/abs/2104.09864) |
| Train Short, Test Long (ALiBi) — Press et al., 2021 | Length extrapolation via attention bias | [arXiv:2108.12409](https://arxiv.org/abs/2108.12409) |
| Fast Transformer Decoding: One Write-Head (MQA) — Shazeer, 2019 | The KV-cache problem, stated early | [arXiv:1911.02150](https://arxiv.org/abs/1911.02150) |
| GQA: Training Generalized Multi-Query Transformer Checkpoints — Ainslie et al., 2023 | The modern default | [arXiv:2305.13245](https://arxiv.org/abs/2305.13245) |
| FlashAttention — Dao et al., 2022 | IO-aware exact attention | [arXiv:2205.14135](https://arxiv.org/abs/2205.14135) |
| FlashAttention-2 — Dao, 2023 | Better parallelism and work partitioning | [arXiv:2307.08691](https://arxiv.org/abs/2307.08691) |
| GLU Variants Improve Transformer (SwiGLU) — Shazeer, 2020 | The modern FFN | [arXiv:2002.05202](https://arxiv.org/abs/2002.05202) |
| Root Mean Square Layer Normalization (RMSNorm) — Zhang & Sennrich, 2019 | Cheaper norm, same result | [arXiv:1910.07467](https://arxiv.org/abs/1910.07467) |
| On Layer Normalization in the Transformer Architecture — Xiong et al., 2020 | Why Pre-LN beat Post-LN | [arXiv:2002.04745](https://arxiv.org/abs/2002.04745) |
| T5: Exploring the Limits of Transfer Learning — Raffel et al., 2019 | Everything as text-to-text; a huge ablation study | [arXiv:1910.10683](https://arxiv.org/abs/1910.10683) |
| Efficient Transformers: A Survey — Tay et al., 2020 | Map of the efficiency landscape | [arXiv:2009.06732](https://arxiv.org/abs/2009.06732) |
| Mamba: Linear-Time Sequence Modeling — Gu & Dao, 2023 | The serious non-attention challenger | [arXiv:2312.00752](https://arxiv.org/abs/2312.00752) |

## Embeddings & retrieval (bridges to Module 08)
| Paper | Takeaway | Link |
|---|---|---|
| Efficient Estimation of Word Representations (word2vec) — Mikolov et al., 2013 | Meaning as geometry | [arXiv:1301.3781](https://arxiv.org/abs/1301.3781) |
| Sentence-BERT — Reimers & Gurevych, 2019 | Usable sentence embeddings via siamese training | [arXiv:1908.10084](https://arxiv.org/abs/1908.10084) |
| Dense Passage Retrieval (DPR) — Karpukhin et al., 2020 | Dense retrieval beats BM25 | [arXiv:2004.04906](https://arxiv.org/abs/2004.04906) |
| Text Embeddings by Weakly-Supervised Contrastive Pre-training (E5) — Wang et al., 2022 | Modern embedding recipe; note the instruction prefixes | [arXiv:2212.03533](https://arxiv.org/abs/2212.03533) |

## The best explainers ever written about transformers
- **The Illustrated Transformer** — Jay Alammar: https://jalammar.github.io/illustrated-transformer/
- **The Annotated Transformer** — Harvard NLP (paper + line-by-line code): https://nlp.seas.harvard.edu/annotated-transformer/
- **Let's build GPT from scratch** — Karpathy (2h video, builds it live): https://www.youtube.com/watch?v=kCc8FmEb1nY
- **3Blue1Brown — Attention in transformers, visually**: https://www.3blue1brown.com/topics/neural-networks
- **Transformer Circuits / induction heads** — Anthropic: https://transformer-circuits.pub/
