# 📄 Papers & Primary Sources — AI Architecture

This module is more "systems engineering" than "research field," so the reading list leans toward
engineering blogs, reference architectures, and a few foundational distributed-systems papers whose
lessons transfer directly.

## Foundational systems thinking
| Source | Why it matters | Link |
|---|---|---|
| **Fallacies of Distributed Computing** — L. Peter Deutsch et al. | Still true, and every "the model API is just a function call" bug traces back to ignoring one of these | https://en.wikipedia.org/wiki/Fallacies_of_distributed_computing |
| **Release It!** — Michael Nygard (book, circuit breakers chapter) | The circuit-breaker pattern this module's gateway implements, from its original source | https://pragprog.com/titles/mnee2/release-it-second-edition/ |
| **The Tail at Scale** — Dean & Barroso, CACM 2013 | Why p99 latency dominates real user experience — directly relevant to model routing decisions | https://research.google/pubs/pub40801/ |

## LLM-system architecture, from the labs that operate them
| Source | Why it matters | Link |
|---|---|---|
| **Anthropic — Building Effective Agents** | The orchestration-layer design principles referenced throughout notes/01 | https://www.anthropic.com/research/building-effective-agents |
| **OpenAI — Production Best Practices** | Rate limiting, retries, and cost controls from a provider's own guidance | https://platform.openai.com/docs/guides/production-best-practices |
| **Efficient Memory Management for LLM Serving with PagedAttention (vLLM)** — Kwon et al., 2023 | The paper behind the serving-layer techniques referenced from Module 04 | https://arxiv.org/abs/2309.06180 |
| **A Systematic Survey of Prompt Engineering in LLMs** (architecture-relevant sections) | Useful for the prompt-as-deploy-artifact argument in notes/02 §4.1 | https://arxiv.org/abs/2402.07927 |

## Vector database and retrieval infrastructure
| Source | Why it matters | Link |
|---|---|---|
| **Efficient and Robust Approximate Nearest Neighbor Search Using HNSW** — Malkov & Yashunin, 2016 | The algorithm underneath most production vector search — reference from Module 08 | https://arxiv.org/abs/1603.09320 |
| **Milvus: A Purpose-Built Vector Data Management System** — Wang et al., 2021 | A concrete case study in the vector-DB selection criteria from notes/01 §5.2 | https://arxiv.org/abs/2104.06678 |

## Observability
| Source | Why it matters | Link |
|---|---|---|
| **OpenTelemetry — GenAI Semantic Conventions** | The emerging standard for tracing LLM calls, referenced from Module 16's LangSmith track | https://opentelemetry.io/docs/specs/semconv/gen-ai/ |

## Where the real reading is
Most of what this module teaches doesn't live in papers — it lives in production postmortems and
architecture blogs from companies operating these systems at scale. Treat engineering blogs (Anthropic,
OpenAI, Netflix, Uber, Stripe) as primary sources for this module specifically, more than for any other
module in this track.
