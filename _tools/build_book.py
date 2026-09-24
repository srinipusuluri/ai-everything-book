#!/usr/bin/env python3
"""
build_book.py -- assemble every markdown file in this repo into one print-ready PDF book,
plus a standalone PDF for each chapter.

    ../.venv/bin/python _tools/build_book.py                    # the whole book
    ../.venv/bin/python _tools/build_book.py 04-llm 08-rag      # only these parts
    ../.venv/bin/python _tools/build_book.py --no-chapters      # skip the per-chapter PDFs
    ../.venv/bin/python _tools/build_book.py --keep-html        # keep book/_build/book.html

Dependencies (already in the repo venv; pypdfium2 is an optional speed-up for the page scan):
    ../.venv/bin/pip install markdown pypdf websockets pypdfium2

What it produces
----------------
book/
├── AI-End-to-End-Learning-Track.pdf   the book: front matter (cover, how-to, contents),
│                                      16 modules + 7 tech-stack tracks + capstones + appendices,
│                                      continuous page numbers, clickable PDF outline
├── chapters/NNN-<label>-<slug>.pdf    one PDF per chapter, in book order
└── _build/book.html                   the intermediate HTML (debugging / re-render)

How it works
------------
1. Discovery. Each part folder (00-launchpad, 01..16, 16's tracks, 99-capstones) contributes
   chapters: README.md (overview), notes/*.md (one chapter each), lab/EXERCISES.md, and a combined
   papers + resources chapter. Part titles, subtitles and accent colours come from slides/deck.json
   when it exists, otherwise from _modules.tsv.
2. Markdown -> HTML with the `markdown` package. Relative repo links become plain text plus the
   repo path (a printed page cannot follow `../../08-rag/`); http(s) links stay clickable.
3. One render. The whole book is printed as a single document through headless Chrome over the
   DevTools protocol, so page numbers are continuous and the contents page can carry true page
   numbers. Every chapter starts with an invisible 1px-white marker (BKMK0007); the printed pages
   are scanned for those markers, which yields both the split points and the contents numbers.
4. Two or three passes. Pass 1 lays the book out with placeholder contents numbers, later passes
   write the real ones and verify that the detected chapter pages still match; the loop stops as
   soon as the layout is stable, so the contents and the body can never disagree.
5. A final marker-free pass. The shipped PDF swaps each marker's glyphs for a space — same element,
   same metrics, so the measured pagination holds — leaving a text layer a reader can copy, search
   and have read aloud without tripping over BKMK0007.
"""
from __future__ import annotations

import base64
import io
import json
import logging
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import pypdf

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "book"
CHAPTERS_DIR = OUT / "chapters"
BUILD_DIR = OUT / "_build"

CHROME_BIN = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
BOOK_TITLE = "AI End-to-End Learning Track"
BOOK_SUBTITLE = ("The 20% of AI that carries the other 80%: from machine-learning foundations to LLMs, "
                 "agents, RAG, security, governance and production")
AUTHOR_NAME = "Srini Pusuluri"
AUTHOR_LINKEDIN = "https://www.linkedin.com/in/pusulurisrinivasa/"
AUTHOR_GITHUB = "https://github.com/srinipusuluri/resume"

INK = "#171923"
MUTED = "#5b6172"
LINE = "#e5e7ef"
WASH = "#f6f7fb"
FALLBACK_ACCENT = "4F46E5"

# Parts that are not modules and therefore have no row in _modules.tsv.
EXTRA_PARTS = {
    "00-launchpad": dict(num="0", title="Launchpad", emoji="🚀", accent="334155",
                         tagline="Read this first: how the track is built, how to set it up, and how to use this book."),
    "99-capstones": dict(num="99", title="Capstone Projects", emoji="", accent="BE123C",
                         tagline="Three weekend-to-a-week projects that pull the track together."),
}

SERIF = '"Charter", "Iowan Old Style", Georgia, "Times New Roman", serif'
SANS = '"Helvetica Neue", Helvetica, Arial, sans-serif'
MONO = '"SF Mono", "Menlo", "Consolas", "DejaVu Sans Mono", monospace'

CSS = f"""
@page {{ size: Letter; margin: 0.85in 0.78in 0.72in 0.78in; }}
* {{ box-sizing: border-box; }}
html {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
body {{
  margin: 0; color: {INK}; background: #fff;
  font-family: {SERIF}; font-size: 10.4pt; line-height: 1.52;
  hyphens: auto; -webkit-hyphens: auto;
}}
p, li {{ orphans: 2; widows: 2; }}
a {{ color: inherit; text-decoration: none; }}
a.ext {{ color: #1d4ed8; }}
code {{
  font-family: {MONO}; font-size: 8.6pt; background: #f1f2f8;
  padding: 0 2px; border-radius: 3px; overflow-wrap: anywhere;
}}
pre {{
  font-family: {MONO}; font-size: 7.6pt; line-height: 1.42;
  background: {WASH}; border: 1px solid {LINE}; border-left: 3px solid var(--accent, #{FALLBACK_ACCENT});
  border-radius: 4px; padding: 7px 9px; margin: 8px 0 10px;
  white-space: pre-wrap; overflow-wrap: anywhere; break-inside: avoid;
}}
pre code {{ background: none; padding: 0; font-size: 7.6pt; }}
blockquote {{
  margin: 10px 0; padding: 7px 12px; background: #fbfbfe;
  border-left: 3px solid #c9cbe0; border-radius: 0 4px 4px 0; color: #3f4557;
}}
blockquote p {{ margin: 4px 0; }}
h1, h2, h3, h4 {{ font-family: {SANS}; color: {INK}; line-height: 1.22; }}
h2 {{
  font-size: 14.5pt; margin: 20px 0 8px; padding-bottom: 4px;
  border-bottom: 1px solid {LINE}; break-after: avoid;
}}
h3 {{ font-size: 11.6pt; margin: 15px 0 5px; color: #2b2f3f; break-after: avoid; }}
h4 {{ font-size: 10.2pt; margin: 12px 0 4px; color: #3f4557; break-after: avoid; }}
h2 code, h3 code, h4 code {{ font-size: 0.88em; }}
ul, ol {{ margin: 7px 0 10px; padding-left: 20px; }}
li {{ margin: 3px 0; }}
li > p {{ margin: 3px 0; }}
hr {{ border: 0; border-top: 1px solid {LINE}; margin: 16px 0; }}
table {{
  width: 100%; border-collapse: collapse; margin: 10px 0 12px;
  font-family: {SANS}; font-size: 8.7pt; break-inside: avoid;
}}
th, td {{ border: 1px solid {LINE}; padding: 4px 6px; text-align: left; vertical-align: top;
          overflow-wrap: anywhere; }}
th {{ background: {WASH}; font-weight: 600; }}
tbody tr:nth-child(even) td {{ background: #fcfcfe; }}
img {{ max-width: 100%; }}
"""

