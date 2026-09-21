# `example-hooks-settings.json` — what every entry does, and why

This file is a working `.claude/settings.json`. It does three genuinely useful things:

1. **Blocks edits to protected paths** — deterministically, not by asking nicely.
2. **Blocks `git push --force` on protected branches** before the command runs.
3. **Runs the formatter after every write**, so Claude never hands you unformatted code.

Plus a `SessionStart` line that prints the current branch into context, because the single most common
"why did it edit the wrong thing" is a session on a branch you forgot you were on.

## Install

```bash
cp example-hooks-settings.json <your-repo>/.claude/settings.json   # merge if one exists
mkdir -p <your-repo>/.claude/hooks
# then create the three scripts below and: chmod +x .claude/hooks/*.sh
```

Verify with `/hooks` in a session, and `/doctor` if something doesn't fire. `settings.json` is read at session
start — restart after editing it. Hooks in a project settings file require you to have trusted the workspace.

> **Read the hooks you install.** A hook is a shell command Claude Code runs on your machine with your
> credentials, on someone else's trigger. Treat a `settings.json` arriving in a pull request exactly as you would
> treat a new `Makefile` target: read it before you run it. The docs carry the same disclaimer.

---

## The structure: three levels of nesting

Every hook config is the same shape, and if you can recite it you can write any hook:

```
hooks
└── <HookEvent>            e.g. "PreToolUse"        — the lifecycle point
    └── [ matcher group ]  e.g. {"matcher": "Edit"} — which occurrences it fires on
        └── hooks: [ ... ] the handlers that run    — command / http / mcp_tool / prompt / agent
```

All matching handlers run **in parallel**. A handler defined identically in two settings files runs once.

---

## Entry by entry

### 1. `PreToolUse` on `Write|Edit|NotebookEdit` → `protect-paths.sh`

**Why `PreToolUse`:** it is the only tool event that can *stop* a call. `PostToolUse` fires after the damage.

**Why this matcher:** a matcher made only of letters, digits, `_`, `-`, spaces, `,` and `|` is treated as a list of
**exact** tool names. `Edit|Write` matches those two tools and nothing else. Anything else in the string makes it an
**unanchored JavaScript regex** — which is why `Edit.*` would also match `NotebookEdit`. Here we list all three
explicitly, which is clearer than relying on a regex to be sloppy in a convenient direction.

**Why `NotebookEdit` is in the list:** `Read` deny rules cover Edit and Write on the same path but the docs note
NotebookEdit isn't covered, so a notebook is a real bypass. Name it.

