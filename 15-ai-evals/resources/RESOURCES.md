# 🔗 Resources — AI Evaluation

## Courses & long-form guides (free)
| Resource | Why | Link |
|---|---|---|
| **Hamel Husain — "Your AI Product Needs Evals"** | The single best practitioner essay on this whole topic; real case study, no hand-waving | https://hamel.dev/blog/posts/evals/ |
| **Hamel Husain — AI Evals notes/course hub** | Ongoing collection of eval-focused writing and the paid "AI Evals for Engineers & PMs" course | https://hamel.dev/notes/llm/evals/ |
| **DeepLearning.AI — Evaluating and Debugging Generative AI** | Short, free, hands-on course from the W&B team on tracking experiments and evaluating LLM apps | https://www.deeplearning.ai/short-courses/evaluating-debugging-generative-ai/ |
| **DeepLearning.AI — Building and Evaluating Advanced RAG** | RAG-specific evaluation (faithfulness, relevance) with TruLens and LlamaIndex | https://www.deeplearning.ai/short-courses/building-evaluating-advanced-rag/ |
| **Stanford HELM project site** | The live, running implementation of the HELM paper's holistic multi-metric evaluation | https://crfm.stanford.edu/helm/ |
| **LMArena (formerly Chatbot Arena) leaderboard + methodology** | Read the methodology page, not just the leaderboard, before citing an Arena rank | https://lmarena.ai/ (rebranded to https://arena.ai/ in 2026) |

## Eval frameworks & repositories
| Repo | What's inside |
|---|---|
| https://github.com/openai/evals | OpenAI's open eval framework and a large registry of community-contributed eval templates |
| https://github.com/confident-ai/deepeval | Pytest-style LLM eval framework: G-Eval, hallucination, answer relevancy, RAGAS-compatible metrics, CI-friendly |
| https://github.com/explodinggradients/ragas | The reference RAG evaluation library — faithfulness, context precision/recall, answer relevance; owned in depth by [`../08-rag/`](../08-rag/) |
| https://github.com/promptfoo/promptfoo | CLI/CI-first prompt and RAG testing, matrix comparisons across models, and built-in red-teaming/vulnerability scanning |
| https://github.com/EleutherAI/lm-evaluation-harness | The standard open harness for running academic benchmarks (MMLU, GPQA, etc.) against any model — pairs with the benchmark-literacy section of note 01 |
| https://github.com/stanford-crfm/helm | The HELM paper's actual implementation |
| https://github.com/langchain-ai/langsmith-sdk | The SDK behind `evaluate()`/`aevaluate()` covered in [`../16-ai-tech-stack/tracks/langsmith/`](../16-ai-tech-stack/tracks/langsmith/) |
| https://github.com/langfuse/langfuse | Open-source, self-hostable alternative with a thinner but growing eval layer |

## Cheat sheets & reference docs
- OpenAI Evals design doc and registry format: https://github.com/openai/evals/blob/main/docs/build-eval.md
- Cohen's kappa, worked through carefully (general reference, not LLM-specific): https://en.wikipedia.org/wiki/Cohen%27s_kappa
- Wilson score interval derivation: https://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval#Wilson_score_interval
- Also see [../../_shared/cheatsheets/](../../_shared/cheatsheets/)

## Communities
- Hamel Husain's "AI Evals" Discord/newsletter community (linked from https://hamel.dev/) — the most active practitioner-level discussion of eval craft specifically, as opposed to general LLM-ops
- r/LocalLLaMA and the EleutherAI Discord (shared with [Module 04](../../04-llm/)) — useful for benchmark-methodology discussion whenever a new leaderboard controversy breaks
- LangChain / LangSmith community Discord — practical `evaluate()` and dataset-design questions, tooling side of this module
