# 📄 Papers & Primary Sources — The LLM Model Landscape

This module leans on benchmark and evaluation methodology papers more than architecture papers (those
live in Module 04). Read these to understand what a leaderboard number actually measures.

## Benchmark methodology and its limits
| Paper | Year | Why it matters | Link |
|---|---|---|---|
| **Measuring Massive Multitask Language Understanding** (MMLU) — Hendrycks et al. | 2020 | The benchmark referenced constantly; also read its known-error follow-ups before trusting a score | [arXiv:2009.03300](https://arxiv.org/abs/2009.03300) |
| **Are We Done With MMLU?** — Gema et al. | 2024 | Documents label errors and near-saturation in MMLU — the "distrust a single score" case, with evidence | [arXiv:2406.04127](https://arxiv.org/abs/2406.04127) |
| **GPQA: A Graduate-Level Google-Proof Q&A Benchmark** — Rein et al. | 2023 | The harder benchmark that replaced MMLU as a frontier-model differentiator | [arXiv:2311.12022](https://arxiv.org/abs/2311.12022) |
| **SWE-bench: Can Language Models Resolve Real-World GitHub Issues?** — Jimenez et al. | 2023 | The current standard for coding-agent capability; read the contamination-risk discussion | [arXiv:2310.06770](https://arxiv.org/abs/2310.06770) |
| **Chatbot Arena: An Open Platform for Evaluating LLMs by Human Preference** — Chiang et al. | 2024 | The methodology behind Elo-style leaderboards, and its own documented biases (style, length) | [arXiv:2403.04132](https://arxiv.org/abs/2403.04132) |
| **HELM: Holistic Evaluation of Language Models** — Liang et al. | 2022 | A multi-metric alternative to single-number leaderboards — worth knowing this exists | [arXiv:2211.09110](https://arxiv.org/abs/2211.09110) |

## Contamination and reproducibility
| Paper | Year | Why it matters | Link |
|---|---|---|---|
| **Data Contamination Quiz: A Tool to Detect and Estimate Contamination in LLMs** — Golchin & Surdeanu | 2023 | A practical method for the exact concern `benchmark_literacy_demo.py` teaches | [arXiv:2311.06233](https://arxiv.org/abs/2311.06233) |
| **Time Travel in LLMs: Tracing Data Contamination in Large Language Models** — Golchin & Surdeanu | 2023 | Companion paper, broader detection framework | [arXiv:2308.08493](https://arxiv.org/abs/2308.08493) |

## Scaling and the tier structure (deeper treatment in Module 04)
| Paper | Year | Link |
|---|---|---|
| Training Compute-Optimal Large Language Models (Chinchilla) — Hoffmann et al. | 2022 | [arXiv:2203.15556](https://arxiv.org/abs/2203.15556) |
| Scaling Laws for Neural Language Models — Kaplan et al. | 2020 | [arXiv:2001.08361](https://arxiv.org/abs/2001.08361) |

## Open-weights model families (primary technical reports)
| Report | Link |
|---|---|
| Llama 3 Herd of Models — Meta AI | [arXiv:2407.21783](https://arxiv.org/abs/2407.21783) |
| Mistral 7B — Jiang et al. | [arXiv:2310.06825](https://arxiv.org/abs/2310.06825) |
| DeepSeek-V3 Technical Report | [arXiv:2412.19437](https://arxiv.org/abs/2412.19437) |
| Qwen2.5 Technical Report | [arXiv:2412.15115](https://arxiv.org/abs/2412.15115) |

Model technical reports go stale fast by design — read them for methodology (how they trained, how they
evaluated) rather than for the specific numbers, which the next release will supersede.
