"""
Chunking strategies for RAG -- fixed-size, recursive, sentence-window, and
document-structure-aware -- compared on a real multi-paragraph document.

The whole point of this file is to make one thing visceral: **the chunker is
where most RAG quality is won or lost**, and it is decided before a single
embedding is computed. A bad chunker sends a retriever off to fetch half a
fact; no reranker downstream can fix that, because the other half was never
retrieved.

Runs fully offline. No embedding API, no network call. The chunk-size sweep
uses scikit-learn's TfidfVectorizer as a deterministic, local stand-in for a
real embedding model -- see notes/01-retrieval-fundamentals.md for why a real
model changes the numbers but not the shape of the trade-off.

    python code/chunking_strategies.py

Requires: scikit-learn, numpy (see requirements.txt).
"""
from __future__ import annotations

import re
import textwrap

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# --------------------------------------------------------------------------- #
# A real multi-paragraph document, with one fact planted so its sentence      #
# straddles an unlucky fixed-size chunk boundary.                             #
# --------------------------------------------------------------------------- #
DOCUMENT = """
The printing press did not appear from nowhere. Woodblock printing had existed
in East Asia for centuries, and Europe already had paper, oil-based inks, and
the screw press used for wine and olives. What was missing was a fast way to
set arbitrary text using reusable pieces.

Johannes Gutenberg solved that problem in the city of Mainz. Around 1450 he
combined movable metal type, a durable oil-based ink, and a converted wine
press into a single workflow. The type itself was cast from a lead, tin, and
antimony alloy chosen because it melted at a manageable temperature, cast with
crisp edges, and resisted wear over thousands of impressions.

The Gutenberg Bible, completed around 1455, is the press's most famous product
and the first major book printed in Europe with movable type. Historians
estimate the print run at about 180 copies, split between paper and the more
expensive vellum, at a time when a single hand-copied Bible could take a
scribe more than a year to finish.

The Great Library of Alexandria, founded in the third century BCE and gone
centuries before Gutenberg was born, is a useful contrast. Ancient libraries
held knowledge in scrolls that were copied by hand, one at a time, so the
Library's estimated holdings of between four hundred thousand and seven
hundred thousand scrolls represented an almost unrepeatable concentration of
labor. A press changes that arithmetic completely.

Movable type spread from Mainz across Europe within decades. By 1500, printing
shops operated in more than 200 European cities, and total output is
estimated at roughly twenty million volumes for the fifteenth century alone.
Book prices fell, literacy became commercially useful rather than a clerical
luxury, and the standardization of spelling accelerated because a printed
edition, unlike a copied one, propagated a single fixed text to thousands of
readers at once.
""".strip()

# The fact we will track through every chunker. Chosen because its critical
# number ("four hundred thousand and seven hundred thousand") sits mid-clause
# -- exactly the kind of sentence a naive splitter cuts without noticing.
FACT_SENTENCE = (
    "the Library's estimated holdings of between four hundred thousand and "
    "seven hundred thousand scrolls represented an almost unrepeatable "
    "concentration of labor"
)


# --------------------------------------------------------------------------- #
# 1. Fixed-size chunking -- the naive baseline everyone starts with           #
# --------------------------------------------------------------------------- #
def fixed_size_chunk(text: str, chunk_size: int, overlap: int = 0) -> list[str]:
    """Slide a fixed character window across the text. No awareness of words,
    sentences, or structure -- it will happily cut a word or a number in half.
    This is `text[i:i+chunk_size]` with a step, nothing more."""
    text = re.sub(r"\s+", " ", text).strip()
    step = chunk_size - overlap
    if step <= 0:
        raise ValueError("overlap must be smaller than chunk_size")
    return [text[i:i + chunk_size] for i in range(0, len(text), step) if text[i:i + chunk_size]]


