#!/usr/bin/env python3
"""
agent_sdk_quickstart.py — an annotated Claude Agent SDK reference agent.

WHAT IT DOES
    Builds a read-only "repo auditor": an agent that can search and read files and call one
    custom tool, and that is denied everything else by construction rather than by instruction.

OFFLINE-SAFE BY DESIGN
    This script never crashes when it cannot run. If `claude-agent-sdk` is not installed, or
    ANTHROPIC_API_KEY is not set, it prints exactly what would have happened, how to enable it,
    and exits 0. That means you can read, run, lint and diff it with no key, no network and no
    spend. Every line of the real usage is commented.

RUN
    /Users/srinip/ai-all/.venv/bin/python 16-ai-tech-stack/tracks/claude-code/code/agent_sdk_quickstart.py

ENABLE FOR REAL (costs money)
    pip install claude-agent-sdk
    export ANTHROPIC_API_KEY=sk-ant-...

DOCS
    https://code.claude.com/docs/en/agent-sdk/overview
    https://code.claude.com/docs/en/agent-sdk/python
    https://code.claude.com/docs/en/agent-sdk/permissions
    https://code.claude.com/docs/en/agent-sdk/custom-tools
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

# Model IDs available at the time of writing. `claude-sonnet-5` is the sensible default for
# code work; `claude-haiku-4-5-20251001` is the cheap one to route subagents at.
MODEL = "claude-sonnet-5"

# The agent is pointed at this track's own folder, so the demo has something real to read
# and cannot wander into the rest of your filesystem.
WORKING_DIR = Path(__file__).resolve().parent.parent

PROMPT = (
    "Audit this learning track. List every Markdown file, then use the count_todo_markers "
    "tool on each one. Report a short table of file -> marker count, and name the single "
    "file most in need of attention. Do not modify anything."
)


# ----------------------------------------------------------------------------------------
# Preflight: decide whether we can actually run, and degrade gracefully if not.
# ----------------------------------------------------------------------------------------
def preflight() -> tuple[bool, list[str]]:
    """Return (can_run, reasons_we_cannot). Never raises."""
    reasons: list[str] = []

    try:
        import claude_agent_sdk  # noqa: F401
    except ImportError:
        reasons.append(
            "the `claude-agent-sdk` package is not installed  ->  pip install claude-agent-sdk"
        )

    # The SDK reads the key from the environment of the process that runs the agent.
    # It does NOT load .env files for you. Bedrock / Vertex / Foundry users authenticate
    # differently (CLAUDE_CODE_USE_BEDROCK=1 etc.) and are treated as runnable here.
    alt_providers = (
        "CLAUDE_CODE_USE_BEDROCK",
        "CLAUDE_CODE_USE_VERTEX",
        "CLAUDE_CODE_USE_FOUNDRY",
        "CLAUDE_CODE_USE_ANTHROPIC_AWS",
    )
    if not os.environ.get("ANTHROPIC_API_KEY") and not any(
        os.environ.get(v) for v in alt_providers
    ):
        reasons.append(
            "ANTHROPIC_API_KEY is not set  ->  export ANTHROPIC_API_KEY=sk-ant-..."
        )

    return (not reasons, reasons)


def explain_offline(reasons: list[str]) -> None:
    """Print what this script would do, then exit 0. This is the no-key path."""
    print("=" * 84)
    print("Claude Agent SDK quickstart — DRY RUN (nothing was sent to any API)")
    print("=" * 84)
    print("\nNot running, because:")
    for r in reasons:
        print(f"  - {r}")

    print(
        f"""
WHAT THIS SCRIPT WOULD DO
-------------------------
  1. Define ONE custom tool, `count_todo_markers`, with the @tool decorator. A custom tool is
     just an MCP tool served in-process: name, description, input schema, async handler.
  2. Wrap it in an in-process MCP server via create_sdk_mcp_server(name="audit", ...). The
     server key becomes the tool's namespace, so Claude calls it `mcp__audit__count_todo_markers`.
  3. Build ClaudeAgentOptions that lock the agent down:
         tools             = ["Read", "Grep", "Glob"]   only these built-ins exist at all
         allowed_tools     = those three + the custom tool     -> run with no prompt
         disallowed_tools  = ["Bash", "Write", "Edit", "WebFetch", "WebSearch"]
                                                              -> definitions removed entirely
         permission_mode   = "dontAsk"   anything else that would prompt is DENIED, not asked
         setting_sources   = []          ignore ~/.claude and ./.claude -- hermetic run
         cwd               = {WORKING_DIR}
         max_turns         = 30          hard stop on runaway loops
         max_budget_usd    = 1.00        client-side spend circuit breaker
  4. Register a PreToolUse hook that denies any Read of a path containing `.env` or `secrets`.
     Belt and braces: the deny is enforced even though Read is on the allow list.
  5. Stream the agent loop with `async for message in query(...)`, printing Claude's reasoning
     and each tool call as they arrive.
  6. Read the terminating ResultMessage for subtype, turn count, total_cost_usd and
     permission_denials -- the last one is the highest-signal line in any agent log.

