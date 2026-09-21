# 📄 Papers & Primary Sources — Claude Code & the Agent SDK

Claude Code is a product, not a paper, so "primary sources" here means the engineering write-ups that explain
*why* it behaves the way it does, plus the research the design descends from. Read the docs alongside these,
not instead of them — and re-check the docs before you argue with either.

## Start here (Anthropic engineering, in this order)

| # | Source | Why it matters | Link |
|---|--------|----------------|------|
| 1 | **Building Effective Agents** — Anthropic Engineering | The workflows-vs-agents distinction this track leans on. Defines when a harness should decide vs. when the model should. | https://www.anthropic.com/engineering/building-effective-agents |
| 2 | **Claude Code: Best Practices for Agentic Coding** — Anthropic | The official usage write-up: CLAUDE.md, permissions, planning mode, subagents, headless runs. | https://www.anthropic.com/engineering/claude-code-best-practices |
| 3 | **Effective Context Engineering for AI Agents** — Anthropic | Why compaction, note-taking and subagent isolation exist: attention budget, not just token count. | https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents |
| 4 | **Writing Effective Tools for Agents** — Anthropic | Tool design as interface design. Pairs with the SDK custom-tools section of the notes. | https://www.anthropic.com/engineering/writing-tools-for-agents |

## The research underneath

| Paper | Year | One-line takeaway | Link |
|---|---|---|---|
| **ReAct: Synergizing Reasoning and Acting in Language Models** — Yao et al. | 2022 | The think-act-observe loop the harness implements; worth reading to see how much is now plumbing | [arXiv:2210.03629](https://arxiv.org/abs/2210.03629) |
| **SWE-bench: Can Language Models Resolve Real-World GitHub Issues?** — Jimenez et al. | 2023 | The benchmark that made "agentic coding" measurable, and its contamination caveats | [arXiv:2310.06770](https://arxiv.org/abs/2310.06770) |
| **Design Patterns for Securing LLM Agents from Prompt Injection Attacks** — Beurer-Kellner et al. | 2025 | The Action-Selector / Plan-Then-Execute / Dual-LLM patterns; the academic version of the permission story | [arXiv:2506.08837](https://arxiv.org/abs/2506.08837) |
| **Not with my name! / InjecAgent** — tool-integration attack studies | 2024 | Direct task-oriented attacks on tool-using agents; the threat model for hooks and `deny` rules | [arXiv:2403.02692](https://arxiv.org/abs/2403.02692) |

## The specification that matters

| Source | Why | Link |
|---|---|---|
| **Model Context Protocol** — spec + docs | The open standard the tool ecosystem speaks; the SDK's custom tools are an in-process MCP server | https://modelcontextprotocol.io/ |

## The blog post every practitioner should read once

- **The Lethal Trifecta** — Simon Willison (2025). Private data + untrusted content + outward communication
  in one agent = prompt injection you cannot prompt your way out of. It is the one-URL threat model briefing
  for everything in the permissions sections: https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/

## How to read a product changelog like a paper

Agent harnesses ship weekly, and the interesting signal is not the feature list — it is *what got moved from
"model judgement" to "harness enforcement"* (or back). Read Claude Code's changelog with that question in mind:
https://code.claude.com/docs/en/changelog