# --------------------------------------------------------------------------- #
# 2. Recursive chunking -- try the "nicest" separator first, fall back        #
# --------------------------------------------------------------------------- #
def recursive_chunk(text: str, chunk_size: int, overlap: int = 40,
                     separators: tuple[str, ...] = ("\n\n", ". ", " ")) -> list[str]:
    """Split on the first separator that gets every piece under chunk_size;
    only fall through to a coarser (more destructive) separator where it
    doesn't. This is the same idea as LangChain's RecursiveCharacterTextSplitter:
    prefer paragraph breaks, then sentence breaks, then whitespace, and only
    hit a hard character cut as an absolute last resort.

    Pieces are then greedily packed up to chunk_size with `overlap` characters
    of trailing context carried into the next chunk, so a reader who lands on
    chunk N+1 isn't missing the sentence that set it up.
    """
    def split_recursive(t: str, seps: tuple[str, ...]) -> list[str]:
        if len(t) <= chunk_size or not seps:
            return [t]
        sep, rest = seps[0], seps[1:]
        parts = [p for p in t.split(sep) if p]
        pieces: list[str] = []
        for p in parts:
            pieces.extend(split_recursive(p, rest) if len(p) > chunk_size else [p])
        return pieces

    atoms = split_recursive(text.strip(), separators)

    # Greedily pack atoms (sentences/paragraphs) into chunks near chunk_size,
    # never splitting an atom itself.
    chunks, current = [], ""
    for atom in atoms:
        candidate = (current + " " + atom).strip() if current else atom
        if len(candidate) > chunk_size and current:
            chunks.append(current)
            current = (current[-overlap:] + " " + atom).strip() if overlap else atom
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


# --------------------------------------------------------------------------- #
# 3. Sentence-window chunking -- retrieve small, return big                   #
# --------------------------------------------------------------------------- #
def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    # A deliberately simple splitter: good enough for prose without abbreviations
    # like "Dr." or "e.g." -- production systems use spaCy/nltk sentence splitters.
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def sentence_window_chunk(text: str, window: int = 1) -> list[dict]:
    """Each retrieval *unit* is a single whole sentence -- so a sentence is
    NEVER split, by construction, unlike fixed-size chunking. But each unit
    also carries a `window_text`: the anchor sentence plus `window` sentences
    of context on either side. You embed and search the anchor sentence
    (small, precise, high signal-to-noise) but hand the LLM the window
    (enough context to actually answer from). This is the same "small chunk
    to retrieve, big chunk to generate" idea used by parent-document retrieval
    -- see notes/02-advanced-patterns-and-evaluation.md.
    """
    sentences = split_sentences(text)
    out = []
    for i, s in enumerate(sentences):
        lo, hi = max(0, i - window), min(len(sentences), i + window + 1)
        out.append({
            "anchor_index": i,
            "anchor_text": s,
            "window_text": " ".join(sentences[lo:hi]),
        })
    return out


# --------------------------------------------------------------------------- #
# 4. Document-structure-aware chunking -- never cross a header boundary       #
# --------------------------------------------------------------------------- #
def structure_aware_chunk(markdown_text: str) -> list[dict]:
    """Split on Markdown headers. A section keeps its header as metadata, so a
    retrieved chunk always knows which part of the document it came from --
    invaluable for citation and for filtering by section (e.g. "only search
    the Troubleshooting section")."""
    lines = markdown_text.strip().splitlines()
    sections, current_header, current_body = [], "(preamble)", []
    for line in lines:
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            if current_body:
                sections.append({"header": current_header, "text": "\n".join(current_body).strip()})
            current_header, current_body = m.group(2), []
        else:
            current_body.append(line)
    if current_body:
        sections.append({"header": current_header, "text": "\n".join(current_body).strip()})
    return [s for s in sections if s["text"]]


# --------------------------------------------------------------------------- #
# Demo: the fact-splitting problem, concretely                                #
# --------------------------------------------------------------------------- #
def rule(title: str) -> None:
    print("\n" + "=" * 78 + f"\n{title}\n" + "=" * 78)


def show_chunk(i: int, text: str, width: int = 74) -> None:
    wrapped = textwrap.fill(text, width=width, initial_indent="    ", subsequent_indent="    ")
    print(f"  chunk {i}:\n{wrapped}")