CSS += f"""
/* ---------- page furniture ---------- */
.part, .chapter, .front-page {{ break-before: page; }}
.front-page.first {{ break-before: auto; }}
/* Out of flow on purpose: the marker must never influence pagination, so that swapping its glyphs
   for a space in the final (marker-free) pass cannot move a single line. */
.bkmk {{ position: absolute; margin: 0; padding: 0; color: #ffffff; font-size: 1px; line-height: 1; }}
.kicker {{
  font-family: {SANS}; font-size: 8pt; letter-spacing: 0.09em; text-transform: uppercase;
  color: var(--accent, #{FALLBACK_ACCENT}); font-weight: 700;
}}

/* ---------- front matter ---------- */
.cover {{ padding-top: 0.6in; }}
.cover-band {{ height: 10px; background: #{FALLBACK_ACCENT}; width: 2.1in; margin-bottom: 34px; }}
.cover h1 {{
  font-family: {SANS}; font-size: 40pt; line-height: 1.03; letter-spacing: -0.02em;
  margin: 0 0 14px; max-width: 6.2in;
}}
.cover .sub {{ font-size: 12.4pt; color: {MUTED}; max-width: 5.7in; margin-bottom: 10px; }}
.cover .byline {{ font-family: {SANS}; font-size: 10.8pt; font-weight: 600; letter-spacing: 0.02em;
                  color: {INK}; margin-bottom: 26px; }}
.cover .byline span {{ font-weight: 400; color: {MUTED}; }}
.cover .stats {{ display: flex; gap: 12px; flex-wrap: wrap; margin: 24px 0 14px; }}
.cover .stat {{ border: 1px solid {LINE}; border-radius: 8px; padding: 9px 13px; min-width: 1.1in; }}
.cover .stat b {{ display: block; font-family: {SANS}; font-size: 19pt; }}
.cover .stat span {{ font-family: {SANS}; font-size: 7.6pt; letter-spacing: 0.07em;
                     text-transform: uppercase; color: {MUTED}; }}
.cover .fine {{ font-family: {SANS}; font-size: 8.6pt; color: {MUTED}; margin-top: 20px; }}
.page-title {{ font-family: {SANS}; font-size: 21pt; margin: 0 0 4px; }}
.page-rule {{ height: 3px; width: 0.85in; background: var(--accent, #{FALLBACK_ACCENT}); margin: 0 0 16px; }}

/* ---------- contents ---------- */
.toc {{ font-family: {SANS}; }}
.toc-part {{
  display: flex; align-items: baseline; gap: 7px;
  margin: 13px 0 3px; font-size: 10pt; font-weight: 700;
  color: var(--toc-accent, #{FALLBACK_ACCENT});
}}
.toc-ch {{ display: flex; align-items: baseline; gap: 7px; margin: 1.5px 0; font-size: 9pt; }}
.toc-label {{ width: 0.6in; color: {MUTED}; font-variant-numeric: tabular-nums; }}
.toc-lead {{ flex: 1; border-bottom: 1px dotted #c7cad6; transform: translateY(-3px); }}
.toc-pg {{ width: 0.42in; text-align: right; font-variant-numeric: tabular-nums; color: {MUTED}; }}
.toc-part .toc-pg {{ color: {INK}; }}

/* ---------- part divider ---------- */
.part-divider {{ padding-top: 1.85in; }}
.part-num {{
  font-family: {SANS}; font-size: 8.6pt; letter-spacing: 0.16em; text-transform: uppercase;
  color: var(--accent, #{FALLBACK_ACCENT}); font-weight: 700; margin-bottom: 10px;
}}
.part-title {{ font-family: {SANS}; font-size: 30pt; line-height: 1.08; margin: 0 0 10px; }}
.part-sub {{ font-size: 12.4pt; color: {MUTED}; max-width: 5.5in; margin-bottom: 20px; }}
.part-tag {{ font-size: 10.6pt; border-left: 3px solid var(--accent, #{FALLBACK_ACCENT});
             padding-left: 11px; color: #3f4557; max-width: 5.5in; }}
.part-list {{ margin-top: 0.5in; font-family: {SANS}; }}
.part-list-head {{ font-size: 8.2pt; letter-spacing: 0.12em; text-transform: uppercase;
                   color: {MUTED}; margin-bottom: 7px; }}
.part-list ol {{ padding-left: 0; list-style: none; margin: 0; }}
.part-list li {{ font-size: 9.4pt; margin: 3px 0; }}
.part-list .lb {{ display: inline-block; width: 0.58in; color: var(--accent, #{FALLBACK_ACCENT});
                  font-weight: 700; }}

/* ---------- chapter opener ---------- */
.opener {{ margin-bottom: 13px; }}
.opener .ch-label {{
  font-family: {SANS}; font-size: 8.4pt; letter-spacing: 0.1em; text-transform: uppercase;
  color: var(--accent, #{FALLBACK_ACCENT}); font-weight: 700; margin-bottom: 5px;
}}
.opener h1 {{ font-family: {SANS}; font-size: 23pt; line-height: 1.13; margin: 0 0 8px; }}
.opener .ch-meta {{ font-family: {MONO}; font-size: 7.6pt; color: {MUTED}; overflow-wrap: anywhere; }}
.opener .ch-rule {{ height: 3px; width: 1in; background: var(--accent, #{FALLBACK_ACCENT});
                    margin: 11px 0 0; }}
.xref-p {{ font-family: {MONO}; font-size: 7.4pt; color: {MUTED}; }}
/* Chapter index (appendix A.2): a narrow number, a wide title, a right-aligned page, and the source
   path in mono with the rest of the width — it is the column readers copy from. */
.srcmap thead th:nth-child(1) {{ width: 0.46in; }}
.srcmap thead th:nth-child(3) {{ width: 0.62in; text-align: right; }}
.srcmap tr.grp td {{ background: #eef0f8; font-weight: 700; }}
.srcmap {{ break-inside: auto; }}
.srcmap tr {{ break-inside: avoid; }}
.srcmap tr.row td:nth-child(1),
.srcmap tr.row td:nth-child(3) {{ white-space: nowrap; }}
.srcmap tr.row td:nth-child(3) {{ text-align: right; color: {MUTED}; }}
.srcmap tr.row td:nth-child(4) {{ font-family: {MONO}; font-size: 7.4pt; }}
"""


# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------
EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\u2190-\u21FF\u2600-\u27BF\u2B00-\u2BFF\uFE0F]")


