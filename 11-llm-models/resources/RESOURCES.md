# 🔗 Resources — The LLM Model Landscape

## Live leaderboards and comparisons (bookmark, don't screenshot)
| Resource | What it shows | Link |
|---|---|---|
| **LMSYS Chatbot Arena** | Human-preference Elo ratings across providers | https://lmarena.ai/ |
| **Artificial Analysis** | Independent price/latency/quality comparison across providers — the closest thing to a neutral cross-provider view | https://artificialanalysis.ai/ |
| **Hugging Face Open LLM Leaderboard** | Open-weights model benchmarks in one place | https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard |
| **Vellum LLM Leaderboard** | Task-specific comparisons (coding, reasoning, etc.) | https://www.vellum.ai/llm-leaderboard |
| **SWE-bench leaderboard** | Coding-agent capability specifically | https://www.swebench.com/ |

## Official pricing and model pages (the only sources you should treat as authoritative)
| Provider | Link |
|---|---|
| Anthropic | https://claude.com/pricing · https://docs.claude.com/ |
| OpenAI | https://openai.com/api/pricing/ · https://platform.openai.com/docs/models |
| Google | https://ai.google.dev/pricing |
| Meta Llama | https://ai.meta.com/llama/ |
| Mistral | https://docs.mistral.ai/ |
| DeepSeek | https://api-docs.deepseek.com/quick_start/pricing/ |

## Courses & deeper reading
| Resource | Why | Link |
|---|---|---|
| **Stanford CS324 — Advances in Foundation Models** | Academic treatment of the model landscape and evaluation | https://stanford-cs324.github.io/winter2023/ |
| **Hugging Face — Open LLM Leaderboard methodology docs** | How to actually read a leaderboard's methodology before trusting it | https://huggingface.co/docs/leaderboards/ |
| **"You Don't Need a Bigger Boat"-style engineering blogs on model selection** | Search for recent posts from teams documenting a real model-migration decision — more useful than any static list | — |

## Communities
- r/LocalLLaMA — active open-weights model tracking and real-world benchmarking
- Hugging Face forums and Discord — model release discussion as it happens
- Provider status pages and changelogs — subscribe directly if a model is load-bearing for your product

## Where to go next
- [../04-llm/](../04-llm/) for how these models are actually built and the theory behind the tiers.
- [../15-ai-evals/](../15-ai-evals/) for how to build the eval set that should decide your model choice — not a leaderboard.
- [../10-ai-architecture/](../10-ai-architecture/) for the model-gateway pattern that lets you avoid ever betting on just one model.