def fact_is_intact(chunk_text: str) -> bool:
    """The fact survives a chunk boundary only if its full sentence appears,
    unbroken, inside a single chunk."""
    normalized = re.sub(r"\s+", " ", chunk_text)
    return FACT_SENTENCE in normalized


def demo_fact_splitting() -> None:
    clean_doc = re.sub(r"\s+", " ", DOCUMENT)
    fact_start = clean_doc.index(FACT_SENTENCE)
    fact_mid = fact_start + len(FACT_SENTENCE) // 2

    rule("1. FIXED-SIZE CHUNKING AT AN UNLUCKY BOUNDARY (chunk_size chosen to land mid-sentence)")
    # Choose a chunk_size whose boundary falls inside the fact sentence -- this
    # is the realistic case: you don't get to pick chunk_size around any one
    # fact, so SOME fact in SOME document always sits on an unlucky boundary.
    unlucky_size = fact_mid + 1
    fixed_chunks = fixed_size_chunk(DOCUMENT, chunk_size=unlucky_size, overlap=0)
    hit_idx = [i for i, c in enumerate(fixed_chunks) if FACT_SENTENCE[:20] in re.sub(r"\s+", " ", c)]
    print(f"  chunk_size={unlucky_size} chars, overlap=0 -> {len(fixed_chunks)} chunks")
    for i in (hit_idx[0], hit_idx[0] + 1) if hit_idx else (0, 1):
        if i < len(fixed_chunks):
            show_chunk(i, fixed_chunks[i])
    print(f"\n  Fact intact in a single chunk? {any(fact_is_intact(c) for c in fixed_chunks)}")
    print("  The number range 'between four hundred thousand and seven hundred")
    print("  thousand' is now split across two chunks. A retriever that fetches")
    print("  ONLY the second chunk will hand the model 'seven hundred thousand")
    print("  scrolls' with no idea it was ever a range starting at four hundred")
    print("  thousand -- a fact turned into a wrong fact, silently.")

    rule("2. RECURSIVE CHUNKING AT THE SAME NOMINAL SIZE -- SENTENCE SURVIVES")
    recursive_chunks = recursive_chunk(DOCUMENT, chunk_size=unlucky_size, overlap=40)
    print(f"  chunk_size~={unlucky_size} chars (soft target), overlap=40 -> {len(recursive_chunks)} chunks")
    intact = [c for c in recursive_chunks if fact_is_intact(c)]
    for i, c in enumerate(recursive_chunks):
        if fact_is_intact(c):
            show_chunk(i, c)
    print(f"\n  Fact intact in a single chunk? {bool(intact)}")
    print("  Recursive chunking never cuts inside a sentence: it packs whole")
    print("  sentences up to ~chunk_size and only falls back to a raw character")
    print("  cut if a single sentence is itself longer than chunk_size (rare).")

    rule("3. SENTENCE-WINDOW CHUNKING -- THE UNIT IS A WHOLE SENTENCE, ALWAYS")
    windows = sentence_window_chunk(DOCUMENT, window=1)
    anchor = next(w for w in windows if FACT_SENTENCE in re.sub(r"\s+", " ", w["anchor_text"]))
    print(f"  {len(windows)} sentence units total. Anchor sentence #{anchor['anchor_index']}:")
    show_chunk("anchor", anchor["anchor_text"])
    print("  Retrieval unit (embedded + searched) is the anchor above -- short,")
    print("  keyword-dense, easy for a similarity search to match precisely.")
    show_chunk("window (handed to the LLM)", anchor["window_text"])
    print("  What actually reaches the prompt is the WINDOW: the anchor plus its")
    print("  neighbors, so the fact's sentence and its surrounding context both")
    print("  survive -- you get the retrieval precision of a small chunk and the")
    print("  context completeness of a large one.")

    rule("4. DOCUMENT-STRUCTURE-AWARE CHUNKING -- NEVER CROSS A HEADER")
    markdown_doc = (
        "# The Printing Press\n\n## Origins\nWoodblock printing predates Gutenberg by centuries; "
        "Europe already had paper, ink, and the screw press.\n\n"
        "## Gutenberg's Contribution\n" + DOCUMENT.split("\n\n")[1] + "\n\n"
        "## Impact\n" + DOCUMENT.split("\n\n")[4]
    )
    sections = structure_aware_chunk(markdown_doc)
    for s in sections:
        print(f"  section '{s['header']}' -> {len(s['text'])} chars")
    print("\n  A chunk from '## Impact' can never accidentally absorb text that")
    print("  belongs to '## Origins' -- useful both for retrieval precision and")
    print("  for citing 'see the Impact section' instead of an opaque chunk id.")


