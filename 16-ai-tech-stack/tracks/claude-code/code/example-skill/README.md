# The `leakage-check` skill — install notes and design rationale

## Install

```bash
# project-scoped (committed, shared with your team)
mkdir -p .claude/skills/leakage-check
cp SKILL.md .claude/skills/leakage-check/

# or personal (every project on this machine)
mkdir -p ~/.claude/skills/leakage-check
cp SKILL.md ~/.claude/skills/leakage-check/
```

Then in a session: `/reload-skills`, check it appears in `/skills`, and run `/leakage-check` or
`/leakage-check src/ranker/features.py`.

> **The command name comes from the directory, not the frontmatter.** For personal and project skills, `name:`
> is only the display label in listings; you invoke `/<directory-name>`. So copy `SKILL.md` into a directory called
> `leakage-check`, not into one called `example-skill`. (Plugin skills are the exception: there `name` *does* set
> the last segment of `/plugin-name:skill-name`.)

## Why each frontmatter field is there

Every field is optional; only `description` is recommended. These are the ones that earn their place here:

| Field | Why |
|---|---|
| `name` | Display label in `/skills` and `/context`. Cosmetic for a project skill, but keeps listings readable. |
| `description` | **The load-bearing field.** Claude reads this to decide whether the skill is relevant. Put the key use case first — `description` + `when_to_use` are truncated at 1,536 characters in the skill listing. |
| `when_to_use` | Trigger phrases and example requests. Appended to `description` in the listing, so it counts toward the same cap. Use it when the description alone leaves the trigger ambiguous. |
| `argument-hint` | Autocomplete hint (`[file-or-directory]`) so you can see what it takes without opening the file. |
| `allowed-tools` | Pre-approves `Read`, `Grep`, `Glob` for the turn that invokes the skill, so an audit doesn't generate three permission prompts. The grant clears when you send your next message. |
| `disallowed-tools` | Removes `Write` and `Edit` from Claude's pool while the skill is active. This is the difference between "the instructions say report only" and **report only**. Also clears at your next message. |

Fields deliberately **not** used, and why:

- `disable-model-invocation: true` — would stop Claude loading this automatically. Here, auto-loading is the point:
  you *want* it to fire when you say "review my feature code" without remembering the command name.
- `context: fork` — would run it in a subagent. Good for long audits that would flood your window; overkill for a
  diff-sized review, and you lose the ability to ask a follow-up question against the same context.
- `model` / `effort` — the session defaults are fine. Override these only when a skill genuinely needs more
  reasoning than the rest of your session, because the override applies to the whole turn.
- `paths` — would restrict auto-activation to matching files. Worth adding in a monorepo
  (`paths: ["src/ranker/**", "training/**"]`); left off here so the example works anywhere.

## The body: two mechanics worth copying

**Dynamic context injection.** The line

```
!`git diff HEAD --stat`
```

is executed by Claude Code *before* Claude sees the skill content, and replaced by its output. So the instructions
arrive with the current diff already inlined — the skill is grounded in your real working tree rather than in
whatever files happen to be open. Use `` !`cmd` `` for cheap, bounded commands; a command that prints megabytes
will simply spend your context.

**`$ARGUMENTS`.** Everything you type after `/leakage-check` lands here. When no placeholder consumes them,
Claude Code appends them as `ARGUMENTS: <value>` instead. Named arguments are available too via the `arguments`
frontmatter list (`arguments: [target, severity]` → `$target`, `$severity`).

**Keep the body short.** Once a skill loads, its content stays in context across turns — every line is a recurring
token cost. State what to do; don't narrate why. This one is ~35 lines and that is close to the ceiling for
something you invoke often.

---

## When a skill beats a slash command

Short answer: **custom commands have been merged into skills.** A file at `.claude/commands/deploy.md` and a skill
at `.claude/skills/deploy/SKILL.md` both give you `/deploy` and both still work. Existing `commands/` files are not
deprecated. So the real question is what a skill directory adds over a single command file:

| | `.claude/commands/x.md` | `.claude/skills/x/SKILL.md` |
|---|---|---|
| Invoke with `/x` | yes | yes |
| Frontmatter | most fields, but **not** `name` or `paths` | all fields |
| Supporting files (scripts, templates, reference docs) | no — one file | yes — it's a directory |
| Claude can load it automatically when relevant | no | yes, unless `disable-model-invocation: true` |
| Run in a forked subagent (`context: fork`) | no | yes |
| Ships in a plugin with agents/hooks/MCP | no | yes |

**Use a skill when:**

- You want Claude to reach for it *without being asked* — the auto-invocation path is the biggest single difference,
  and it's what turns a command you forget into a habit that fires on its own. (This skill is the example: you say
  "review my feature changes", it loads.)
- It needs supporting files: a checklist, a schema, a script the skill runs via `${CLAUDE_SKILL_DIR}`.
- It should run in isolated context (`context: fork`) because it reads a lot and returns a little.
- It's going into a plugin for the team.
- It's reference material rather than an action — an API style guide Claude should apply while working. A command
  file can't do this at all, because nothing loads it unless you type it.

**A command file is still fine when** it's a three-line prompt you type yourself and nothing more. Prefer a skill
for new work anyway; the directory costs you one `mkdir` and leaves every door open.

**And the comparison that actually matters — skill vs the alternatives:**

- vs **`CLAUDE.md`**: `CLAUDE.md` loads every session forever. A skill's body loads only when used. Anything that
  isn't needed in *every* session belongs in a skill. This is the main reason to reach for one.
- vs **subagent**: a skill runs in your main context and shares it; a subagent has its own window and returns only
  a summary. Need isolation? Subagent (or `context: fork`).
- vs **hook**: a skill is instructions Claude interprets — the outcome can vary. A hook always fires on its event.
  Guidance goes in a skill; **guarantees go in a hook.**