WHY THE SDK RATHER THAN THE MESSAGES API
----------------------------------------
  The tool loop, Read/Grep/Glob, context compaction, permission evaluation, subagents and cost
  accounting are already written. On the Messages API you would own all of it. Use the raw API
  when the job is one bounded call; use the SDK when the job looks like work on a real machine.

WHY NOT LANGGRAPH
-----------------
  LangGraph gives you an explicit graph: fixed stages, conditional edges, checkpoints, human
  approval at defined points. Reach for it when the control flow is a requirement you must be
  able to audit. Here the control flow IS the model's judgement, which is the SDK's home turf.
  See ../../langgraph/ and notes/02-agent-sdk-and-building-on-it.md for the full table.

Exiting 0. Nothing was sent anywhere.
"""
    )


# ----------------------------------------------------------------------------------------
# The real agent. Only imported and executed when preflight passes.
# ----------------------------------------------------------------------------------------
async def run_agent() -> int:
    # Imported here, not at module scope, so the file stays importable without the SDK.
    from claude_agent_sdk import (            # the package is `claude-agent-sdk` (renamed from
        AssistantMessage,                     # `claude-code-sdk`); imports use underscores
        ClaudeAgentOptions,                   # the options dataclass (was ClaudeCodeOptions)
        HookMatcher,                          # binds a matcher pattern to hook callbacks
        ResultMessage,                        # the terminal message: cost, usage, subtype
        create_sdk_mcp_server,                # wraps tools into an in-process MCP server
        query,                                # the agent loop -> AsyncIterator[Message]
        tool,                                 # decorator that turns a coroutine into a tool
    )

    # --- 1. A custom tool ----------------------------------------------------------------
    # @tool takes (name, description, input_schema). The DESCRIPTION is a prompt: it is the
    # only thing Claude reads when deciding whether to call this. Write it like one.
    # The Python schema is a dict of {param: type}; every key is REQUIRED. To make a parameter
    # optional, leave it out of the schema, mention it in the description, and use args.get().
    @tool(
        "count_todo_markers",
        "Count TODO, FIXME, XXX and HACK markers in a single UTF-8 text file. "
        "Returns the counts and the total. Use it to rank files by how much unfinished "
        "work they contain.",
        {"file_path": str},
    )
    async def count_todo_markers(args: dict[str, Any]) -> dict[str, Any]:
        # The handler is an ordinary async function. It receives validated arguments.
        path = Path(args["file_path"])

        # Guard rail inside the tool itself: never read outside the working directory, no
        # matter what Claude passes. A custom tool runs in YOUR process with YOUR privileges,
        # so its own input validation is part of the security boundary, not an afterthought.
        try:
            path = path.resolve()
            path.relative_to(WORKING_DIR)
        except (ValueError, OSError):
            # `isError: True` lets you compose the message Claude reads instead of leaking a
            # raw traceback, and signals a tool failure it can react to.
            return {
                "content": [{"type": "text", "text": f"Refused: {path} is outside the audit root."}],
                "isError": True,
            }

        if not path.is_file():
            return {
                "content": [{"type": "text", "text": f"Not a file: {path}"}],
                "isError": True,
            }

        text = path.read_text(encoding="utf-8", errors="replace")
        counts = {m: text.count(m) for m in ("TODO", "FIXME", "XXX", "HACK")}
        total = sum(counts.values())

        # A handler must return `content`: a list of blocks typed text/image/audio/resource.
        # `structuredContent` is the optional machine-readable twin -- same facts, parseable.
        return {
            "content": [
                {"type": "text", "text": f"{path.name}: {total} markers  {counts}"}
            ],
            "structuredContent": {"file": str(path), "total": total, **counts},
        }

    # --- 2. Wrap it in an in-process MCP server ------------------------------------------
    # No subprocess, no socket. The `name` here is the server's own name; the KEY you use in
    # ClaudeAgentOptions.mcp_servers below is what forms `mcp__<key>__<tool>`. Rename that key
    # and every allowed_tools entry that mentions it breaks silently.
    audit_server = create_sdk_mcp_server(
        name="audit",
        version="1.0.0",
        tools=[count_todo_markers],
    )

    # --- 3. A PreToolUse hook: the only gate that catches EVERY call ----------------------
    # Auto-approved tools never reach a can_use_tool callback -- a bare allowed_tools entry
    # approves the tool before the callback is consulted. A PreToolUse hook runs first, before
    # deny rules, allow rules and the permission mode, so it is the right place for a rule
    # that must hold unconditionally.
    async def deny_secret_reads(
        input_data: dict[str, Any],
        tool_use_id: str | None,
        context: Any,
    ) -> dict[str, Any]:
        # The event JSON carries tool_name, tool_input and tool_use_id. For Read/Write/Edit,
        # `file_path` has already been expanded to an absolute path, so relative-path and `~`
        # tricks cannot dodge this check.
        target = str(input_data.get("tool_input", {}).get("file_path", "")).replace("\\", "/")
        if any(part in target.lower() for part in (".env", "secret", "credential", "id_rsa")):
            # PreToolUse answers inside hookSpecificOutput (NOT the top-level `decision` field,
            # which is deprecated for this event). permissionDecision is allow/deny/ask/defer;
            # on deny, permissionDecisionReason is shown to Claude so it can adapt.
            return {
                "hookSpecificOutput": {
                    "hookEventName": input_data["hook_event_name"],
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "Reading credential-like paths is blocked by policy.",
                }
            }
        return {}  # an empty dict means "no opinion" -- the normal flow continues

    # --- 4. Options: say no by construction ----------------------------------------------
    options = ClaudeAgentOptions(
        model=MODEL,
        cwd=str(WORKING_DIR),                     # the agent's filesystem root for this run

        # `tools` sets which BUILT-IN tools exist at all. Everything not listed is absent.
        tools=["Read", "Grep", "Glob"],

        # `allowed_tools` pre-approves calls so they run without prompting. MCP tools are
        # named mcp__<server-key>__<tool-name>; `mcp__audit__*` would allow the whole server.
        allowed_tools=["Read", "Grep", "Glob", "mcp__audit__count_todo_markers"],

        # A bare name in `disallowed_tools` removes the tool DEFINITION from the request:
        # Claude never sees it and cannot try. Denies win in every mode, bypassPermissions
        # included. Belt and braces alongside the `tools` list above.
        disallowed_tools=["Bash", "Write", "Edit", "NotebookEdit", "WebFetch", "WebSearch"],

        # "dontAsk": anything that would have prompted is DENIED instead. Paired with an
        # explicit allow list this is the documented recipe for a locked-down unattended agent.
        permission_mode="dontAsk",

        # [] means: load NO filesystem settings -- not ~/.claude/settings.json, not the repo's
        # .claude/settings.json, not settings.local.json. A hermetic run that a teammate's hook
        # or a cloned repo's config cannot alter. NOTE: this also means no CLAUDE.md; include
        # "project" in the list if you want the repo's instructions loaded.
        setting_sources=[],

        mcp_servers={"audit": audit_server},      # the key here forms the tool namespace
        hooks={"PreToolUse": [HookMatcher(matcher="Read", hooks=[deny_secret_reads])]},

        system_prompt=(
            "You are a read-only repository auditor. You never modify files. "
            "You report findings as a short markdown table and stop."
        ),

        max_turns=30,                             # hard stop on a runaway loop
        max_budget_usd=1.00,                      # client-side spend circuit breaker
    )

    print(f"Running the auditor over {WORKING_DIR} on {MODEL}...\n")

    # --- 5. The agent loop ---------------------------------------------------------------
    # query() opens a fresh session and returns an AsyncIterator[Message]. Each iteration is
    # Claude thinking, calling a tool, observing the result, or finishing. For a multi-turn
    # conversation that keeps one context, use ClaudeSDKClient instead.
    result: Any = None
    async for message in query(prompt=PROMPT, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):            # a TextBlock: Claude's reasoning/output
                    print(block.text)
                elif hasattr(block, "name"):          # a ToolUseBlock: a tool being called
                    print(f"  [tool] {block.name}")
        elif isinstance(message, ResultMessage):      # always the last message
            result = message

    # --- 6. Read the result ---------------------------------------------------------------
    if result is None:
        print("\nNo ResultMessage received — the stream ended early.", file=sys.stderr)
        return 1

    print("\n" + "-" * 84)
    # subtype: success | error_during_execution | error_max_turns | error_max_budget_usd | ...
    print(f"subtype        : {result.subtype}")
    print(f"turns          : {result.num_turns}")
    # total_cost_usd covers the whole run. Careful with `usage`: it is the MAIN LOOP ONLY and
    # excludes subagents. `model_usage` is the per-model breakdown that includes everything.
    print(f"cost (USD)     : {result.total_cost_usd}")
    # The highest-signal log line you have: what your policy actually stopped.
    print(f"denials        : {result.permission_denials}")
    print("-" * 84)

    return 0 if result.subtype == "success" else 1


def main() -> int:
    can_run, reasons = preflight()
    if not can_run:
        explain_offline(reasons)
        return 0  # a dry run is a successful run
    try:
        return asyncio.run(run_agent())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except Exception as exc:  # never dump a traceback at a reader of this file
        print(f"\nAgent run failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        print("See https://code.claude.com/docs/en/agent-sdk/troubleshooting", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
