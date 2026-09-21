---
marp: true
theme: default
paginate: true
style: |
  section h1 { color: #D97757; }
  section { font-size: 24px; }
---

# Claude Code and the Agent SDK

### Using the harness well, then building on it

**Module 16.7** · AI End-to-End Learning Track

---

## The mental model

- A harness around a loop: read, think, call a tool, observe, repeat
- The tools ARE the agency -- file edits, Bash, search, web fetch
- Interactive mode for you working alongside it; print mode for automation
- Two halves to this track: using Claude Code well, then building on the SDK

---

## Context is the budget you are actually spending

- Every file read, every tool result, every turn consumes the same window
- CLAUDE.md is project memory -- loaded every session, so it is not free either
- The rule that matters: keep CLAUDE.md under 200 lines
- Important rules get lost in noise long before you hit a hard limit

<!-- speaker note: This is the same lesson as prompt caching in Module 04 -- budget attention deliberately. -->

---

## Permission modes

| Mode | Behaviour |
|---|---|
| default (Manual) | prompts on first use of each tool |
| acceptEdits | auto-accepts file edits and common fs commands |
| plan | read-only; does not edit your source |
| auto | a classifier model approves or blocks in the background |
| bypassPermissions | skips prompts except what no mode auto-approves |


<!-- speaker note: Cycle modes with Shift+Tab. Start conservative; loosen deliberately, not by habit. -->

---

## Permission rules: deny beats allow, always

> **Evaluation is deny -> ask -> allow, first match wins. Specificity does not change the order.**

- A broad Bash(aws *) deny beats a narrow Bash(aws s3 ls) allow
- Write(path) rules are silently NEVER consulted -- use Edit(...) instead
- Path anchors: //abs, ~/home, /anchored-at-settings-source, ./relative

<!-- speaker note: The Write(path) gotcha is a real, documented trap. Flag it explicitly. -->

---

## The lethal trifecta

- Reads untrusted content + holds sensitive data/credentials + can act externally
- A .env in the repo, a WebFetch tool, and Bash access -- all three at once
- A README, a GitHub issue, a scraped page can contain text addressed to the MODEL
- The model cannot reliably tell data-it-reads from instructions-it-was-given

<!-- speaker note: This is Module 13 material landing inside a tool you use every day. Make the connection explicit. -->

---

## What you actually do about it

- Deny the secrets: Read(./.env), Read(~/.ssh/**) in permissions.deny -- a wall, not a request
- Deny the exfiltration path: outbound network commands, restrict WebFetch(domain:...)
- Command-text rules are a speed bump: Bash(curl *) misses sh -c 'curl ...'
- For a real boundary: sandboxing, a container, or a PreToolUse hook that parses the command
- Trust verification is OFF by default in non-interactive (-p) runs -- know this

<!-- speaker note: Full attack taxonomy and defenses live in ../../../13-ai-security/. -->

---

## Skills, subagents, hooks: pick the right mechanism

- Skill: a reusable PROCEDURE you invoke by name or trigger -- packaged instructions
- Subagent: a separate context window for a bounded task -- isolation, not just delegation
- Hook: code that runs on an EVENT (PreToolUse, PostToolUse) -- deterministic, not model-decided
- Guardrails go in hooks and permission rules. Guidance goes in CLAUDE.md. Procedures go in skills

---

## MCP, plugins, and integrations

- MCP servers connect tools and data -- treat them as CODE YOU ARE INSTALLING
- Project-scoped .mcp.json servers load without a prompt in -p, SDK, and cloud sessions
- Plugins and marketplaces package skills/agents/hooks/MCP servers together
- IDE integrations and the GitHub Action extend the same harness, not a different one

<!-- speaker note: Full protocol detail lives in ../../../09-mcp/. -->

---

## Habits of people who get good output

| Anti-pattern | Fix |
|---|---|
| The kitchen-sink session | /clear between unrelated tasks |
| Correcting over and over | after 2 corrections, /clear and rewrite the prompt |
| The over-specified CLAUDE.md | prune ruthlessly; convert rules to hooks |
| The trust-then-verify gap | never ship what you can't verify |
| The infinite exploration | scope it, or delegate to a subagent |


<!-- speaker note: Also: bypassPermissions as a lifestyle turns off the harness layer entirely, including writes to .git. And a subagent is not free -- it has its own input and output tokens. -->

---

## Delegate, don't dictate

> **'The checkout flow breaks for expired cards, investigate and fix' beats a file-by-file script.**

- Give it a check it can run; ask for the evidence, not the claim
- Point at existing patterns instead of writing the spec from scratch
- Let it interview you when the spec is fuzzy
- You are hiring a colleague, not writing a macro

---

## The Agent SDK

*Claude Code as a library you build on*


---

## What the SDK gives you over raw API calls

- The agent loop, included -- you do not rebuild read/think/act/observe
- ~30 built-in tools plus your own via an in-process MCP server
- Permissions: modes, allow/ask/deny, hooks, a can_use_tool callback
- Automatic context compaction and subagent isolation
- Python and TypeScript packages; the minimum viable agent is a few lines

---

## Custom tools and programmatic permissions

- Define a tool as an in-process MCP server -- no separate process needed
- can_use_tool lets your code approve or deny each call at runtime
- Streaming, sessions, and structured output all first-class
- code/agent_sdk_quickstart.py is a real reference, guarded to exit 0 with no key

---

## SDK vs Messages API vs LangGraph

| Dimension | Messages API | Agent SDK | LangGraph |
|---|---|---|---|
| Control flow | whatever you write | model-driven, turn by turn | explicit graph |
| Determinism | total | low -- Claude decides next step | high -- graph decides |
| Filesystem/shell | none unless you build it | first-class, permission-gated | none unless you build it |
| Best at | narrow, high-volume calls | software/ops on a real filesystem | auditable business workflows |


<!-- speaker note: They compose: a LangGraph node can call an Agent SDK agent for the 'go fix the repo' step while the graph owns the surrounding workflow. -->

---

## The failure mode to avoid

> **Using an agentic loop where a state machine was the requirement.**

- If a compliance reviewer asks 'which steps ran, who approved step 4' --
- a model choosing its next action turn by turn is the wrong architecture
- The inverse failure is just as common: a 40-node graph to 'fix the type errors'

<!-- speaker note: This single distinction resolves most SDK-vs-LangGraph debates in five minutes. -->

---

## Choose deliberately

- Messages API: one bounded call -- classify, extract, summarize, rewrite
- Agent SDK: read a repo, edit files, run a build, triage logs, review a PR
- LangGraph: fixed stages, conditional routing, approval gates, audit trails
- Don't spawn an agent harness to call one function

---

## Exit check

- Write an exemplary CLAUDE.md under 200 lines, annotated with why each line earns its place
- Configure a hook that blocks edits to a protected path
- Explain the lethal trifecta and name three concrete mitigations
- Pick correctly between Messages API, Agent SDK, and LangGraph for three scenarios
- This closes the tech-stack module -- return to the top-level README

---

## Now go build

`code/` run it · `lab/EXERCISES.md` break it · `papers/` go deeper
