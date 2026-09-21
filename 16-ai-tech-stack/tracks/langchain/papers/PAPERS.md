# 📄 Primary Sources — LangChain

LangChain is a framework, not a research programme, so "papers" here means two things: **the official
documentation you should treat as the source of truth**, and **the handful of papers whose ideas the
framework is a direct implementation of**. Every URL below was fetched and returned 200 while writing
this track.

---

## Read these three first

| # | Source | Why it matters | Link |
|---|--------|----------------|------|
| 1 | **LangChain Philosophy & timeline** | The maintainers' own account of every pivot from v0.0.1 (Oct 2022) to v1.0 (Oct 2025) and Deep Agents (Mar 2026). Read it before any tutorial — it tells you which era the tutorial is from. | <https://docs.langchain.com/oss/python/langchain/philosophy> |
| 2 | **LangChain v1 migration guide** | The exact namespace changes: what stayed in `langchain`, what moved to `langchain-classic`, `create_react_agent` → `create_agent`, hooks → middleware. The single most useful page in the docs. | <https://docs.langchain.com/oss/python/migrate/langchain-v1> |
| 3 | **ReAct: Synergizing Reasoning and Acting in Language Models** — Yao et al., 2022 | The paper LangChain's original agents implemented. Worth reading to see how much of today's "agent loop" is just tool calling with better plumbing. | [arXiv:2210.03629](https://arxiv.org/abs/2210.03629) |

---

## Official documentation (the source of truth)

| Page | What it settles | Link |
|---|---|---|
| Overview | `create_agent` as the current front door; relationship to LangGraph | <https://docs.langchain.com/oss/python/langchain/overview> |
| Install | Python 3.10+, provider packages are separate installs | <https://docs.langchain.com/oss/python/langchain/install> |
| Component architecture | The canonical diagrams: ingest → embed → retrieve → generate | <https://docs.langchain.com/oss/python/langchain/component-architecture> |
| Models | `init_chat_model`, `bind_tools`, `with_structured_output`, `usage_metadata`, rate limiters | <https://docs.langchain.com/oss/python/langchain/models> |
| Messages | Standard content blocks (`.content_blocks`), the v1 message format | <https://docs.langchain.com/oss/python/langchain/messages> |
| Tools | `@tool`, `ToolRuntime`, `return_direct`, `wrap_tool_call` error middleware | <https://docs.langchain.com/oss/python/langchain/tools> |
| Structured output | `ToolStrategy` vs `ProviderStrategy` and when each is chosen | <https://docs.langchain.com/oss/python/langchain/structured-output> |
| Retrieval | 2-step RAG vs agentic RAG vs hybrid, with a latency/control table | <https://docs.langchain.com/oss/python/langchain/retrieval> |
| Short-term memory | Checkpointers, `thread_id`, trimming and `SummarizationMiddleware` | <https://docs.langchain.com/oss/python/langchain/short-term-memory> |
| Streaming | `stream_mode` values and the newer typed event-streaming API | <https://docs.langchain.com/oss/python/langchain/streaming> |
| Observability | The two environment variables that turn on tracing | <https://docs.langchain.com/oss/python/langchain/observability> |
| Unit testing | The official position on faking models in tests | <https://docs.langchain.com/oss/python/langchain/test/unit-testing> |
| Python changelog | Check this before every upgrade. Not optional. | <https://docs.langchain.com/oss/python/langchain/changelog-py> |
| API reference | Signatures, not prose. Where you go when the guide is ambiguous. | <https://reference.langchain.com/python/> |
| `llms.txt` index | Machine-readable index of every docs page — useful for your own RAG over the docs | <https://docs.langchain.com/llms.txt> |

> **Warning about older docs.** `https://python.langchain.com/` still resolves and still surfaces in
> search results. Much of it describes v0. When in doubt, prefer `docs.langchain.com/oss/python/`
> and check the migration guide.

---

## Announcements worth reading once

| Source | Takeaway | Link |
|---|---|---|
| LangChain & LangGraph 1.0 (blog) | Why LangGraph became the runtime and LangChain the high-level API on top of it | <https://www.langchain.com/blog/langchain-langgraph-1dot0> |
| LangChain 1.0 GA (changelog) | The dated, terse version of the same thing | <https://changelog.langchain.com/announcements/langchain-1-0-now-generally-available> |
| Runtimes, frameworks, and harnesses | The maintainers' taxonomy: what is a runtime, what is a harness, where each product sits | <https://docs.langchain.com/oss/python/concepts/products> |

---

## Papers the framework implements

| Paper | Year | One-line takeaway | Link |
|---|---|---|---|
| **ReAct: Synergizing Reasoning and Acting** — Yao et al. | 2022 | Interleave reasoning traces with tool actions. LangChain's first agents were a literal implementation; `create_agent` is its descendant with the JSON parsing replaced by native tool calling. | [arXiv:2210.03629](https://arxiv.org/abs/2210.03629) |
| **Retrieval-Augmented Generation for Knowledge-Intensive NLP** — Lewis et al. | 2020 | The origin of RAG. Note that the paper trains retriever and generator jointly; what the industry calls RAG is the frozen, prompt-stuffing approximation LangChain popularised. | [arXiv:2005.11401](https://arxiv.org/abs/2005.11401) |
| **Toolformer: Language Models Can Teach Themselves to Use Tools** — Schick et al. | 2023 | Tool use as a learned capability rather than a prompting trick — the intellectual bridge to native tool-calling APIs, which is what `bind_tools` targets today. | [arXiv:2302.04761](https://arxiv.org/abs/2302.04761) |
| **Language Models are Few-Shot Learners (GPT-3)** — Brown et al. | 2020 | Why few-shot prompt templates exist at all. Read §3 and then look at `FewShotChatMessagePromptTemplate` with fresh eyes. | [arXiv:2005.14165](https://arxiv.org/abs/2005.14165) |

---

## Read the source — it is unusually readable

`langchain-core` is small and deliberately dependency-light. Three files repay an hour each:

| File | Why | Where |
|---|---|---|
| `langchain_core/runnables/base.py` | `Runnable`, `RunnableSequence`, `__or__`. The entire abstraction fits in one class hierarchy. | <https://github.com/langchain-ai/langchain> |
| `langchain_core/language_models/chat_models.py` | `BaseChatModel.generate`, and the default `with_structured_output` — it is `bind_tools` plus a parser, exactly as advertised. | same repo |
| `langchain_core/language_models/fake_chat_models.py` | The official fakes. Compare with [`../code/fakes.py`](../code/fakes.py). | same repo |

In your venv they are at
`/Users/srinip/ai-all/.venv/lib/python3.14/site-packages/langchain_core/`.

## How to read framework docs (30 minutes, 3 passes)

1. **Pass 1 (5 min):** find the version. Which major? Which page in the changelog does it predate?
   A doc without a version is a doc you cannot trust.
2. **Pass 2 (15 min):** find the *interface*, not the tutorial. What methods must I implement? What
   does this return? Tutorials rot; interfaces are the contract.
3. **Pass 3 (10 min):** find the failure modes. Search the page for "error", "raises", "warning",
   "deprecated". That is where the real information is.
