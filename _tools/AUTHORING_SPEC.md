# Authoring Spec — AI End-to-End Learning Track

Every module/track folder in this repo follows the **same** contract. Read this before writing anything.
The gold-standard reference implementation is [`/Users/srinip/ai-all/01-ml-foundations/`](../01-ml-foundations/) —
skim its `README.md`, `notes/01-core-concepts.md`, `code/`, `lab/EXERCISES.md` and `slides/deck.json`
and match that voice, density and structure.

## 1. Required files

```
<track>/
├── README.md                  # the front door (see §2)
├── notes/01-<topic>.md        # core concepts, teaching prose
├── notes/02-<topic>.md        # deep dive / practitioner craft
├── code/<name>.py|.ts         # 2+ RUNNABLE examples, heavily commented
├── code/requirements.txt      # or package.json for TS
├── lab/EXERCISES.md           # graded exercises with explicit deliverables + checks
├── papers/PAPERS.md           # primary sources / official docs, real URLs, annotated
├── resources/RESOURCES.md     # courses, repos, docs, communities — real URLs only
└── slides/deck.json           # slide source (see §3) — do NOT write .pptx yourself
```

## 2. README.md shape

- H1 with an emoji + track name.
- A blockquote line with time estimate and prerequisites.
- 2–4 sentences on *why this matters* and where it sits in the track.
- `## Learning objectives` — 5–7 numbered, testable capabilities ("you can X"), not topics.
- `## Suggested path` — a markdown table: step | do this | file (relative link) | time.
- `## The N terms you must own` — inline-code list of key vocabulary.
- `## Exit check ✅` — a concrete, verifiable deliverable.

## 3. slides/deck.json schema

```json
{
  "module": "16.1",
  "title": "Track Title",
  "subtitle": "One sharp line",
  "accent": "64748B",
  "slides": [
    {"type": "bullets", "title": "...", "bullets": ["...", "- nested sub-point"], "notes": "speaker note"},
    {"type": "table",   "title": "...", "columns": ["A","B"], "rows": [["1","2"]], "notes": "..."},
    {"type": "quote",   "title": "...", "quote": "one line", "bullets": ["..."], "notes": "..."},
    {"type": "section", "title": "...", "subtitle": "...", "notes": "..."}
  ]
}
```

Rules: 14–20 slides. Max 6 bullets/slide, max ~14 words each. Tables max 6 rows, 4 columns.
**ASCII only inside deck.json** (no smart quotes, em dashes, arrows, or emoji — use `->`, `--`).
Every slide gets a `notes` field with something a presenter would actually say.
A title slide and an outro slide are added automatically — do not write them.
Build with: `/Users/srinip/ai-all/.venv/bin/python /Users/srinip/ai-all/_tools/build_decks.py <track-folder-name>`
and confirm it prints a ✓ line.

## 4. Quality bar — this is the part that matters

- **Teach, don't list.** Explain *why*, show the mechanism, name the failure mode. A bulleted glossary is a failure.
- **Opinionated.** Say which option you would pick and why. Name the common mistake.
- **Concrete.** Real library names, real version-era behaviour, real numbers, real commands.
- **Tables** for comparisons; **ASCII diagrams** for architectures; short code blocks inline in notes.
- **Forward/backward links** to other modules using relative paths (e.g. `../../08-rag/`), with a
  "where this returns" table at the end of the core-concepts note.
- **Runnable code**: scripts must execute top-to-bottom and print something instructive. If a script needs
  network/API keys, guard it so it degrades to an offline explanation instead of crashing, and say so in a docstring.
- **No fabrication.** Every URL must be one you are confident exists. Prefer official docs, arXiv, and
  well-known GitHub repos. If unsure of a URL, link the project root rather than a deep path.
- Notes files: aim 150–250 lines each. Be substantive; do not pad.

## 5. Tone

Direct, technical, slightly opinionated, occasionally dry-funny. Write for a competent engineer who is new
to this specific topic and hates being condescended to. Second person. No marketing language.

## 6. Building the book

`_tools/build_book.py` turns the markdown of the whole repository into one print-ready PDF plus a PDF
per chapter:

```bash
.venv/bin/python -m pip install markdown pypdf websockets pypdfium2
.venv/bin/python _tools/build_book.py                  # whole book -> book/
.venv/bin/python _tools/build_book.py 04-llm 08-rag    # a subset, for a quick look
.venv/bin/python _tools/build_book.py --help
```

Discovery is by folder (`00-launchpad`, `01-…`–`16-…`, `16-…/tracks/*`, `99-capstones`), so a new
module appears in the book automatically once it has `README.md`, `notes/`, `lab/`, `papers/` and
`resources/`. A part's chapters are, in order: the README (as **Overview**), each `notes/*.md`, the
lab, any markdown under `code/` (templates, prompt patterns), then `papers/PAPERS.md` +
`resources/RESOURCES.md` as one **Sources** chapter. `slides/slides.md` — a generated export of the
deck — and non-markdown code are deliberately not printed.
