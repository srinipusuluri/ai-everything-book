# 📄 Papers & Primary Sources — Agentic AI Systems

Read the first two before anything else — they're not academic papers but they are the two most
consequential primary sources in this space, and they disagree with each other in an instructive way.

## Read these two first (and hold them against each other)

| # | Source | Why it matters | Link |
|---|-------|----------------|------|
| 1 | **How we built our multi-agent research system** — Anthropic Engineering | The primary source for the 15x token-cost figure used throughout this module, and an honest account of when a lead-agent/sub-agent supervisor topology earned its cost. Read the section on why multi-agent won for open-ended research and lost for narrower tasks. | https://www.anthropic.com/engineering/multi-agent-research-system |
| 2 | **Don't Build Multi-Agents** — Walden Yan, Cognition | The sharpest published counter-argument: context isolation is oversold, hand-off summarization loses information structurally, and most tasks are better served by one long-context agent. Read this right after #1 — the two sources are responding to the same trade-off and reaching different defaults for different task shapes. | https://cognition.ai/blog/dont-build-multi-agents |

## Multi-agent frameworks and architectures (primary sources)

| Paper | Year | One-line takeaway | Link |
|---|---|---|---|
| **AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation** — Wu et al. | 2023 | Conversable agents as the unit of composition; customizable roles, human-in-the-loop as a first-class agent type | [arXiv:2308.08155](https://arxiv.org/abs/2308.08155) |
| **MetaGPT: Meta Programming for a Multi-Agent Collaborative Framework** — Hong et al. | 2023 | Encodes Standard Operating Procedures into agent roles to fight "cascading hallucination" from naively chaining LLMs — the pipeline topology, formalized for software engineering | [arXiv:2308.00352](https://arxiv.org/abs/2308.00352) |
| **CAMEL: Communicative Agents for "Mind" Exploration of Large Language Model Society** — Li et al. | 2023 | Role-playing agents that negotiate a task via structured dialogue with minimal human steering — an early, clean statement of peer-to-peer coordination | [arXiv:2303.17760](https://arxiv.org/abs/2303.17760) |
| **Generative Agents: Interactive Simulacra of Human Behavior** — Park et al. | 2023 | Memory, reflection, and planning loops for agents in a shared simulated environment; the ancestor of most "agent society" and long-horizon memory designs | [arXiv:2304.03442](https://arxiv.org/abs/2304.03442) |
| **Improving Factuality and Reasoning in Language Models through Multiagent Debate** — Du et al. | 2023 | The empirical case for the debate/vote topology: independent models arguing over multiple rounds measurably reduce factual errors versus a single model | [arXiv:2305.14325](https://arxiv.org/abs/2305.14325) |

## Evaluation (connects to Module 15)

| Paper | Year | One-line takeaway | Link |
|---|---|---|---|
| **AgentBench: Evaluating LLMs as Agents** — Liu et al. | 2023 | Multi-environment benchmark exposing how much of "agent" performance is really long-horizon reasoning and instruction-following, not single-turn capability — read this before trusting any single-number agent leaderboard | [arXiv:2308.03688](https://arxiv.org/abs/2308.03688) |

## Standards and protocols

| Source | What it is | Link |
|---|---|---|
| **Announcing the Agent2Agent Protocol (A2A)** — Google Developers Blog | The original announcement: Agent Cards, Tasks, and the transport for agent-to-agent delegation across vendors | https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/ |
| **A2A Protocol Specification** | The living technical spec, now under Linux Foundation stewardship | https://a2a-protocol.org/latest/specification/ |
| **Model Context Protocol** | The agent-to-tool/data standard this module contrasts A2A against — full coverage in [Module 09](../../09-mcp/) | https://modelcontextprotocol.io/ |
| **LangGraph — Multi-agent concepts** | How this module's five topologies compile down to subgraphs and hand-offs in one popular framework | https://langchain-ai.github.io/langgraph/concepts/multi_agent/ |

## How to read an agentic-systems paper (30 minutes, 3 passes)

1. **Pass 1 (5 min):** what's the topology (even if the paper doesn't name it that way), and what's the
   claimed win over a single agent?
2. **Pass 2 (15 min):** look for the cost accounting. Does the paper report token/API-call counts against
   its single-agent baseline, or only task success? A paper that only reports success without cost is
   telling you half the trade-off from notes/02 section 1.
3. **Pass 3 (10 min):** find the failure analysis. Almost every multi-agent paper has a "limitations"
   paragraph describing one of the five coordination failure modes in notes/02 section 3 without naming it
   that way — that paragraph is usually the most useful one in the paper.

Keep a one-paragraph note per paper, specifically on which of the five topologies (notes/01 section 2) it
actually implements — paper authors rarely use this module's vocabulary, and mapping their architecture
onto it is the fastest way to tell if a "novel framework" is actually a supervisor with new branding.
