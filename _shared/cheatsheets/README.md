# 🗂️ Cheatsheets

Quick-reference tables pulled from across the track. Each links back to the module note that derives it —
use these for recall, not for first learning.

## Loss functions ([01](../../01-ml-foundations/notes/01-core-concepts.md))
| Task | Loss | Notes |
|---|---|---|
| Regression | MSE / MAE / Huber | MSE penalizes outliers most; Huber compromises |
| Binary classification | Binary cross-entropy | pair with sigmoid |
| Multi-class | Categorical cross-entropy | pair with softmax; the LLM pretraining loss |
| Ranking / retrieval | Contrastive / InfoNCE | powers embedding models — see Module 08 |

## Sampling parameters ([04](../../04-llm/notes/02-inference-and-adaptation.md))
| Parameter | What it does | Typical range |
|---|---|---|
| Temperature | scales logits before softmax; higher = more random | 0.0–1.2 |
| top-p (nucleus) | samples from the smallest set of tokens covering p probability mass | 0.9–0.95 |
| top-k | restricts sampling to the k most likely tokens | 20–50 |
| Repetition penalty | discourages repeating already-generated tokens | 1.0–1.3 |

## Attention shapes ([03](../../03-nlp/notes/02-transformers.md))
| Symbol | Meaning |
|---|---|
| `d_model` | the residual stream width (e.g. 4096) |
| `n_heads` | number of attention heads |
| `d_head` | `d_model / n_heads`, the per-head dimension |
| `n_ctx` | context length in tokens |
| KV cache size | `2 × n_layers × n_kv_heads × d_head × n_ctx × batch × bytes_per_elem` |

## Model adaptation decision order ([04](../../04-llm/notes/02-inference-and-adaptation.md))
`Prompting → Few-shot → RAG (08) → LoRA fine-tune → Full fine-tune → Continued pretraining`
— try each in order; only move to the next when the current one demonstrably fails on your eval set (15).

## RAG retrieval metrics ([08](../../08-rag/))
| Metric | Measures |
|---|---|
| Recall@k | fraction of relevant docs found in the top k |
| MRR | how high the FIRST relevant doc ranks, averaged |
| NDCG | ranking quality weighted by graded relevance |
| Faithfulness | does the generated answer only use retrieved content |

## OWASP-style LLM risk categories ([13](../../13-ai-security/))
Prompt injection (direct/indirect) · insecure output handling · training data poisoning ·
model denial of service · supply chain vulnerabilities · sensitive info disclosure ·
insecure plugin/tool design · excessive agency · overreliance · model theft.
See `13-ai-security/notes/` for the verified current list and mitigations for each.

## Statistical significance for evals ([15](../../15-ai-evals/))
- A score difference on n<100 examples is usually noise — compute a confidence interval (Wilson score
  interval for proportions) before trusting it.
- Use a **paired** test (McNemar's, paired bootstrap) when comparing two models/prompts on the *same*
  examples — it's far more powerful than comparing independent means.
- Binary rubric criteria produce better human/judge agreement (Cohen's kappa) than 1–10 Likert scales.