def leading_emoji(text: str) -> str:
    """Pull a leading emoji off a heading, e.g. '# 🐍 Track 16.1' -> '🐍'."""
    out = []
    for ch in text.strip():
        if ch.isspace():
            continue
        if EMOJI_RE.match(ch) or ord(ch) > 0x2190:
            out.append(ch)
            continue
        break
    return "".join(out)


def slugify(text: str, maxlen: int = 58) -> str:
    text = EMOJI_RE.sub("", text)
    text = re.sub(r"[^\w\s.-]", " ", text.lower())
    text = re.sub(r"[\s_.]+", "-", text).strip("-")
    text = re.sub(r"-{2,}", "-", text)
    return text[:maxlen].rstrip("-") or "chapter"


def rel_dir(path: Path) -> str:
    d = path.parent.relative_to(ROOT)
    return "" if str(d) == "." else d.as_posix()


def split_title(md_text: str) -> tuple[str, str]:
    """Peel the first '# ' heading off a markdown file: (title, rest)."""
    lines = md_text.split("\n")
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        if line.startswith("# "):
            return line[2:].strip(), "\n".join(lines[i + 1:])
        break
    return "", md_text


def demote_headings(md_text: str, by: int = 1) -> str:
    """Push every ATX heading down `by` levels, leaving fenced code alone."""
    out, fence = [], False
    for line in md_text.split("\n"):
        if line.lstrip().startswith("```"):
            fence = not fence
            out.append(line)
            continue
        if not fence and re.match(r"^#{1,5}\s", line):
            line = "#" * by + line
        out.append(line)
    return "\n".join(out)


A_RE = re.compile(r'<a href="([^"]+)"[^>]*>(.*?)</a>', re.S)
TAG_RE = re.compile(r"<[^>]+>")


def rewrite_links(html: str, src_dir: str) -> str:
    """Keep http(s) links clickable; turn repo-relative links into text + path."""
    def sub(m: re.Match) -> str:
        href, text = m.group(1), m.group(2)
        if href.startswith(("http://", "https://")):
            return f'<a class="ext" href="{href}">{text}</a>'
        if href.startswith("#"):
            return f'<a href="{href}">{text}</a>'
        target = posixpath.normpath(posixpath.join(src_dir, href.split("#")[0]))
        if target in (".", "") or target.startswith(".."):
            target = href
        plain = TAG_RE.sub("", text).strip()
        if plain.rstrip("/").lower() == target.rstrip("/").lower() or plain == href:
            return f'<span>{text}</span>'
        return f'<span>{text} <span class="xref-p">[{target}]</span></span>'

    return A_RE.sub(sub, html)


def md_to_html(md_text: str, src_dir: str = "") -> str:
    import markdown

    engine = markdown.Markdown(
        extensions=["extra", "sane_lists", "toc"],
        extension_configs={"toc": {"permalink": False, "anchorlink": False}},
    )
    html = engine.convert(md_text)
    html = re.sub(r"<div class=\"toc\">.*?</div>\s*</div>", "", html, flags=re.S)
    return rewrite_links(html, src_dir)


def esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# --------------------------------------------------------------------------------------
# model
# --------------------------------------------------------------------------------------
@dataclass
class Chapter:
    idx: int                      # 1-based position in the book
    key: str                      # stable id, e.g. "01-ml-foundations/notes/01-core-concepts"
    label: str                    # "1.2", "16.3.1", "A.1"
    title: str
    kicker: str                   # "Part 01 -- Machine Learning Foundations"
    accent: str
    files: list[Path]
    kind: str = ""                # "", "Overview", "Lab", "Sources", "Appendix"
    html: str = ""
    start_page: int = 0
    end_page: int = 0

    @property
    def bkmk(self) -> str:
        return f"BKMK{self.idx:04d}"


@dataclass
class Part:
    key: str
    num: str                      # "01", "16.3", "A"
    kind_word: str                # "Part" | "Track" | "Appendices"
    title: str
    subtitle: str
    tagline: str
    accent: str
    chapters: list[Chapter] = field(default_factory=list)
    idx: int = 1                  # 1-based position in the book (used for the divider marker)
    divider_page: int = 0         # page the divider lands on (measured, not assumed)

    @property
    def divider_mark(self) -> str:
        return f"DIV{self.idx:04d}"

    @property
    def label(self) -> str:
        if self.num == "A":
            return "Appendices"
        return f"{self.kind_word} {self.num}".strip()


# --------------------------------------------------------------------------------------
# discovery
# --------------------------------------------------------------------------------------
def load_module_rows() -> dict[str, dict]:
    rows: dict[str, dict] = {}
    tsv = ROOT / "_modules.tsv"
    if not tsv.exists():
        return rows
    for line in tsv.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        key, title, emoji, tagline, accent = line.split("\t")
        rows[key] = dict(title=title.strip(), emoji=emoji.strip(),
                         tagline=tagline.strip(), accent=accent.strip().lstrip("#"))
    return rows