**Why exec form** (`"args": []`): a command hook runs in exec form whenever `args` is present — `command` is
resolved as an executable and spawned directly, no shell, so `${CLAUDE_PROJECT_DIR}` is substituted as one literal
argument. In shell form a path containing a space would be re-tokenized. The docs recommend exec form for any hook
referencing a path placeholder. (On Windows, exec form needs a real executable — `.cmd`/`.bat` shims won't spawn.)

**Why `${CLAUDE_PROJECT_DIR}`:** it is the project root where the session started, regardless of Claude's current
directory. It even stays put when Claude enters a worktree — the worktree path arrives as `cwd` in the hook's JSON
input instead.

The script:

```bash
#!/usr/bin/env bash
# .claude/hooks/protect-paths.sh
# PreToolUse on Write|Edit|NotebookEdit. Exit 2 = block.
set -euo pipefail
input=$(cat)                                              # event JSON arrives on stdin
file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // ""')
file_path="${file_path//\\//}"                            # normalize Windows separators

case "$file_path" in
  */.github/workflows/*|*/migrations/*|*/.claude/settings.json|*.lock|*/go.sum|*/uv.lock)
    echo "Blocked: $file_path is protected. Ask a human to change it." >&2
    exit 2
    ;;
esac
exit 0
```

**Why exit 2 and not exit 1.** On events that can block, exit 2 blocks — and your **stderr** becomes the reason
Claude reads, so it can adapt instead of retrying blindly. Exit 1 is a *non-blocking* error: the transcript shows a
hook-error notice and **the tool call proceeds anyway.** This is the opposite of Unix instinct and it is the single
most common hook bug. Exit 2 also beats JSON: even a `permissionDecision: "allow"` on stdout cannot override it.

**Why `tool_input.file_path` is safe to match on:** for `Write`, `Edit` and `Read`, Claude Code expands `~` and
relative paths *before* hooks run, so the path is always absolute. A hook can't be dodged with `./foo/../.env`.
The `${file_path//\\//}` line handles Windows, where the path arrives with backslashes even under Git Bash — a
`/migrations/` check would silently never match otherwise, and the call would sail through.

**The structured-JSON alternative.** Instead of exit 2 you can exit 0 and print:

```json
{ "hookSpecificOutput": { "hookEventName": "PreToolUse",
    "permissionDecision": "deny", "permissionDecisionReason": "Protected path" } }
```

`permissionDecision` takes `allow`, `deny`, `ask`, or `defer`; when several `PreToolUse` hooks disagree, precedence
is `deny > defer > ask > allow`. Use JSON when you want `ask` (send it to the human) or `updatedInput` (rewrite the
call). Use exit 2 when the answer is simply no — it's three lines of bash instead of a JSON template.

### 2. `PreToolUse` on `Bash` with `if: "Bash(git push *)"` → `block-force-push.sh`

**Why the `if` field:** the `matcher` filters on the tool *name* only, so `"Bash"` fires on every shell command.
`if` takes exactly one **permission-rule** pattern and matches the tool name *and arguments together*, so the
script only runs for pushes. That keeps a hook off the hot path of every `ls`.

Behaviour worth knowing: leading `VAR=value` assignments are stripped before matching; each subcommand of
`a && b` is checked; commands inside `$()` and backticks are checked. And when Claude Code can't tell what a command
expands to (`$TOOL git push`), it runs your hook anyway — `if` is deliberately **fail-open on ambiguity**, which is
why the docs say to use the permission system, not `if`, for a hard allow/deny. There is no `&&`/`||` in `if`:
one rule per handler, add another handler for another condition.

```bash
#!/usr/bin/env bash
# .claude/hooks/block-force-push.sh
set -euo pipefail
input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""')
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")

if printf '%s' "$cmd" | grep -Eq -- '--force(-with-lease)?|(^| )-f( |$)'; then
  case "$branch" in
    main|master|release/*)
      echo "Blocked: force-push to '$branch'. Push to a feature branch and open a PR." >&2
      exit 2
      ;;
  esac
fi
exit 0
```

**Be honest about the limit.** This inspects the command text Claude wrote. It does not stop
`/usr/bin/git push --force` or `sh -c 'git push -f'` — the docs say the same about `Bash(...)` permission rules.
Command-text inspection is a guardrail against Claude doing something dumb, **not** a security boundary against an
adversary. For a real boundary use [sandboxing](https://code.claude.com/docs/en/sandboxing), a container, or a
server-side branch protection rule. Defence in depth: this hook plus GitHub branch protection.

### 3. `PostToolUse` on `Write|Edit` → `format-after-write.sh`

**Why `PostToolUse`:** the file exists now, so we can act on it. The input carries both `tool_input` (arguments)
and `tool_response` (result). Formatting is the canonical hook: it must happen *every* time, and it needs no
reasoning — the docs' own rule is that deterministic, no-thinking actions are hooks, not instructions.

```bash
#!/usr/bin/env bash
# .claude/hooks/format-after-write.sh
set -euo pipefail
input=$(cat)
file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // ""')
file_path="${file_path//\\//}"
[ -f "$file_path" ] || exit 0

case "$file_path" in
  *.py)              command -v ruff >/dev/null && ruff format -q "$file_path" ;;
  *.ts|*.tsx|*.js|*.jsx|*.json|*.md)
                     command -v prettier >/dev/null && prettier --write --log-level warn "$file_path" ;;
  *.go)              command -v gofmt >/dev/null && gofmt -w "$file_path" ;;
  *.rs)              command -v rustfmt >/dev/null && rustfmt --edition 2021 "$file_path" ;;
esac
exit 0
```

**Always exit 0 from a formatter.** A `PostToolUse` hook that exits 2 feeds a blocking error back to Claude, which
will then try to "fix" it — and a missing `prettier` is not something Claude can fix. The `command -v` guards keep a
teammate without your toolchain from getting an error on every edit. The `timeout: 60` is generous because a cold
`prettier` on a large file is slow; the default for command hooks is 600 seconds, which is far too long to sit
behind a formatter.

**To surface a warning to Claude instead of blocking**, print JSON with `additionalContext` (or use
`systemMessage`). Plain stderr from a hook that exits 0 goes to the debug log only — Claude never sees it.

### 4. `SessionStart` with matcher `startup|resume`

The matcher on `SessionStart` filters **how the session started** — `startup`, `resume`, `clear`, `compact` are the
documented values. This one fires on a new or resumed session but not after a `/clear`, where you already know
where you are.

`SessionStart` is one of only four events (with `UserPromptSubmit`, `UserPromptExpansion` and `PostModelSwitch`)
where **plain stdout is added to Claude's context**. That makes it the cheap way to inject dynamic session facts:
current branch, deploy target, whether the local stack is up, today's on-call. Keep it to a line or two — it is
paid for on every request afterwards.

This entry is in shell form (no `args`) because it uses a pipeline and command substitution, which need a shell.
That's the rule: **exec form for scripts and path placeholders, shell form when you need shell features.**

---

## The permissions block: why both layers

The `permissions` object at the top isn't decoration. Hooks and permission rules do different jobs:

| | `permissions.deny` | `PreToolUse` hook |
|---|---|---|
| Evaluated | before hooks in the rule chain; deny wins over ask and allow | first in the flow; can deny outright |
| Expressiveness | path/command patterns | arbitrary code — branch state, file contents, time of day, your API |
| Covers Bash file commands | yes: `Read` deny also covers `cat`, `head`, `sed`, and `>` redirect targets | only what you inspect |
| Cost to maintain | a line of JSON | a script you own and must keep working |
| Fails how | closed | if the script is missing or non-executable, it's a **non-blocking** error — the action proceeds |

So: **static, expressible-as-a-pattern → permission rule. Conditional, stateful, needs logic → hook.** Use both for
anything that matters, because the hook can break and the rule cannot.

Note also `"ask": ["Bash(git push *)"]` sitting next to the force-push hook. Evaluation order is
deny → ask → allow, first match wins, and specificity does not change the order — a broad deny will swallow a
narrow allow, so don't try to write allowlist exceptions inside a deny.

---

## Debugging

| Symptom | Check |
|---|---|
| Hook never fires | `/hooks` shows what's registered; `settings.json` is read at **session start** — restart |
| Fires but doesn't block | you exited 1, not 2. Only exit 2 blocks |
| "hook error" in the transcript | script missing, not `chmod +x`, or stdout that looks like broken JSON |
| Fires on the wrong tool | your matcher contained a non-word character and became an unanchored regex |
| Works on macOS, not Windows | backslash separators in `file_path`; normalize before comparing |
| Everything is weird | `claude --debug` or `/doctor`; `--safe-mode` starts with all customizations off |

Turn everything off for one run with `--settings '{"disableAllHooks": true}'`. Note that setting it in *user*
settings isn't enough — project settings take precedence and can set it back to `false`.
