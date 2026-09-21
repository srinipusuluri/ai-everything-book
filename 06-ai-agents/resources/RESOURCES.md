# 🔗 Resources — AI Agents

## Courses & lectures (free)

| Resource | Why | Link |
|---|---|---|
| **LLM Agents MOOC (Berkeley)** | The most rigorous free course on this exact material — reasoning, planning, tool use, memory, evaluation, taught by the people who wrote several of the canon papers | https://llmagents-learning.org/f24 |
| **DeepLearning.AI — Functions, Tools and Agents with LangChain** | Short, hands-on: the tool-calling round trip and the ReAct loop, built incrementally | https://www.deeplearning.ai/short-courses/functions-tools-agents-langchain/ |
| **DeepLearning.AI — AI Agents in LangGraph** | The runtime side of this module — pairs directly with [`../../16-ai-tech-stack/tracks/langgraph/`](../../16-ai-tech-stack/tracks/langgraph/) | https://www.deeplearning.ai/short-courses/ai-agents-in-langgraph/ |
| **Prompting Guide — LLM Agents** | A concise, well-maintained reference on ReAct, planning and agent architectures, with links back to the primary papers | https://www.promptingguide.ai/research/llm-agents |

## Repositories worth cloning

| Repo | What's inside |
|---|---|
| https://github.com/ysymyth/ReAct | The original ReAct paper's code and prompts — read the actual few-shot exemplars |
| https://github.com/noahshinn/reflexion | Reference implementation of Reflexion's verbal self-critique loop |
| https://github.com/princeton-nlp/tree-of-thought-llm | Tree of Thoughts reference implementation, including the scoring/pruning logic |
| https://github.com/ShishirPatil/gorilla | Large-scale API/tool-calling benchmark and models — the "too many tools" evidence in code form |
| https://github.com/anthropics/anthropic-cookbook | Runnable tool-use and agent recipes against the Claude API |
| https://github.com/langchain-ai/langchain | The tool/model abstraction layer most agent frameworks build on — see [`../../16-ai-tech-stack/tracks/langchain/`](../../16-ai-tech-stack/tracks/langchain/) |
| https://github.com/langchain-ai/langgraph | The durable, resumable agent-loop runtime — see [`../../16-ai-tech-stack/tracks/langgraph/`](../../16-ai-tech-stack/tracks/langgraph/) |

## Cheat sheets

- Anthropic docs (tool use, agent SDK, agent design patterns): https://docs.claude.com/
- OpenAI function calling guide: https://platform.openai.com/docs/guides/function-calling
- Also see [../../_shared/cheatsheets/](../../_shared/cheatsheets/)

## Where the theory meets production (this repo)

| Concern | Where |
|---|---|
| Durable, resumable agent runtime; cycles, checkpoints, human-in-the-loop | [`../../16-ai-tech-stack/tracks/langgraph/`](../../16-ai-tech-stack/tracks/langgraph/) |
| The model/tool abstraction layer, concrete implementation | [`../../16-ai-tech-stack/tracks/langchain/`](../../16-ai-tech-stack/tracks/langchain/) |
| A real agent harness applying these exact recovery/permission patterns | [`../../16-ai-tech-stack/tracks/claude-code/`](../../16-ai-tech-stack/tracks/claude-code/) |
| Multi-agent topologies, hand-offs, supervisors | [Module 07 — Agentic AI Systems](../../07-agentic-ai/) |
| The lethal trifecta, prompt injection, tool-access abuse | [Module 13 — AI Security](../../13-ai-security/) |
| Trajectory grading, agent eval harnesses | [Module 15 — AI Evaluation](../../15-ai-evals/) |
| Standardizing tool/data access across agents | [Module 09 — MCP](../../09-mcp/) |

## Communities

- r/LocalLLaMA and r/LangChain — active discussion of what actually breaks in agent deployments, not just demos
- LangChain / LangGraph Discord — the people building the runtime this module's theory feeds into
- Hugging Face forums (`agents` tag) — https://discuss.huggingface.co/
