# Annotated `CLAUDE.md` template — for an AI/ML project

Copy the fenced block below to `CLAUDE.md` at your repo root (or `.claude/CLAUDE.md`), then delete every line that
doesn't pass the test in §0. The commentary after the block explains *why each section earns its place* — a section
that can't answer "would removing this cause Claude to make a mistake?" should not be there.

> Generate a first draft with `/init` rather than typing this from scratch. Then prune. `/init` is good at build
> commands and layout, and has no idea which of your conventions are load-bearing.

---

## 0. The test every line must pass

**Would removing this line cause Claude to make a mistake?** If no, cut it.

Target: **under 200 lines.** The docs are explicit that longer files consume more context *and reduce adherence* —
a bloated `CLAUDE.md` makes Claude follow your rules **less** reliably, because the important ones are buried.
It is loaded into every request forever, so a line here is the most expensive place in the repo to put a sentence.

---

## The template

```markdown
# <project-name>

Recommendation service: FastAPI + a fine-tuned ranker, served on GPU, trained offline in `training/`.
Python 3.12, `uv` for deps.

## Commands
- Install: `uv sync --all-extras`
- Test (all): `uv run pytest`
- Test (one): `uv run pytest tests/test_ranker.py::test_scores_are_calibrated -x`
- Lint + format: `uv run ruff check --fix . && uv run ruff format .`
- Types: `uv run mypy src/`
- Serve locally: `uv run uvicorn app.main:app --reload --port 8080`
- Train a smoke model (~90s, CPU): `uv run python training/train.py --config configs/smoke.yaml`

## Layout
- `src/app/` — FastAPI service. Route handlers stay thin; logic lives in `src/app/services/`.
- `src/ranker/` — model code. Pure functions, no I/O, no config reads.
- `training/` — offline jobs. May import `src/ranker`; must never import `src/app`.
- `configs/` — Hydra YAML. Every experiment is a config, never a code edit.
- `data/` — gitignored. Never commit anything under it.

## Conventions
- Type hints on every public function. `mypy --strict` is clean; keep it that way.
- Pydantic v2 models for every API boundary and every config object.
- Use `structlog`, not `print` and not stdlib `logging`.
- Random seeds come from `src/ranker/seed.py::set_seed`. Never call `np.random.seed` directly.
- New dependency: add to `pyproject.toml` and run `uv lock`. Do not `pip install`.

## Things that will bite you
- `src/ranker/features.py` builds features from an event stream. Any feature must use a timestamp strictly
  earlier than the prediction timestamp, or it is leakage. This has shipped to prod twice. Check it.
- The GPU box is Ampere; `torch.compile` with `mode="max-autotune"` hangs there. Use the default mode.
- `tests/integration/` needs a local Redis (`docker compose up -d redis`). Skip them with `-m "not integration"`.
- IMPORTANT: model artifacts in `artifacts/` are immutable. Train a new version; never overwrite one.

## Workflow
- Branch naming: `feat/<ticket>-short-slug`, `fix/<ticket>-short-slug`.
- Run lint, types, and the unit tests before you say a change is done. Show me the output, not a summary.
- Never commit or push unless I ask.
- For changes under `src/ranker/`, use plan mode first — a change there moves an offline metric.

## Compact instructions
When compacting, preserve: the failing test output, any metric numbers we discussed, and the current
hypothesis about the bug. Drop file listings and successful tool output.

@docs/architecture.md
```

---

## Why each section earns its place

### `# <project-name>` — the two-line orientation

Claude opens a fresh context window every session. Two sentences of "what is this and what stack" saves it three or
four exploratory file reads on *every* session, which is the cheapest trade in the entire file. Keep it to what it
does, the stack, and the runtime — not a pitch.

### `## Commands` — the single highest-value section

This is the canonical example of *"bash commands Claude can't guess."* If your test command is `pytest`, you don't
need this section. If it's `uv run pytest` behind a `--all-extras` sync, or `make test-unit ENV=ci`, Claude will
guess wrong, the guess will fail, and it will spend turns recovering.

Two details that pay for themselves:

- **Include the single-test form.** The docs recommend preferring one test over the whole suite for performance.
  If Claude knows the incantation it will use it; if not it runs your 8-minute suite to check a one-line change.
- **Note anything slow or expensive** (`~90s`, `needs GPU`) so Claude can decide whether to run it or ask.

