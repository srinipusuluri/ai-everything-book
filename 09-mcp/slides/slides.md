---
marp: true
theme: default
paginate: true
style: |
  section h1 { color: #F59E0B; }
  section { font-size: 24px; }
---

# Model Context Protocol

### One protocol, not M times N integrations

**Module 09** · AI End-to-End Learning Track

---

## The problem: M times N integrations

- M AI apps x N tools/data sources = up to M x N bespoke integrations
- Each one hand-built, each with its own auth, schema, error conventions
- Every new tool means every AI app re-implements the same adapter
- This is the exact shape USB and LSP already solved elsewhere

<!-- speaker note: Ask the room: how many custom Slack/DB/Drive integrations has their org built for different AI tools already? Usually more than one. -->

---

## The USB-C analogy

> **MCP is like a USB-C port for AI applications.**

- One interface for tool/data builders to target
- One client implementation for AI apps to support
- Anthropic open-sourced it November 2024; now community-governed

<!-- speaker note: This is the spec's own framing, not a stretch analogy. Also compare to LSP for editors/languages. -->

---

## What MCP does NOT solve

- It standardizes the WIRE CONTRACT, not the integration work itself
- Someone still writes the adapter mapping a tool to your backend
- Someone still decides scope: what should a model be ALLOWED to do
- MCP relocates integration work to be reusable -- it doesn't remove it

<!-- speaker note: Set expectations early. MCP is not magic; it's a standard interface, same as REST didn't eliminate backend logic. -->

---

## Three primitives, three control loci

| Primitive | Who decides to invoke | Analogy |
|---|---|---|
| Tool | The MODEL, mid-conversation | POST endpoint |
| Resource | The HOST application / user | GET endpoint |
| Prompt | The USER, explicitly | Slash command / menu item |


<!-- speaker note: This table is the single most important idea in the whole module. Everything else is mechanics. -->

---

## The most common MCP design mistake

- Putting a pure data-fetch behind a Tool
- -> model must DECIDE to fetch context that should just be there
- Putting a side-effecting action behind a Resource
- -> nothing stops a host from silently loading it into every chat
- Ask: who should decide when this runs? That answer picks the primitive

<!-- speaker note: Give a concrete example: 'read this file' as a tool wastes a model turn. 'send this email' as a resource is a silent-execution bug. -->

---

## Tool descriptions are not documentation

- The model reads name + description + JSON Schema to decide when/how to call
- Vague verbs (process, handle) make the model guess
- State exact semantics: 'case-insensitive substring match', not 'searches'
- SDK builds the schema FROM your type hints -- no drift to keep in sync

<!-- speaker note: Live demo: open minimal_mcp_server.py and read search_catalog's docstring aloud as if you were the model. -->

---

## Error handling: the bug everyone writes once

- raise ToolError(...) -> result with is_error=True, model can retry
- return "error message" -> is_error=False, looks like SUCCESS
- Every client UI and the model itself reads is_error to route logic
- Resources are stricter: a miss is a protocol-level error, no in-between

<!-- speaker note: Run code/mcp_client_demo.py's failed search_catalog call live and point at is_error=True in the printed JSON. -->

---

## Architecture and wire protocol

*Host, Client, Server, and what's actually on the wire*


---

## Host, Client, Server

- HOST: the AI application a human uses (Claude Desktop, an IDE, your agent)
- CLIENT: one per server connection, maintained by the host
- SERVER: implements tools/resources/prompts against a real backend
- 5 servers connected = 5 client objects, each blind to the others
- Cross-server coordination is the HOST's job, not the protocol's

<!-- speaker note: Draw the 1:1 client-server pairing on the board. This is why agents federating many servers need their own orchestration logic. -->

---

## Transports: local vs remote

| Transport | How | Typical use |
|---|---|---|
| stdio | Client spawns server as subprocess; JSON-RPC on stdin/stdout | Local: filesystem, local DB |
| Streamable HTTP | POST + optional SSE stream | Remote, shared: SaaS server, OAuth-backed |


<!-- speaker note: Older HTTP+SSE (two endpoints) was replaced by Streamable HTTP in 2025-03-26. Flag it as deprecated if it shows up in old tutorials. -->

---

## Every message is JSON-RPC 2.0

- Request: jsonrpc, id, method, params
- Response: jsonrpc, id, and result OR error
- Notification: no id, no reply expected
- SDK pydantic models ARE this JSON, just deserialized -- not a simulation

<!-- speaker note: model_dump(mode='json') on any SDK object reproduces the wire payload exactly. Show this in mcp_client_demo.py's show() helper. -->

---

## The classic handshake (2024-11-05 through 2025-11-25)

- 1. Client sends initialize: protocolVersion, capabilities, clientInfo
- 2. Server replies with its own version, capabilities, serverInfo
- 3. Client sends notifications/initialized -- one-way, no reply
- Session now in Operation phase; tools/list, tools/call, etc. flow
- This is what virtually every deployed server speaks TODAY

<!-- speaker note: This is what mcp_client_demo.py performs and prints. The negotiated version in the demo is 2025-11-25. -->

---

## 2026-07-28: the stateless redesign

- Handshake removed entirely -- no initialize/initialized at all
- Every request carries protocolVersion + capabilities in _meta
- Discovery becomes one optional call: server/discover
- List results now cacheable via ttlMs / cacheScope fields
- Sampling and logging (client primitives) marked deprecated

<!-- speaker note: This is the CURRENT spec as of writing, but adoption is nascent. SDKs remain dual-era and still speak the classic handshake by default. -->

---

## Trust, security, and where MCP fits

*An MCP server is code you didn't write, running with privileges you granted*


---

## The trust model, stated plainly

- An MCP server is a DEPENDENCY, not just a data source
- Local stdio server = runs with YOUR os-user privileges
- Tool output is untrusted input the model can't distinguish from the user
- Vet a server like a new prod dependency: what can it READ, WRITE, TRIGGER

<!-- speaker note: Connect directly to Module 13's lethal trifecta: untrusted input + sensitive access + exfil channel. -->

---

## Named attacks from the spec's security guidance

| Attack | Core issue |
|---|---|
| Confused deputy | Static client ID + consent cookie skips user consent |
| Token passthrough | Server forwards a token not issued for it |
| SSRF | Malicious server points OAuth discovery at internal IPs |
| State handle hijacking | Stateless server doesn't bind handle to caller |
| Local server compromise | One-click install runs arbitrary code |


<!-- speaker note: These are documented, named attack classes in the spec's own security_best_practices doc -- not hypothetical. -->

---

## Independent research backs the trust framing

- 67,057 servers audited across 6 registries -- widespread hijack conditions found
- 1,899 open-source servers: 8 vuln classes, only 3 overlap traditional CWEs
- Tool poisoning: malicious instructions in a tool's OWN description
- The attack surface is what a tool claims, not just what it returns

<!-- speaker note: Cite papers/PAPERS.md arXiv:2510.16558, 2506.13538, 2603.22489. Numbers will be stale -- the categories won't. -->

---

## MCP vs. the alternatives

| Approach | Standardizes | Weak point |
|---|---|---|
| Custom tool-calling | Nothing beyond your codebase | Zero portability across hosts |
| OpenAPI / REST | HTTP API shape for humans/codegen | Not model-facing by design |
| MCP | Host <-> tool/data/prompt server | Says nothing about agent-to-agent |
| A2A | Agent <-> independent agent | Overkill inside one system you own |


<!-- speaker note: The line to land: MCP is how an agent gets a screwdriver; A2A is how it asks another agent to build the shelf. -->

---

## Governance: a server is a new vendor

- Map what it reads and what it writes/triggers BEFORE approval
- Prefer registry-listed, verified-namespace servers over random repo URLs
- Scope credentials to least privilege -- no admin key for convenience
- Log tool calls like any privileged API call for audit reconstruction

<!-- speaker note: This is the same vendor-risk lens Module 12 applies to any third-party dependency. MCP doesn't invent a new category. -->

---

## Exit check

- Run mcp_client_demo.py end to end; read every printed JSON message
- Explain why the failed search_catalog call is is_error=True, not a protocol error
- Name the primitive you'd use for a new hypothetical tool, with a control-locus reason
- State one concrete trust decision before connecting a third-party server
- Next: Module 10 -- AI Architecture, where MCP becomes the tool layer

---

## Now go build

`code/` run it · `lab/EXERCISES.md` break it · `papers/` go deeper
