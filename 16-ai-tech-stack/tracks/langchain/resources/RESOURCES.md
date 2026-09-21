# 🔗 Resources — LangChain

## Documentation
| Page | What's inside |
|---|---|
| https://python.langchain.com/docs/introduction/ | The current docs front door (v1 era) |
| https://python.langchain.com/docs/concepts/ | Concept guides: messages, tools, retrieval, structured output |
| https://python.langchain.com/api_reference/core/index.html | `langchain-core` API reference — the `Runnable` surface this track teaches |
| https://docs.langchain.com/ | Unified docs home; the migration notes from 0.x are worth reading even if you never used 0.x |

## Repositories
| Repo | What's inside |
|---|---|
| https://github.com/langchain-ai/langchain | The monorepo: `langchain-core` is the part worth reading; `langchain-classic` is the museum |
| https://github.com/langchain-ai/langgraph | Where agents went when they needed control ([../langgraph/](../langgraph/)) |
| https://github.com/langchain-ai/langchainjs | The TypeScript twin; the abstractions map almost one-to-one |

## Courses
| Course | Why | Link |
|---|---|---|
| **LangChain Academy** | Free official courses; the LangGraph one matters more than the LangChain one — telling | https://academy.langchain.com/ |
| **DeepLearning.AI — LangChain for LLM Application Development** | The famous 1-hour course; note it teaches the 0.x API — a useful archaeology exercise | https://www.deeplearning.ai/short-courses/langchain-for-llm-application-development/ |

## Blogs
- The LangChain blog tracks the 0.x -> 1.x rewrites: https://blog.langchain.com/
  Read the v1 announcement and the LCEL retrospectives; they are unusually honest about what didn't work.
- Hamel Husain's writing on evals is the antidote to framework-first thinking: https://hamel.dev/

## Communities
- LangChain forum — https://forum.langchain.com/
- GitHub Issues on the main repo — half of real-world LangChain knowledge lives in issue threads
- r/LangChain — unofficial, fast-moving, variable signal

## Also in this repo
- Everything here runs offline against fake chat models in [../code/fakes.py](../code/fakes.py)
- The escalation path when control matters: [../langgraph/](../langgraph/)
- The observability layer for whatever you build: [../langsmith/](../langsmith/)
