# 🔗 Resources — Claude Code & the Agent SDK

## Official documentation (start here, keep open)
| Page | What's inside |
|---|---|
| https://code.claude.com/docs | The front door; the quickstart is genuinely quick |
| https://code.claude.com/docs/en/memory | CLAUDE.md, rules, auto memory — the "project memory" surface |
| https://code.claude.com/docs/en/skills | Skills: model-invoked capabilities and reference material |
| https://code.claude.com/docs/en/sub-agents | Subagents: separate context windows, separate prompts |
| https://code.claude.com/docs/en/hooks | Hook events (PreToolUse/PostToolUse/...), config, exit-code semantics |
| https://code.claude.com/docs/en/settings | settings.json, permission modes, allow/ask/deny rule syntax |
| https://code.claude.com/docs/en/mcp | MCP server configuration in Claude Code |
| https://code.claude.com/docs/en/changelog | Ships weekly; read before trusting anything above |
| https://docs.claude.com/en/docs/claude-code/sdk | Agent SDK overview, then Python / TypeScript subpages |

## Repositories worth cloning
| Repo | What's inside |
|---|---|
| https://github.com/anthropics/claude-code | The public repo: issues, examples, the release notes people actually read |
| https://github.com/anthropics/claude-agent-sdk-python | Python SDK: query loop, tools, hooks, permission callbacks |
| https://github.com/anthropics/claude-agent-sdk-typescript | TypeScript SDK, same loop, different ergonomics |
| https://github.com/anthropics/skills | Anthropic's own skills — the reference style for writing yours |
| https://github.com/anthropics/anthropic-cookbook | Agent patterns and tool-use recipes beyond Claude Code itself |
| https://github.com/modelcontextprotocol/servers | Reference MCP servers: filesystem, git, fetch — read one before writing your own |

## Community & keeping current
- r/ClaudeAI — the largest working-practices forum; filter hard for signal vs. vibes
- The changelog RSS discipline: skim weekly, adopt one new mechanism per month, not ten
- Simon Willison's blog — the best running commentary on agent safety in practice: https://simonwillison.net/

## Also in this repo
- The offline SDK reference script: [../code/agent_sdk_quickstart.py](../code/agent_sdk_quickstart.py)
- The guardrail hook pair to install and attack: [../code/example-hooks-settings.json](../code/example-hooks-settings.json)
- See also [../../../13-ai-security/](../../../13-ai-security/) for the injection deep dive and
  [../../../09-mcp/](../../../09-mcp/) for the protocol itself.
