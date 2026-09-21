# 🔗 Resources — LangSmith, Tracing & LLM Observability

## Start here
| Resource | Who it's for | Link |
|---|---|---|
| **LangSmith docs home** | The canonical entry point; the left nav is the product map | https://docs.langchain.com/langsmith/home |
| **LangSmith app** | Free tier is enough for everything in [../lab/EXERCISES.md](../lab/EXERCISES.md) §7 | https://smith.langchain.com/ |
| **LangChain Academy** | Free courses; the LangSmith and LangGraph ones pair with this track | https://academy.langchain.com/ |
| **LangChain blog** | Where new LangSmith capabilities are announced before the docs settle | https://blog.langchain.com/ |

## Repositories worth cloning
| Repo | What's inside |
|---|---|
| https://github.com/langchain-ai/langsmith-sdk | The Python + JS SDKs. Read `python/langsmith/run_helpers.py` — it is the production version of [`../code/minimal_tracer.py`](../code/minimal_tracer.py) |
| https://github.com/langchain-ai/openevals | Prebuilt LLM-as-judge evaluators (correctness, groundedness, conciseness) you can read and steal the prompts from |
| https://github.com/langchain-ai/langsmith-cookbook | Task-shaped recipes: CI evals, feedback plumbing, dataset construction |
| https://github.com/langfuse/langfuse | The main open-source alternative. Self-hostable; worth running once to compare data models |
| https://github.com/Arize-ai/phoenix | OTel-native open-source tracing + eval; runs in a notebook |
| https://github.com/open-telemetry/semantic-conventions-genai | The vendor-neutral GenAI span/attribute spec |
| https://github.com/traceloop/openllmetry | OTel instrumentation for LLM libraries; the format LangSmith also accepts |
| https://github.com/confident-ai/deepeval | Pytest-style LLM evals — the "evals as unit tests" ergonomic, if that is your taste |
| https://github.com/explodinggradients/ragas | RAG-specific metrics (faithfulness, context precision/recall) that plug into an eval harness |

## Alternatives, first-party docs
Read at least two of these before you commit to one vendor. Their data models differ in ways that matter.

| Tool | Link |
|---|---|
| Langfuse | https://langfuse.com/docs |
| Arize Phoenix | https://arize.com/docs/phoenix |
| Braintrust | https://www.braintrust.dev/docs |
| Weights & Biases Weave | https://weave-docs.wandb.ai/ |
| Helicone | https://docs.helicone.ai/ |
| OpenTelemetry (tracing concepts) | https://opentelemetry.io/docs/concepts/signals/traces/ |

## Adjacent tracks in this repo
| Where | Why you'd go there |
|---|---|
| [../../../15-ai-evals/](../../../15-ai-evals/) | The theory this track is the tooling for. Read it. |
| [../../langchain/](../../langchain/) · [../../langgraph/](../../langgraph/) | The frameworks that trace automatically |
| [../../../08-rag/](../../../08-rag/) | Where most "hallucinations" in a traced system actually come from |
| [../../../06-ai-agents/](../../../06-ai-agents/) · [../../../07-agentic-ai/](../../../07-agentic-ai/) | Multi-step loops are the reason a tree view beats a log |
| [../../../13-ai-security/](../../../13-ai-security/) | PII redaction, adversarial eval sets |
| [../../../12-ai-governance/](../../../12-ai-governance/) · [../../../14-ai-compliance/](../../../14-ai-compliance/) | Traces and experiments as audit evidence |
| [../../../11-llm-models/](../../../11-llm-models/) | Model migration is a pairwise-eval problem |

## Cheat sheet — environment variables
```bash
LANGSMITH_TRACING=true                 # master switch; forget this and nothing appears
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=my-app-prod          # default tracing project
LANGSMITH_ENDPOINT=https://eu.api.smith.langchain.com   # data region (EU shown)
LANGSMITH_TRACING_SAMPLING_RATE=0.1    # 0.0-1.0, applied at the trace root
LANGSMITH_HIDE_INPUTS=true             # blunt PII kill-switch
LANGSMITH_HIDE_OUTPUTS=true
LANGSMITH_HIDE_METADATA=true
```

## Communities
- LangChain Forum — https://forum.langchain.com/
- LangChain on GitHub Discussions — https://github.com/langchain-ai/langchain/discussions
- r/LLMDevs — https://www.reddit.com/r/LLMDevs/
- OpenTelemetry community — https://opentelemetry.io/community/

## Also see
- [../../../_shared/cheatsheets/](../../../_shared/cheatsheets/)