# --------------------------------------------------------------------------- #
# Chunk-size sweep: a small labeled retrieval task                            #
# --------------------------------------------------------------------------- #
# Six mini-articles, each built the way real documents actually look: a fixed
# amount of generic boilerplate (shared vocabulary across every article, e.g.
# an "about this archive" preamble) wrapped around ONE keyword-dense answer
# sentence that a query targets. Total article length is held constant across
# the sweep -- only how it gets sliced into chunks changes -- so the sweep
# isolates the effect of chunk SIZE, not the effect of writing more content.
_FILLER_BLOCK = (
    "This section of the archive discusses a topic in the history of "
    "communication technology and its broader cultural effects over time. "
    "Readers interested in the general subject should consult the "
    "bibliography for further material on related developments and context. "
) * 4   # repeated to give large chunks real filler to be diluted by

_ANSWERS: dict[str, str] = {
    "gutenberg": "Gutenberg's movable-type press used a lead-tin-antimony "
                 "alloy cast at low temperature to produce durable reusable letterforms.",
    "alexandria": "The Library of Alexandria stored several hundred thousand "
                  "handwritten manuscripts collected from ships passing through the harbor.",
    "telegraph": "The electric telegraph used Morse code pulses over copper "
                 "wire to send messages across continents in minutes instead of weeks.",
    "papyrus": "Ancient Egyptian scribes manufactured papyrus by pressing "
               "layered reed strips into sheets that could be rolled into durable scrolls.",
    "codex": "The codex format replaced the scroll because bound pages "
             "allowed random access to any point in a text instead of sequential unrolling.",
    "radio": "Early radio broadcasts used amplitude modulation to carry "
             "voice and music through the air to any receiver tuned to the right frequency.",
}

# Every article = filler + answer + filler, so the answer sentence sits deep
# inside a sea of shared boilerplate, exactly like a real document's central
# claim surrounded by introduction and boilerplate on both sides.
ARTICLES: dict[str, str] = {
    name: f"{_FILLER_BLOCK.strip()} {answer} {_FILLER_BLOCK.strip()}"
    for name, answer in _ANSWERS.items()
}

QUERIES: list[tuple[str, str]] = [
    ("What alloy was used to cast Gutenberg's movable type?", "gutenberg"),
    ("How many manuscripts did the Library of Alexandria hold?", "alexandria"),
    ("What code did the electric telegraph use to send messages?", "telegraph"),
    ("How did Egyptian scribes manufacture papyrus sheets?", "papyrus"),
    ("Why did the codex format replace the scroll?", "codex"),
    ("What modulation did early radio broadcasts use?", "radio"),
]


def word_chunks(text: str, size: int) -> list[str]:
    words = text.split()
    return [" ".join(words[i:i + size]) for i in range(0, len(words), size)] or [text]


