# 🔗 Resources — AI Architecture

## Reference architectures and guides
| Resource | Why | Link |
|---|---|---|
| **AWS — Generative AI on AWS reference architectures** | Concrete, provider-specific versions of the layered architecture in notes/01 | https://aws.amazon.com/generative-ai/architectures/ |
| **Google Cloud — Generative AI application architectures** | A second provider's take — compare the layer boundaries | https://cloud.google.com/architecture/genai |
| **Microsoft Azure — AI application architecture design** | A third — notice what's the same across all three | https://learn.microsoft.com/en-us/azure/architecture/ai-ml/ |
| **a16z — Emerging Architectures for LLM Applications** | The widely-cited early map of this exact stack | https://a16z.com/emerging-architectures-for-llm-applications/ |

## Gateway and routing tools
| Tool | What it does | Link |
|---|---|---|
| **LiteLLM** | Open-source model gateway — unifies ~100 providers behind one API, does routing/fallback/budgets | https://github.com/BerriAI/litellm |
| **Portkey** | Hosted AI gateway with caching, routing, and observability built in | https://portkey.ai/ |
| **OpenRouter** | A hosted router across many model providers — useful to study its API design | https://openrouter.ai/ |

## Vector databases (for the data-architecture section)
| Option | Model | Link |
|---|---|---|
| **Qdrant** | Open-source, self-hostable, strong hybrid search support | https://qdrant.tech/ |
| **Weaviate** | Open-source, hybrid search, GraphQL API | https://weaviate.io/ |
| **pgvector** | A Postgres extension — the "use what you already run" option | https://github.com/pgvector/pgvector |
| **Pinecone** | Fully managed, no ops burden, usage-based cost | https://www.pinecone.io/ |

## Observability and tracing
- LangSmith — see [../16-ai-tech-stack/tracks/langsmith/](../16-ai-tech-stack/tracks/langsmith/) for the full track
- Langfuse (open-source alternative) — https://langfuse.com/
- OpenTelemetry — https://opentelemetry.io/

## Communities
- The Pragmatic Engineer newsletter — regularly covers real production AI-architecture postmortems
- r/mlops — operational war stories from teams running this stack
- InfoQ / QCon talks tagged "LLM" or "generative AI" — real architecture talks from real production teams

## Where to go next
- [../16-ai-tech-stack/](../16-ai-tech-stack/) for hands-on implementation of every layer described here.
- [../13-ai-security/](../13-ai-security/) for the security-control placement this module only sketches.
- [../12-ai-governance/](../12-ai-governance/) for why the deployment/registry pattern in notes/02 §4.4 is a compliance requirement, not just good practice.
