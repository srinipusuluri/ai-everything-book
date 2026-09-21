# 🔗 Resources — Agentic AI Systems

## Courses & talks
| Resource | Why | Link |
|---|---|---|
| **Anthropic — Building Effective Agents** | The essay this module's "one agent with better tools" position is drawn from | https://www.anthropic.com/research/building-effective-agents |
| **Anthropic — How we built our multi-agent research system** | The 15x-token-cost finding, straight from the team that shipped it | https://www.anthropic.com/engineering/multi-agent-research-system |
| **Cognition — Don't Build Multi-Agents** | The dissenting, equally-informed view — read both and form your own position | https://cognition.ai/blog/dont-build-multi-agents |
| **DeepLearning.AI — Multi AI Agent Systems with crewAI** | Free short course, topology patterns in a framework-specific setting | https://www.deeplearning.ai/short-courses/multi-ai-agent-systems-with-crewai/ |
| **Berkeley CS294 — Large Language Model Agents** | Academic treatment of planning, tool use, and multi-agent coordination | https://llmagents-learning.org/ |

## Repositories worth reading
| Repo | What's inside |
|---|---|
| https://github.com/langchain-ai/langgraph | The topology primitives this module describes in the abstract — see [../16-ai-tech-stack/tracks/langgraph/](../16-ai-tech-stack/tracks/langgraph/) |
| https://github.com/langchain-ai/langgraph-supervisor-py | A thin, readable reference implementation of the supervisor pattern |
| https://github.com/langchain-ai/langgraph-swarm-py | A thin, readable reference implementation of the hand-off/swarm pattern |
| https://github.com/microsoft/autogen | A different design point for multi-agent conversation patterns |
| https://github.com/crewAIInc/crewAI | Role-based multi-agent framework — a good second reference topology |
| https://github.com/openai/swarm | OpenAI's minimal, educational multi-agent hand-off primitives |
| https://a2a-protocol.org/ | The Agent2Agent protocol spec referenced in notes/02 §2 |

## Communities
- r/LocalLLaMA and r/MachineLearning — active discussion of agent architecture trade-offs
- LangChain Discord / Slack — practical topology debugging war stories
- Anthropic's Discord — agent design discussions specific to Claude-based systems

## Where to go next
- [../06-ai-agents/](../06-ai-agents/) if you arrived here first — this module assumes single-agent theory.
- [../16-ai-tech-stack/tracks/langgraph/](../16-ai-tech-stack/tracks/langgraph/) for the runtime that implements every topology in notes/01 §2.
- [../15-ai-evals/](../15-ai-evals/) for how to actually measure whether a multi-agent system is worth its cost.
