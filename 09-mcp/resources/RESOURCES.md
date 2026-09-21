# 🔗 Resources — Model Context Protocol

## Official documentation
| Resource | Why | Link |
|---|---|---|
| **MCP documentation home** | Canonical docs: introduction, architecture, build-server/build-client guides | https://modelcontextprotocol.io/ |
| **Specification (latest)** | The normative spec — data layer, transport layer, authorization | https://modelcontextprotocol.io/specification/latest |
| **MCP Blog** | Where spec revisions, roadmap posts, and adoption/ecosystem updates actually get announced | https://blog.modelcontextprotocol.io/ |
| **Build servers guide** | Step-by-step server construction per language, current spec revision | https://modelcontextprotocol.io/docs/2026-07-28/develop/build-server |
| **Build clients guide** | The client-side equivalent — what `code/mcp_client_demo.py` in this module is a minimal version of | https://modelcontextprotocol.io/docs/2026-07-28/develop/build-client |

## SDK repositories
| Repo | What's inside | Link |
|---|---|---|
| **python-sdk** | The `mcp` PyPI package used by this module's code | https://github.com/modelcontextprotocol/python-sdk |
| **typescript-sdk** | The Tier-1 TS/JS SDK; Zod-native schemas | https://github.com/modelcontextprotocol/typescript-sdk |
| **servers** (reference implementations) | Official filesystem/fetch/memory/git servers — the best "read real code" starting point | https://github.com/modelcontextprotocol/servers |
| **inspector** | Interactive dev tool for testing a server without writing a client | https://github.com/modelcontextprotocol/inspector |
| **modelcontextprotocol/modelcontextprotocol** | The spec's own source repo — changelogs, SEPs (spec enhancement proposals), governance docs | https://github.com/modelcontextprotocol/modelcontextprotocol |

## Server discovery
| Resource | What it gives you | Link |
|---|---|---|
| **Official MCP Registry** | The authoritative, verified-namespace index of publicly available servers | https://registry.modelcontextprotocol.io/ |
| **Registry API docs** | REST API for programmatic server discovery — useful if you're building a client that federates many servers | https://registry.modelcontextprotocol.io/docs |

## Client/host support (where you'll actually use this)
- Claude (Desktop, Code, API Connectors) — https://claude.com/docs/connectors/building
- ChatGPT / OpenAI API MCP support — https://developers.openai.com/api/docs/mcp/
- VS Code MCP servers — https://code.visualstudio.com/docs/copilot/chat/mcp-servers
- Cursor MCP support — https://cursor.com/docs/context/mcp

## Cheat sheets
- JSON-RPC 2.0 spec (the wire format underneath everything) — https://www.jsonrpc.org/specification
- Also see [../../_shared/cheatsheets/](../../_shared/cheatsheets/)

## Communities
- MCP GitHub Discussions — the working-group/SEP conversations that shape the spec: https://github.com/modelcontextprotocol/modelcontextprotocol/discussions
- Anthropic Developer Discord — has an active MCP channel for server-building questions
- r/mcp and r/ClaudeAI — informal but active for "why isn't my server showing up" debugging

## Where this connects back
- [../../06-ai-agents/resources/RESOURCES.md](../../06-ai-agents/resources/RESOURCES.md) — tool-calling and
  agent frameworks that consume MCP servers as one of their tool sources.
- [../../13-ai-security/](../../13-ai-security/) — OWASP Top 10 for LLM Applications, for the general
  prompt-injection background this module's security notes assume.
- [../../16-ai-tech-stack/tracks/claude-code/resources/RESOURCES.md](../../16-ai-tech-stack/tracks/claude-code/resources/RESOURCES.md) —
  the practical side: configuring MCP servers inside Claude Code day to day.