def run_chunk_size_sweep() -> None:
    rule("5. CHUNK-SIZE SWEEP -- A SMALL LABELED RETRIEVAL TASK")
    print("  6 articles (~330 words each: filler + one answer sentence + filler),")
    print("  6 queries, each targeting exactly one article's answer sentence.")
    print("  We chunk every article at a fixed word count, embed every chunk")
    print("  with TF-IDF, and retrieve the single nearest chunk per query.")
    print()
    print("  The metric that matters here is the MARGIN: the retrieved chunk's")
    print("  similarity score minus the best-scoring WRONG chunk's score. Top-1")
    print("  accuracy alone saturates at 100% on a toy task this clean -- margin")
    print("  is what shows the trade-off *before* it becomes an outright miss.\n")
    print(f"  {'chunk size (words)':>19} {'chunks total':>13} {'top-1 accuracy':>15} "
          f"{'avg margin':>11} {'avg chunk chars':>16}")

    for size in (10, 20, 40, 80, 100_000):
        chunk_records = []  # (article, chunk_text)
        for article, text in ARTICLES.items():
            for c in word_chunks(text, size):
                chunk_records.append((article, c))

        # use_idf=False on purpose: with idf on, the shared filler words get
        # near-zero weight (they appear in every chunk, so idf collapses them)
        # and the dilution effect this sweep exists to show would vanish into
        # the weighting scheme instead of the chunk boundaries. Plain
        # term-frequency cosine similarity is a closer proxy for how a real
        # embedding model behaves: it has no idea a word is "boilerplate", so
        # a big bag of shared filler really does drag the vector toward a
        # generic centroid and away from the query.
        vectorizer = TfidfVectorizer(use_idf=False, stop_words="english")
        chunk_texts = [c for _, c in chunk_records]
        chunk_vectors = vectorizer.fit_transform(chunk_texts)

        correct = 0
        margins = []
        for query, gold_article in QUERIES:
            q_vec = vectorizer.transform([query])
            sims = cosine_similarity(q_vec, chunk_vectors)[0]
            best_idx = int(np.argmax(sims))
            if chunk_records[best_idx][0] == gold_article:
                correct += 1
            gold_sims = [s for s, (a, _) in zip(sims, chunk_records) if a == gold_article]
            wrong_sims = [s for s, (a, _) in zip(sims, chunk_records) if a != gold_article]
            margins.append(max(gold_sims) - max(wrong_sims))

        accuracy = correct / len(QUERIES)
        avg_margin = float(np.mean(margins))
        avg_len = np.mean([len(c) for c in chunk_texts])
        size_label = "100000 (whole doc)" if size == 100_000 else str(size)
        print(f"  {size_label:>19} {len(chunk_records):>13} {accuracy:>14.0%} "
              f"{avg_margin:>11.3f} {avg_len:>16.0f}")

    print("\n  Reading the curve:")
    print("  - Margin falls steadily as chunk size grows: 0.46 at 10 words down")
    print("    to 0.05 at whole-document chunks. Every extra filler word pulls")
    print("    the chunk's normalized vector further from the query's precise")
    print("    keywords -- the SAME underlying content, just diluted by being")
    print("    bundled with more of its neighbors. Retrieval still finds the")
    print("    right document here (the task is clean), but a real corpus with")
    print("    hundreds of similar documents would start flipping to a wrong")
    print("    one well before the margin hits zero.")
    print("  - This is 'too large wastes tokens AND hurts precision': whole-doc")
    print("    chunking is both the least precise row above and the most")
    print("    expensive (10-30x the tokens of the small-chunk rows) per hit.")
    print("  - Margin keeps climbing as chunks shrink, which is exactly why")
    print("    teams are tempted to shrink chunks aggressively. Don't stop")
    print("    there: sections 1-2 above showed the other half of the trade-off")
    print("    -- an arbitrarily small FIXED-size chunk doesn't know where")
    print("    sentence boundaries are, so shrinking chunk_size only increases")
    print("    the odds that today's chunker cuts tomorrow's fact in half.")
    print("    High retrieval margin on a chunk that contains half a fact is")
    print("    worthless. The fix is boundary-respecting chunking (recursive,")
    print("    sentence-window, structure-aware) at a moderate size -- not an")
    print("    ever-smaller fixed-size chunk.")


def main() -> None:
    demo_fact_splitting()
    run_chunk_size_sweep()
    print("\nDone. See notes/01-retrieval-fundamentals.md section 3 for the")
    print("overlap discussion and when to reach for each strategy.")


if __name__ == "__main__":
    main()
