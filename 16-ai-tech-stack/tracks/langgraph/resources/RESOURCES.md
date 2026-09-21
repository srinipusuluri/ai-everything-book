# 🔗 Resources — LangGraph

## Documentation (keep two tabs open)
| Page | What's inside |
|---|---|
| https://langchain-ai.github.io/langgraph/ | The canonical LangGraph docs: graphs, state, checkpointing, interrupts |
| https://langchain-ai.github.io/langgraph/concepts/ | The concept guides — read before the how-tos; the mental model lives here |
| https://langchain-ai.github.io/langgraph/how-tos/ | Task-oriented recipes: retries, subgraphs, time travel, map-reduce |
| https://docs.langchain.com/ | The unified LangChain/LangGraph docs home (v1 era) |

## Repositories
| Repo | What's inside |
|---|---|
| https://github.com/langchain-ai/langgraph | The library itself; `libs/langgraph` is readable and heavily commented |
| https://github.com/langchain-ai/langgraphjs | The TypeScript twin — worth a skim for the shared mental model |
| https://github.com/langchain-ai/langgraph-examples | Runnable example apps (agents, RAG, customer support) |

## Courses (free)
| Course | Why | Link |
|---|---|---|
| **LangChain Academy — Intro to LangGraph** | The official course, taught by the framework authors; state and human-in-the-loop chapters are the good parts | https://academy.langchain.com/courses/intro-to-langgraph |
| **DeepLearning.AI — AI Agents in LangGraph** | Short, hands-on, agentic search and multi-agent examples | https://www.deeplearning.ai/short-courses/ai-agents-in-langgraph/ |

## Blogs & papers worth your time
- The LangGraph concept guide on persistence is the best short explanation of checkpointing semantics —
  read it after [../code/checkpoint_and_interrupt.py](../code/checkpoint_and_interrupt.py), not before.
- **ReAct** ([arXiv:2210.03629](https://arxiv.org/abs/2210.03629)) — the loop you rebuild by hand in this track
- **Building Effective Agents** — Anthropic: https://www.anthropic.com/engineering/building-effective-agents
  (the workflows-vs-agents distinction that decides whether you need this library at all)
- The annotated paper list for this track: [../papers/PAPERS.md](../papers/PAPERS.md)

## Ecosystem neighbours
| Tool | Relationship to LangGraph |
|---|---|
| https://smith.langchain.com/ | Tracing + evals; the observability half of the story ([../langsmith/](../langsmith/)) |
| https://www.temporal.io/ | The durable-execution engine to compare against when reliability is the driver |
| https://github.com/crewAIInc/crewAI | CrewAI: the role-based multi-agent alternative — less explicit, less controllable |
| https://github.com/microsoft/autogen | AutoGen: conversational multi-agent; the other main orchestration camp |

## Communities
- LangChain forum — https://forum.langchain.com/
- GitHub Discussions on the langgraph repo — the maintainers answer; search before filing