### `## Layout` — only the parts that aren't obvious

Not a file-by-file tour; Claude can read a directory listing. What it cannot infer is **the dependency rules**:
"`training/` may import `src/ranker` but must never import `src/app`" is an architectural constraint that exists
only in your head and in a code review you're tired of writing. Same for "route handlers stay thin" — that is a
decision, not a discoverable fact.

If this section grows past ~10 lines, it belongs in a `.claude/rules/` file scoped with `paths:` frontmatter so it
only loads when Claude opens files in that area.

### `## Conventions` — only the deltas from the default

Claude already writes type hints and already knows PEP 8. What it can't know is that you standardised on
`structlog`, that seeds go through one helper, or that your dependency workflow is `uv lock` rather than `pip`.
Every line here should be a **delta from what a competent engineer would do by default**. "Write clean code" and
"use meaningful variable names" are the canonical wasted lines.

### `## Things that will bite you` — the section that actually changes outcomes

This is where a `CLAUDE.md` stops being documentation and starts being useful. Every entry is a real bug that has
happened, with the specific mechanism named. The leakage line is worth more than the other three sections combined,
because the mistake is invisible in tests and expensive in production (see [../../../../01-ml-foundations/](../../../../01-ml-foundations/)).

Populate it from: code review comments you've written twice, incidents, and corrections you keep typing into chat.
That's the documented trigger — *"Claude makes the same mistake a second time"* — and it applies to humans too.

Note the single `IMPORTANT:` marker. The docs say emphasis works **when it is rare**: "If you emphasize many lines,
none of them stands out." One `IMPORTANT` per file, maybe two. Zero is also fine.

### `## Workflow` — repository etiquette

Branch naming and "never commit unless I ask" are cheap to state and annoying to undo. **"Show me the output, not
a summary"** is the highest-leverage line in the section: it converts Claude's self-report ("tests pass") into
evidence you can check, which is the documented cure for the trust-then-verify gap.

The last line — plan mode for `src/ranker/` — routes a class of risky change into the slower, safer path without
you remembering to ask.

### `## Compact instructions` — the section almost nobody writes

A documented feature: a "Compact instructions" section in `CLAUDE.md` steers what survives summarization when the
window fills. Long sessions are where context is silently lost, and losing the failing test output or the metric
you were chasing costs you a re-run. Four lines here save real money.

### `@docs/architecture.md` — the import, used sparingly

`@path` imports are expanded **at launch**, so an imported file costs exactly what pasting it in would cost. Use an
import when the content is genuinely needed every session and is maintained elsewhere (an `AGENTS.md` you share with
another tool, a design doc the team edits). Do **not** use it to pretend your 600-line file is small.
If the content is only needed sometimes, it is a **skill**, not an import.

---

## What deliberately isn't here, and where it went instead

| Content | Why not in `CLAUDE.md` | Where it goes |
|---|---|---|
| The release checklist | needed occasionally, ~40 lines | a skill: `.claude/skills/release/SKILL.md` |
| Frontend style rules in a monorepo | only relevant under `web/` | `.claude/rules/frontend.md` with `paths: ["web/**"]` |
| "Never read `.env`" | a request, not enforcement | `permissions.deny: ["Read(./.env)"]` + a `PreToolUse` hook |
| "Always run the formatter after editing" | Claude may forget; a hook cannot | a `PostToolUse` hook on `Edit\|Write` |
| Full API reference for an internal service | huge, changes weekly | a skill, or an MCP server |
| Your personal editor preferences | not the team's business | `~/.claude/CLAUDE.md` |
| Your sandbox URLs and test credentials | must not be committed | `CLAUDE.local.md` (gitignored) |

That table is the real lesson of this file. **Most of what people put in `CLAUDE.md` belongs somewhere cheaper.**

---

## Maintenance

- Run `/context` and confirm the file appears under **Memory files**. If it isn't there, nothing else matters.
- Re-read it monthly. Delete rules for problems that no longer exist. Conflicting rules make Claude pick one
  arbitrarily, and a stale rule is worse than no rule.
- If Claude keeps violating one specific rule, the file is probably too long — prune before you add emphasis.
- If Claude asks you something this file already answers, the file is too long or the answer is buried.
- Every time you catch yourself typing the same correction twice: that's a new line here, a new hook, or a new skill.
  Decide which, deliberately. Guidance → here. Guarantee → hook. Procedure → skill.