def read_deck(folder: Path) -> dict:
    deck = folder / "slides" / "deck.json"
    if not deck.exists():
        return {}
    try:
        return json.loads(deck.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def h1_of(path: Path) -> str:
    try:
        title, _ = split_title(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, UnicodeDecodeError):
        return ""
    return title


def make_part(folder: Path, rows: dict[str, dict], *, is_track: bool, num: str = "") -> Part:
    deck = read_deck(folder)
    row = rows.get(folder.name) or EXTRA_PARTS.get(folder.name) or {}
    readme_title = h1_of(folder / "README.md")
    fallback = re.sub(r"^(Track|Module)\s+[\d.]+\s*[—–-]\s*", "", readme_title).strip()
    title = (deck.get("title") or row.get("title") or fallback or folder.name).strip()
    folder_num = re.match(r"^(\d\d)", folder.name)
    part_num = (num or str(deck.get("module") or row.get("num")
                          or (folder_num.group(1) if folder_num else ""))).strip()
    accent = (deck.get("accent") or row.get("accent") or FALLBACK_ACCENT).lstrip("#")
    emoji = row.get("emoji") or leading_emoji(readme_title)
    if emoji and emoji not in title:
        title = f"{emoji} {title}"
    return Part(
        key=folder.relative_to(ROOT).as_posix(),
        num=part_num,
        kind_word="Track" if is_track else "Part",
        title=title,
        subtitle=(deck.get("subtitle") or "").strip(),
        tagline=(row.get("tagline") or "").strip(),
        accent=accent,
    )


def chapter_groups(folder: Path) -> list[tuple[str, str, list[Path]]]:
    """(kind, title override, files) groups for one part folder, in reading order."""
    groups: list[tuple[str, str, list[Path]]] = []
    readme = folder / "README.md"
    if readme.exists():
        groups.append(("Overview", "Overview", [readme]))
    notes_dir = folder / "notes"
    if notes_dir.is_dir():
        for note in sorted(notes_dir.glob("*.md")):
            groups.append(("", "", [note]))
    lab = folder / "lab" / "EXERCISES.md"
    if lab.exists():
        groups.append(("Lab", "Lab exercises", [lab]))
    code_dir = folder / "code"
    code_docs = sorted(p for p in code_dir.rglob("*.md")) if code_dir.is_dir() else []
    if code_docs:
        # markdown that lives with the code (templates, prompt patterns, READMEs) is content
        groups.append(("Code", "Code templates & reference notes", code_docs))
    sources = [p for p in (folder / "papers" / "PAPERS.md", folder / "resources" / "RESOURCES.md")
               if p.exists()]
    if sources:
        groups.append(("Sources", "Primary sources & further reading", sources))
    return groups


def render_group(part: Part, files: list[Path], override: str) -> tuple[str, str]:
    """Render the markdown of one chapter. Returns (title, html)."""
    blocks: list[str] = []
    title = override or ""
    for i, path in enumerate(files):
        raw = path.read_text(encoding="utf-8")
        heading, body = split_title(raw)
        head = heading or path.stem
        if i == 0 and not override:
            title = head
        else:
            blocks.append(f'<h2 class="src-head">{esc(head)}</h2>')
            body = demote_headings(body, 1)
        blocks.append(md_to_html(body, rel_dir(path)))
    return title or files[0].stem, "\n".join(blocks)


def fill_chapters(part: Part, folder: Path, counter: list[int]) -> None:
    for n, (kind, override, files) in enumerate(chapter_groups(folder), start=1):
        counter[0] += 1
        title, html = render_group(part, files, override)
        part.chapters.append(Chapter(
            idx=counter[0],
            key=files[0].relative_to(ROOT).as_posix(),
            label=f"{part.num}.{n}",
            title=title,
            kicker=f"{part.label} — {part.title}",
            accent=part.accent,
            files=files,
            kind=kind,
            html=html,
        ))


def appendices_part(counter: list[int]) -> Part:
    part = Part(key="_tools/appendices", num="A", kind_word="Appendices", title="Appendices",
                subtitle=("How this book was built, a chapter index, the authoring contract, "
                          "and the shared reference tables."),
                tagline="", accent="475569")

    def add(label: str, title: str, kind: str, files: list[Path],
            html: str = "", markdown_text: str = "") -> None:
        counter[0] += 1
        part.chapters.append(Chapter(
            idx=counter[0], key=f"appendices/{label}", label=label, title=title,
            kicker="Appendices", accent=part.accent, files=files, kind=kind,
            html=md_to_html(markdown_text) if markdown_text else html))

    add("A.1", "How this book was built", "Overview", [])          # filled by refresh_appendices
    add("A.2", "Chapter index", "Overview", [])                    # filled by refresh_appendices

    spec = ROOT / "_tools" / "AUTHORING_SPEC.md"
    spec_title, spec_html = render_group(part, [spec], "")
    add("A.3", spec_title, "Appendix", [spec], html=spec_html)

    shared = [ROOT / "_shared" / "glossary" / "README.md",
              ROOT / "_shared" / "cheatsheets" / "README.md"]
    shared_title, shared_html = render_group(part, shared, "Glossary & cheatsheets")
    add("A.4", shared_title, "Appendix", shared, html=shared_html)
    return part


def source_files(parts: list[Part]) -> list[Path]:
    seen: dict[str, Path] = {}
    for part in parts:
        for chapter in part.chapters:
            for path in chapter.files:
                seen[path.as_posix()] = path
    return [seen[k] for k in sorted(seen)]


def chapter_index_html(parts: list[Part]) -> str:
    rows = []
    for part in parts:
        rows.append('<tr class="grp">'
                    f'<td colspan="4">{esc(part.label)} — {esc(part.title)}</td></tr>')
        for chapter in part.chapters:
            src = "<br>".join(esc(p.relative_to(ROOT).as_posix()) for p in chapter.files) or "generated"
            rows.append(f'<tr class="row"><td>{esc(chapter.label)}</td><td>{esc(chapter.title)}</td>'
                        f"<td>{chapter.start_page or ''}</td><td>{src}</td></tr>")
    return ('<table class="srcmap"><thead><tr><th>Ch.</th><th>Title</th><th>Page</th>'
            "<th>Source file</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>")


APPENDIX_INDEX_HEAD = """## Every chapter, with the file it came from

Use this when you want to go the other way — from something you remember reading here, back to the
markdown (or the deck, or the code) that lives in the repository. **Ch.** is the chapter number used
in the contents page and in the PDF outline; **Page** is where that chapter starts in this book.
"""


def appendix_build_md(parts: list[Part], pages: int) -> str:
    chapters = sum(len(p.chapters) for p in parts)
    files = len(source_files(parts))
    return f"""## What this document is

Every word in this book comes from the markdown in this repository: the module READMEs, the two or
three teaching notes per module, the labs, the source lists and the shared reference tables. Nothing
was rewritten for print — the book *is* the repository, re-typeset so it can be read and skimmed the
way a textbook is read, instead of the way hundreds of files are read.

Each **module** is a part. Inside a part you get, in order: the **overview** (the module README, with
its time estimate and exit check), the **teaching notes** (`notes/01-…`, `notes/02-…`, and in one case
a third), the **lab exercises** with their stated deliverables, any **code templates** that ship as
markdown beside that module's scripts, and one chapter of **primary sources and further reading**.
Module 16 is special: it opens with the map of the tech stack and is then split into its seven tracks —
16.1 Python through 16.7 Claude Code and the Agent SDK — each a part in its own right.

## Reading conventions

| Convention | Meaning |
|---|---|
| `Chapter n.m` | Printed at the top of every chapter; the contents page, this index and the PDF outline use the same numbering. |
| Repo path in brackets, e.g. `[see also] [08-rag/notes/02-advanced-patterns-and-evaluation.md]` | A relative link from the markdown, which print cannot follow. The words stay, and the target path is printed next to them. |
| Blue links | Real `https://` URLs remain clickable in the PDF. |
| Code blocks | Printed verbatim. Long lines wrap, so ASCII diagrams that fit the column keep their alignment and ones that do not will visibly fold. |
| No source listings | The runnable scripts in each module's `code/` folder are deliberately not echoed here — they are meant to be run, not read. The lab chapters tell you which ones to run and in what order. |
| Slide decks | Every module also ships `slides/deck.json` plus a built `.pptx`; those are not part of the book. |

## How to rebuild it

```bash
cd <repo root>
.venv/bin/python -m pip install markdown pypdf websockets
.venv/bin/python _tools/build_book.py                     # the whole book
.venv/bin/python _tools/build_book.py 04-llm 08-rag        # a subset, for a quick look
```

The build prints the entire book through headless Chrome as one document, so page numbers run
continuously from the cover to the last page. It then reads the chapter breaks back out of the printed
PDF, which gives both the split points for the per-chapter files and the page numbers printed in the
contents. Contents and body therefore cannot disagree.

## Build facts

| | |
|---|---|
| Parts | {len(parts)} |
| Chapters | {chapters} |
| Source markdown files | {files} |
| Printed pages | {pages or "—"} |
| Paper and type | US Letter; 10.4pt Charter body, Helvetica Neue headings, SF Mono code |
| Generator | `_tools/build_book.py` |
"""


def refresh_appendices(parts: list[Part], pages: int) -> None:
    """(Re)build the generated appendix chapters. Safe to call on every render pass."""
    if not parts or parts[-1].num != "A":
        return
    build_chapter, index_chapter = parts[-1].chapters[0], parts[-1].chapters[1]
    build_chapter.html = md_to_html(appendix_build_md(parts, pages))
    index_chapter.html = md_to_html(APPENDIX_INDEX_HEAD) + chapter_index_html(parts)


# --------------------------------------------------------------------------------------
# html assembly
# --------------------------------------------------------------------------------------
def chapter_html(part: Part, chapter: Chapter, markers: bool = True) -> str:
    word = "Appendix" if part.num == "A" else "Chapter"
    label = f"{word} {chapter.label}"
    if chapter.kind:
        label += f" · {chapter.kind}"
    sources = " · ".join(p.relative_to(ROOT).as_posix() for p in chapter.files) or "generated"
    mark = f'<span class="bkmk">{chapter.bkmk}</span>' if markers else BKMK_BLANK
    return (
        f'<section class="chapter" style="--accent:#{chapter.accent}">'
        f"{mark}"
        f'<header class="opener">'
        f'<div class="ch-label">{esc(label)}</div>'
        f'<h1>{esc(chapter.title)}</h1>'
        f'<div class="ch-meta">{esc(chapter.kicker)} &nbsp;·&nbsp; {esc(sources)}</div>'
        f'<div class="ch-rule"></div>'
        f"</header>"
        f'<div class="ch-body">{chapter.html}</div>'
        f"</section>"
    )


def part_html(part: Part, markers: bool = True) -> str:
    tag = (f'<div class="part-tag">{esc(part.tagline)}</div>' if part.tagline else "")
    sub = (f'<div class="part-sub">{esc(part.subtitle)}</div>' if part.subtitle else "")
    items = "".join(
        f'<li><span class="lb">{esc(c.label)}</span>{esc(c.title)}</li>' for c in part.chapters)
    mark = f'<span class="bkmk">{part.divider_mark}</span>' if markers else BKMK_BLANK
    return (
        f'<section class="part" style="--accent:#{part.accent}">'
        f"{mark}"
        f'<div class="part-divider">'
        f'<div class="part-num">{esc(part.label)}</div>'
        f'<h1 class="part-title">{esc(part.title)}</h1>'
        f"{sub}{tag}"
        f'<div class="part-list"><div class="part-list-head">In this part</div>'
        f"<ol>{items}</ol></div>"
        f"</div></section>"
    )


def cover_html(parts: list[Part], chapters: int, pages: int) -> str:
    stats = [
        ("16", "modules"),
        ("7", "tech-stack tracks"),
        (str(chapters), "chapters"),
        (str(pages) if pages else "—", "printed pages"),
    ]
    boxes = "".join(f"<div class='stat'><b>{v}</b><span>{k}</span></div>" for v, k in stats)
    return (
        f'<section class="front-page first cover" style="--accent:#{FALLBACK_ACCENT}">'
        f'<div class="cover-band"></div>'
        f"<h1>{esc(BOOK_TITLE)}</h1>"
        f'<div class="sub">{esc(BOOK_SUBTITLE)}</div>'
        f'<div class="byline"><span>by</span> {esc(AUTHOR_NAME)}</div>'
        f'<div class="stats">{boxes}</div>'
        f'<div class="fine">{esc(COVER_NOTE)}</div>'
        f"</section>"
    )


def contents_html(parts: list[Part], numbers: dict[str, int]) -> str:
    """numbers maps block markers ("BKMK0007"/"DIV0003") to the page they landed on."""
    rows = ['<section class="front-page toc" style="--accent:#%s">' % FALLBACK_ACCENT,
            '<h1 class="page-title">Contents</h1><div class="page-rule"></div>']
    for part in parts:
        # the divider page sits immediately before the part's first chapter
        first = part.chapters[0] if part.chapters else None
        pg = part.divider_page or ((first.start_page - 1) if first and first.start_page else 0)
        rows.append(f'<div class="toc-part" style="--toc-accent:#{part.accent}">'
                    f"<span>{esc(part.label)} &nbsp; {esc(part.title)}</span>"
                    f'<span class="toc-lead"></span><span class="toc-pg">{pg or ""}</span></div>')
        for chapter in part.chapters:
            num = numbers.get(chapter.bkmk, 0)
            rows.append(f'<div class="toc-ch"><span class="toc-label">{esc(chapter.label)}</span>'
                        f"<span>{esc(chapter.title)}</span>"
                        f'<span class="toc-lead"></span><span class="toc-pg">{num or ""}</span></div>')
    rows.append("</section>")
    return "".join(rows)


COVER_NOTE = ("Generated from the markdown of this repository by _tools/build_book.py. "
              "A part is a module; a chapter is one file from it. Page numbers run continuously "
              "and are the same numbers you will find in the contents.")

ABOUT_AUTHOR = f"""**{AUTHOR_NAME}** is a Sr. Salesforce/AI/CRM Program Architect. His work sits across
AI/CRM/CPQ strategy, AI chatbots and agents, CPQ migrations, AI/ML, CDP, security and integration --
most recently centered on Agentforce. He holds 20 Salesforce certifications and 5 AI certifications,
has worked across Google, Elastic, GE, AT&T, IBM and USAA, and trains Salesforce practitioners and
speaks at Dreamforce.

| | |
|---|---|
| LinkedIn | [linkedin.com/in/pusulurisrinivasa]({AUTHOR_LINKEDIN}) |
| GitHub / resume | [github.com/srinipusuluri/resume]({AUTHOR_GITHUB}) |
"""

WHY_THIS_BOOK = """In the last two years the AI stack moved from "an LLM you prompt" to "an agent you
architect" -- RAG, tool use, MCP, LangGraph, agentic orchestration, governance, evals, all of it
landing on architects' plates at once, usually without a map connecting the pieces.

I kept re-deriving the same foundations -- why a transformer attends the way it does, why a RAG
pipeline hallucinates anyway, why an agent's 95%-per-step accuracy still fails one task in three --
for different audiences and different projects.

This book is that map, written the way I wish I had had it: one continuous path from the linear
algebra under a gradient to a governed, evaluated, production agent, with runnable code and no
hand-waving in between. Sixteen modules, each with notes, runnable code, a lab, primary sources and
a slide deck -- built to be worked through top to bottom, or dropped into wherever the gap actually
is.
"""

HOW_TO_READ = """## Everyone starts here

This book is a course. It was written as sixteen modules that expect to be read in order, and the
order matters more than the page count: Module 03 (NLP) lands very differently once you have met
attention in 02, and Module 08 (RAG) is mostly a list of good ideas until you know what a KV cache and
a reranker actually do.

If you are starting from zero, read **Part 0 — Launchpad** (fifteen minutes: how the track is built,
how to set up a Python environment, what "done" looks like) and then walk forward from Module 01. If
you already work with models and need one specific thing, jump: retrieval is Part 08, agents are Parts
06–07, prompt injection is Part 13, evals are Part 15, and shipping the thing sits in Part 16.

## What a part contains

| Chapter | What it is | How to use it |
|---|---|---|
| `n.1 Overview` | The module README: objectives ("you can X"), a suggested path with time estimates, the vocabulary you must own, and an **exit check** | Read it first. The exit check is the actual bar — if you can meet it without looking things up, skip the module. |
| `n.2 … Notes` | The teaching prose. First note: core concepts. Second: the deep dive or practitioner craft. Module 14 adds a third on building a compliance program. | Read with a terminal open. Every claim that matters has a number or a failure mode attached. |
| `Lab exercises` | Graded exercises with explicit deliverables and stated checks | Do them. Solutions are deliberately absent; the checks tell you when you are right. |
| `Code templates` (present in a few modules) | Markdown that ships next to the code: prompt patterns, a model-card template, IAM and guardrail examples, the `CLAUDE.md` and skill templates | Copy these rather than retyping them; each one is referenced from that module's notes or lab. |
| `Sources` | Primary papers, official docs, courses and repositories, annotated | Follow up on whichever one the notes made you doubt. |

Part 16 is the exception: it opens with the map of the AI tech stack and then gives you seven tracks
(16.1 Python, 16.2 TypeScript, 16.3 LangChain, 16.4 LangGraph, 16.5 LangSmith, 16.6 AWS Bedrock,
16.7 Claude Code and the Agent SDK). Each track has exactly the same shape as a module.

Part 99 — Capstone Projects gives you three build briefs with explicit non-goals and an evaluation
bar. Do one at the end, not before.

## Three conventions worth knowing

1. **Relative links become printed paths.** The markdown is full of `../08-rag/` style links, which
   print cannot follow. Where the target is another repository file, the path is printed next to the
   words, like `[Module 08's eval metrics] [08-rag/notes/02-advanced-patterns-and-evaluation.md]`.
   Real `https://` URLs stay clickable.
2. **Code is not echoed.** Each module ships runnable, heavily commented scripts in its `code/`
   folder, plus a slide deck in `slides/`. Neither is printed here; the lab chapters tell you which
   script to run for which exercise. Every script in the repository runs offline.
3. **Every chapter starts on a new page, and every page number is real.** The contents page was
   typeset from the same printed document you are holding, so a chapter's number in the contents is
   the page it begins on.

## The bar

Each module ends with an exit check, and each lab has stated deliverables. If you finish a module
without being able to produce its exit check, you have read about the module rather than learned it.
The capstones exist to catch exactly that: they need three or four modules at once, and they are graded
by whether the numbers they produce are trustworthy — not by whether the demo runs.
"""


# --------------------------------------------------------------------------------------
# book assembly
# --------------------------------------------------------------------------------------
def book_html(parts: list[Part], numbers: dict[str, int], pages: int,
              markers: bool = True) -> str:
    refresh_appendices(parts, pages)
    chapters = sum(len(p.chapters) for p in parts)
    body = [
        cover_html(parts, chapters, pages),
        ('<section class="front-page" style="--accent:#%s">'
         '<h1 class="page-title">About the author</h1><div class="page-rule"></div>%s</section>'
         % (FALLBACK_ACCENT, md_to_html(ABOUT_AUTHOR))),
        ('<section class="front-page" style="--accent:#%s">'
         '<h1 class="page-title">Why this book</h1><div class="page-rule"></div>%s</section>'
         % (FALLBACK_ACCENT, md_to_html(WHY_THIS_BOOK))),
        ('<section class="front-page" style="--accent:#%s">'
         '<h1 class="page-title">How to read this book</h1><div class="page-rule"></div>%s</section>'
         % (FALLBACK_ACCENT, md_to_html(HOW_TO_READ))),
        contents_html(parts, numbers),
    ]
    for part in parts:
        body.append(part_html(part, markers))
        for chapter in part.chapters:
            body.append(chapter_html(part, chapter, markers))
    head = ('<!doctype html><html><head><meta charset="utf-8">'
            f"<title>{esc(BOOK_TITLE)}</title><style>{CSS}</style></head><body>")
    return head + "".join(body) + "</body></html>"


# --------------------------------------------------------------------------------------
# chrome: one browser, printed as one document
# --------------------------------------------------------------------------------------
FOOTER_TEMPLATE = (
    '<div style="width:100%;font-family:Helvetica,Arial,sans-serif;font-size:9px;color:#8a8f9f;'
    'padding:0 0.78in;display:flex;justify-content:space-between;">'
    f"<span>{BOOK_TITLE}</span>"
    '<span>page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>'
)
BKMK_RE = re.compile(r"(?:BKMK|DIV)\d{4}")
# In the shipped PDF the marker keeps its element and metrics but loses its text, so pagination is
# identical while the text layer stays free of "BKMK0007" noise in copy-paste, search and screen
# readers.
BKMK_BLANK = '<span class="bkmk"> </span>'


def silence_chrome_trailer_noise() -> None:
    """Hide one pypdf warning that comes from Chrome, not from us.

    Chrome's PDF writer understates the trailer /Size by a handful of objects, so cloning the printed
    document logs 'Object count N exceeds defined trailer size M'. pypdf handles it, and the file this
    script writes back carries a correct /Size, so it is hand-off noise. Every other pypdf warning
    still reaches the console.
    """
    class _Filter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            return "exceeds defined trailer size" not in record.getMessage()

    noise_filter = _Filter()
    logging.lastResort.addFilter(noise_filter)
    for handler in logging.getLogger().handlers:
        handler.addFilter(noise_filter)


def free_port() -> int:
    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class ChromePrinter:
    """Drive headless Chrome over CDP so we get real page numbers in the footer."""

    def __init__(self, timeout: float = 1800.0) -> None:
        from websockets.sync.client import connect

        if not CHROME_BIN.exists():
            raise SystemExit(f"Google Chrome not found at {CHROME_BIN}\n"
                             "Install Chrome, or edit CHROME_BIN at the top of this script.")
        self.timeout = timeout
        self._profile = Path(tempfile.mkdtemp(prefix="build-book-chrome-"))
        self._port = free_port()
        self._proc = subprocess.Popen(
            [str(CHROME_BIN), "--headless=new", f"--remote-debugging-port={self._port}",
             f"--user-data-dir={self._profile}", "--no-first-run", "--no-default-browser-check",
             "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ws_url = self._page_ws_url()
        self._ws = connect(ws_url, max_size=1024 * 1024 * 1024, open_timeout=60)
        self._id = 0
        self._send("Page.enable")
        self._send("Runtime.enable")

    # -- plumbing -----------------------------------------------------------------
    def _page_ws_url(self) -> str:
        deadline = time.time() + 45
        while time.time() < deadline:
            try:
                json.load(urllib.request.urlopen(
                    f"http://127.0.0.1:{self._port}/json/version", timeout=2))
                break
            except Exception:
                time.sleep(0.25)
        else:
            raise SystemExit("Chrome never opened its DevTools port")
        tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{self._port}/json/list", timeout=10))
        for tab in tabs:
            if tab.get("type") == "page":
                return tab["webSocketDebuggerUrl"]
        req = urllib.request.Request(f"http://127.0.0.1:{self._port}/json/new?about:blank", method="PUT")
        return json.load(urllib.request.urlopen(req, timeout=10))["webSocketDebuggerUrl"]

    def _send(self, method: str, params: dict | None = None) -> dict:
        self._id += 1
        self._ws.send(json.dumps({"id": self._id, "method": method, "params": params or {}}))
        while True:
            raw = self._ws.recv(timeout=self.timeout)
            msg = json.loads(raw)
            if msg.get("id") == self._id:
                if "error" in msg:
                    raise RuntimeError(f"{method} failed: {msg['error']}")
                return msg.get("result", {})

    # -- printing -----------------------------------------------------------------
    def print_pdf(self, html_path: Path) -> bytes:
        self._send("Page.navigate", {"url": html_path.as_uri()})
        deadline = time.time() + 120
        while time.time() < deadline:
            state = self._send("Runtime.evaluate",
                               {"expression": "document.readyState", "returnByValue": True})
            if state.get("result", {}).get("value") == "complete":
                break
            time.sleep(0.1)
        time.sleep(0.35)                       # let the local fonts settle
        result = self._send("Page.printToPDF", {
            "printBackground": True,
            "preferCSSPageSize": True,
            "displayHeaderFooter": True,
            "headerTemplate": "<div></div>",
            "footerTemplate": FOOTER_TEMPLATE,
            "scale": 1,
            "transferMode": "ReturnAsBase64",
        })
        return base64.b64decode(result["data"])

    def close(self) -> None:
        try:
            self._ws.close()
        except Exception:
            pass
        self._proc.terminate()
        try:
            self._proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self._proc.kill()
        shutil.rmtree(self._profile, ignore_errors=True)


def page_texts(pdf_bytes: bytes):
    """Page text, one page at a time. pypdfium2 is ~10x faster than pypdf when installed."""
    try:
        import pypdfium2 as pdfium
    except ImportError:
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            yield page.extract_text() or ""
        return
    document = pdfium.PdfDocument(pdf_bytes)
    try:
        for page in document:
            textpage = page.get_textpage()
            try:
                yield textpage.get_text_range()
            finally:
                textpage.close()
    finally:
        document.close()


def detect_pages(pdf_bytes: bytes) -> tuple[dict[str, int], int]:
    """token -> first page it appears on, plus the page count."""
    found: dict[str, int] = {}
    count = 0
    for number, text in enumerate(page_texts(pdf_bytes), start=1):
        count = number
        for token in BKMK_RE.findall(text):
            found.setdefault(token, number)
    return found, count


def _wanted(name: str, only: list[str], extra: list[str] | None = None) -> bool:
    if not only:
        return True
    haystack = [name] + list(extra or [])
    return any(needle in hay or hay.startswith(needle) for needle in only for hay in haystack)


def track_order(folder: Path) -> tuple:
    """Sort tracks by their '16.3' style module number, not by folder name."""
    num = str(read_deck(folder).get("module") or "")
    digits = tuple(int(part) for part in re.findall(r"\d+", num))
    return (digits or (999,), folder.name)


def discover(only: list[str]) -> list[Part]:
    rows = load_module_rows()
    counter = [0]
    parts: list[Part] = []
    dirs = sorted((p for p in ROOT.iterdir() if p.is_dir() and re.match(r"^\d\d-", p.name)),
                  key=lambda p: p.name)
    for folder in dirs:
        if not _wanted(folder.name, only):
            continue
        part = make_part(folder, rows, is_track=False)
        fill_chapters(part, folder, counter)
        parts.append(part)
        tracks = folder / "tracks"
        if not tracks.is_dir():
            continue
        for track in sorted((t for t in tracks.iterdir() if t.is_dir()), key=track_order):
            track_num = str(read_deck(track).get("module") or track.name)
            if not _wanted(track.name, only, extra=[track_num, f"{folder.name}/{track.name}"]):
                continue
            tp = make_part(track, rows, is_track=True, num=track_num)
            fill_chapters(tp, track, counter)
            parts.append(tp)
        if len(part.chapters) == 1:
            # A part that owns tracks is a map of them rather than a chapter of its own: number
            # its overview 16.0 so the tracks keep the repo's 16.1.1 ... 16.7.5 scheme.
            part.chapters[0].label = f"{part.num}.0"
    if not only:
        parts.append(appendices_part(counter))
    for number, part in enumerate(parts, start=1):
        part.idx = number
    return parts


# --------------------------------------------------------------------------------------
# passes, splitting and the combined book
# --------------------------------------------------------------------------------------
def all_chapters(parts: list[Part]) -> list[Chapter]:
    return [chapter for part in parts for chapter in part.chapters]


def book_blocks(parts: list[Part]) -> list[tuple[str, Part, Chapter | None]]:
    """(marker, part, chapter) in document order: every part's divider, then its chapters."""
    blocks: list[tuple[str, Part, Chapter | None]] = []
    for part in parts:
        blocks.append((part.divider_mark, part, None))
        for chapter in part.chapters:
            blocks.append((chapter.bkmk, part, chapter))
    return blocks


def render_book(parts: list[Part], printer: ChromePrinter, html_out: Path) -> tuple[bytes, int]:
    """Print the book, re-print until the contents numbers match the layout, then measure ranges."""
    blocks = book_blocks(parts)
    numbers: dict[str, int] = {}
    detected: dict[str, int] = {}
    pages = 0
    data = b""
    for attempt in range(1, 5):
        html_out.write_text(book_html(parts, numbers, pages), encoding="utf-8")
        start = time.time()
        data = printer.print_pdf(html_out)
        printed = time.time() - start
        start = time.time()
        detected, pages = detect_pages(data)
        scanned = time.time() - start
        missing = [mark for mark, _, _ in blocks if mark not in detected]
        if missing:
            raise SystemExit(
                f"could not find {len(missing)} page marker(s): {missing[:4]}\n"
                "Dividers and chapters each start with an invisible 1px marker; if one is missing "
                "the contents page would be wrong, so this fails loudly instead.")
        for mark, part, chapter in blocks:
            if chapter is None:
                part.divider_page = detected[mark]
            else:
                chapter.start_page = detected[mark]
        fresh = {mark: detected[mark] for mark, _, _ in blocks}
        if attempt > 1 and fresh == numbers:
            print(f"  ✓ layout stable after {attempt} passes ({pages} pages)", flush=True)
            break
        moved = sum(1 for mark in numbers if numbers[mark] != fresh.get(mark))
        note = "measured divider and chapter starts" if attempt == 1 else f"{moved} block(s) moved"
        print(f"  · pass {attempt}: {pages} pages printed in {printed:.0f}s, "
              f"scanned in {scanned:.0f}s — {note}", flush=True)
        numbers = fresh
    else:
        print("  ! contents did not fully stabilise in 4 passes; using the last measurement",
              flush=True)
    starts = [detected[mark] for mark, _, _ in blocks]
    for i, (_, _, chapter) in enumerate(blocks):
        if chapter is None:
            continue
        chapter.end_page = (starts[i + 1] - 1) if i + 1 < len(starts) else pages

    # Fourth pass, no measuring markers: flip the last print to the marker-free variant. Same DOM,
    # same font metrics, only the glyphs inside each marker change, so the layout is the one we just
    # measured. The page count is checked anyway; if it ever did move we keep the measured print.
    html_out.write_text(book_html(parts, numbers, pages, markers=False), encoding="utf-8")
    clean = printer.print_pdf(html_out)
    clean_pages = len(pypdf.PdfReader(io.BytesIO(clean)).pages)
    if clean_pages == pages:
        data = clean
    else:
        print(f"  ! marker-free pass printed {clean_pages} pages, not {pages}; "
              "keeping the measured print", flush=True)
    return data, pages


def write_book(pdf_bytes: bytes, parts: list[Part], pages: int, path: Path) -> None:
    writer = pypdf.PdfWriter(clone_from=io.BytesIO(pdf_bytes))
    chapters = all_chapters(parts)
    writer.add_outline_item("Cover, how to read, contents", 0)
    for part in parts:
        parent = writer.add_outline_item(f"{part.label}: {part.title}",
                                         max(part.divider_page - 1, 0))
        for chapter in part.chapters:
            writer.add_outline_item(f"{chapter.label}  {chapter.title}",
                                    max(chapter.start_page - 1, 0), parent=parent)
    writer.add_metadata({
        "/Title": BOOK_TITLE,
        "/Author": AUTHOR_NAME,
        "/Subject": f"{len(parts)} parts, {len(chapters)} chapters, {pages} pages",
        "/Creator": "_tools/build_book.py (headless Chrome print-to-PDF)",
        "/Keywords": "; ".join(f.relative_to(ROOT).as_posix() for f in source_files(parts)),
    })
    with path.open("wb") as handle:
        writer.write(handle)


def write_chapters(pdf_bytes: bytes, parts: list[Part]) -> list[Path]:
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    written: list[Path] = []
    for part in parts:
        for chapter in part.chapters:
            writer = pypdf.PdfWriter()
            for page_number in range(chapter.start_page - 1, chapter.end_page):
                writer.add_page(reader.pages[page_number])
            writer.add_metadata({
                "/Title": f"{chapter.label}  {chapter.title}",
                "/Author": BOOK_TITLE,
                "/Subject": f"{part.label} — {part.title}",
                "/Creator": "_tools/build_book.py",
                "/Keywords": "; ".join(f.relative_to(ROOT).as_posix() for f in chapter.files),
            })
            name = f"{chapter.idx:03d}-{chapter.label}-{slugify(chapter.title)}.pdf"
            out_path = CHAPTERS_DIR / name
            with out_path.open("wb") as handle:
                writer.write(handle)
            written.append(out_path)
    return written


# --------------------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------------------
def main() -> int:
    args = sys.argv[1:]
    flags = {a for a in args if a.startswith("--")}
    allowed = {"--no-chapters", "--keep-html", "--no-clean", "--help"}
    if "--help" in flags:
        print(__doc__)
        return 0
    unknown = flags - allowed
    if unknown:
        print(f"unknown flag(s): {', '.join(sorted(unknown))}\n")
        print(__doc__)
        return 2
    only = [a for a in args if not a.startswith("--")]
    silence_chrome_trailer_noise()

    parts = discover(only)
    if not parts:
        print(f"no parts matched {only!r}")
        return 1
    chapters = all_chapters(parts)
    print(f"  · {len(parts)} part(s), {len(chapters)} chapter(s), "
          f"{len(source_files(parts))} source file(s)")

    OUT.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    if "--no-chapters" not in flags:
        if CHAPTERS_DIR.exists() and "--no-clean" not in flags:
            shutil.rmtree(CHAPTERS_DIR)
        CHAPTERS_DIR.mkdir(parents=True, exist_ok=True)

    html_out = BUILD_DIR / "book.html"
    printer = ChromePrinter()
    try:
        pdf_bytes, pages = render_book(parts, printer, html_out)
    finally:
        printer.close()

    book_path = OUT / f"{BOOK_TITLE.replace(' ', '-')}.pdf"
    write_book(pdf_bytes, parts, pages, book_path)
    print(f"  ✓ {book_path.relative_to(ROOT)}  {pages} pages, {len(chapters)} chapters")

    if "--no-chapters" not in flags:
        written = write_chapters(pdf_bytes, parts)
        biggest = max(written, key=lambda p: p.stat().st_size)
        print(f"  ✓ {CHAPTERS_DIR.relative_to(ROOT)}/  {len(written)} chapter PDFs "
              f"(largest: {biggest.name})")

    if "--keep-html" in flags:
        print(f"  · html kept at {html_out.relative_to(ROOT)}")
    else:
        html_out.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
