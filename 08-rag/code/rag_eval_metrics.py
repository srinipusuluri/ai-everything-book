"""
RAG evaluation metrics -- Recall@k, MRR, NDCG@k for retrieval quality, plus a
cheap, fully offline "RAGAS-style" faithfulness checker for the generated
answer. This is the file that answers: "the demo looks good, but how do you
actually know if it's good?"

Two halves, because RAG has two failure surfaces and one metric can never
cover both:

  1. RETRIEVAL metrics (this file, section 1-3) -- did we fetch the right
     evidence? Recall@k, MRR, and NDCG@k, implemented from their textbook
     definitions and cross-checked against hand-computed examples so you can
     trust the numbers, not just the code.

  2. GENERATION faithfulness (section 4-5) -- given that evidence, did the
     model's answer actually stick to it? Real RAGAS (Es et al., 2023) does
     this by asking an LLM to decompose the answer into atomic claims and
     verify each one against the context with an NLI-style judgment. That
     costs an LLM call per claim. What's implemented here is the offline,
     zero-cost proxy: per-sentence keyword + bigram overlap against the
     retrieved context. It is deliberately crude -- see the caveats in
     section 4 for exactly where it breaks -- but it demonstrates the same
     SHAPE of check you'd wire an LLM judge into, and it's a real thing
     teams reach for as a fast pre-filter before spending LLM-judge budget.

Runs fully offline. No embedding API, no network call, no LLM call.

    python code/rag_eval_metrics.py

Requires: only the Python standard library (re, math, collections). numpy is
imported solely for float formatting convenience and is optional -- if it's
missing the script still runs, so it degrades gracefully with no numpy at all.
"""
from __future__ import annotations

import math
import re
from collections import Counter

try:
    import numpy as np
    _HAVE_NUMPY = True
except ImportError:  # pragma: no cover -- offline fallback, see docstring
    _HAVE_NUMPY = False


def _mean(xs: list[float]) -> float:
    return (float(np.mean(xs)) if _HAVE_NUMPY else sum(xs) / len(xs)) if xs else 0.0


def rule(title: str) -> None:
    print("\n" + "=" * 78 + f"\n{title}\n" + "=" * 78)


# =========================================================================== #
# SECTION 1 -- Recall@k                                                       #
# =========================================================================== #
def recall_at_k(ranked_ids: list[str], relevant: dict[str, int], k: int) -> float:
    """Fraction of ALL relevant documents (any grade > 0) that appear
    anywhere in the top-k retrieved results.

        recall@k = |{relevant docs} ∩ {top-k retrieved}| / |{relevant docs}|

    Recall@k does not care about ORDER within the top-k, and it does not
    care about grade -- a grade-1 ("somewhat relevant") hit counts exactly
    the same as a grade-2 ("highly relevant") hit. That's its blind spot:
    a system that buries the one great document at rank k and surrounds it
    with four mediocre-but-technically-relevant ones scores identically to
    a system that puts the great document at rank 1. NDCG (section 3) is
    the metric that cares about order and grade; use them together.
    """
    total_relevant = sum(1 for grade in relevant.values() if grade > 0)
    if total_relevant == 0:
        return 0.0
    top_k = set(ranked_ids[:k])
    hit = sum(1 for doc_id, grade in relevant.items() if grade > 0 and doc_id in top_k)
    return hit / total_relevant


# =========================================================================== #
# SECTION 2 -- Mean Reciprocal Rank                                           #
# =========================================================================== #
def reciprocal_rank(ranked_ids: list[str], relevant: dict[str, int]) -> float:
    """1 / (rank of the FIRST relevant document), or 0.0 if none of the
    retrieved documents are relevant. Ranks are 1-indexed (the top result is
    rank 1) because that's the convention in every IR paper that reports it --
    an off-by-one here silently shifts every MRR you ever compute.

    MRR (the mean of this over queries) answers one narrow question well:
    "how far down the list does a user have to scroll before hitting
    something useful?" It is blind to everything after the first hit -- a
    system that retrieves the single best document at rank 1 and nothing
    else relevant scores a perfect 1.0, identical to a system that also
    retrieves every other relevant document right behind it. That is
    exactly the blind spot recall@k exists to cover; see the "metrics can
    disagree" demo below for a case built to make this concrete.
    """
    for rank, doc_id in enumerate(ranked_ids, start=1):
        if relevant.get(doc_id, 0) > 0:
            return 1.0 / rank
    return 0.0


# =========================================================================== #
# SECTION 3 -- NDCG@k                                                         #
# =========================================================================== #
def dcg_at_k(graded_relevances: list[int], k: int) -> float:
    """Discounted Cumulative Gain, using the graded-gain formulation from
    Burges et al. (2005) / the version used by every modern search-ranking
    paper (it's also what sklearn's ndcg_score computes):

        DCG@k = sum_{i=1}^{k}  (2^rel_i - 1) / log2(i + 1)

    `i` is the 1-indexed rank. Two design choices worth naming explicitly:
      - `2^rel - 1` (not plain `rel`) makes a grade-2 ("highly relevant")
        document worth 3x a grade-1 document, not 2x -- it exponentially
        rewards the BEST documents rather than scoring linearly. For binary
        relevance (rel in {0,1}) this collapses to plain `rel`, so it's a
        strict generalization, not a different metric.
      - `log2(i + 1)` (not `log2(i)`) so rank 1 divides by log2(2)=1, not
        log2(1)=0 -- the classic off-by-one that breaks a naive port of the
        formula from a paper that 1-indexes differently.
    """
    return sum(
        (2 ** rel - 1) / math.log2(i + 1)
        for i, rel in enumerate(graded_relevances[:k], start=1)
    )


def ndcg_at_k(ranked_ids: list[str], relevant: dict[str, int], k: int) -> float:
    """NDCG@k = DCG@k / IDCG@k, where IDCG@k ("ideal DCG") is the DCG of the
    best possible ordering: every known relevance grade, sorted descending,
    truncated to k. Normalizing by IDCG is what makes NDCG comparable ACROSS
    queries that have different numbers of relevant documents or different
    maximum grades -- raw DCG is not comparable across queries at all.

    Returns 0.0 for a query with no relevant documents (IDCG would be 0;
    treated as "undefined, contributes nothing" rather than raising).
    """
    actual_grades = [relevant.get(doc_id, 0) for doc_id in ranked_ids[:k]]
    dcg = dcg_at_k(actual_grades, k)

    ideal_grades = sorted(relevant.values(), reverse=True)
    idcg = dcg_at_k(ideal_grades, k)

    return dcg / idcg if idcg > 0 else 0.0


# =========================================================================== #
# Self-check: verify every formula above against a hand-computed example      #
# before trusting a single number the rest of this file prints.               #
# =========================================================================== #
def _self_check() -> None:
    rule("SELF-CHECK -- verifying formulas against hand-computed values")

    # --- Recall@k, worked by hand -------------------------------------- #
    # relevant = {A:2, B:1, C:1} (3 relevant docs), ranked = [X, A, Y, B, Z]
    # top-3 = {X, A, Y} -> contains only A -> recall@3 = 1/3
    ranked = ["X", "A", "Y", "B", "Z"]
    relevant = {"A": 2, "B": 1, "C": 1}
    got = recall_at_k(ranked, relevant, k=3)
    expected = 1 / 3
    assert abs(got - expected) < 1e-9, f"recall@3 expected {expected}, got {got}"
    print(f"  recall@3([X,A,Y,B,Z], relevant={{A,B,C}}) = {got:.4f}  (hand-calc: 1/3)  OK")

    # --- MRR, worked by hand --------------------------------------------#
    # first relevant doc (A) is at rank 2 -> RR = 1/2
    got = reciprocal_rank(ranked, relevant)
    assert abs(got - 0.5) < 1e-9, f"RR expected 0.5, got {got}"
    print(f"  reciprocal_rank(...) = {got:.4f}  (hand-calc: 1/2, first hit at rank 2)  OK")

    # RR is 0.0 when nothing retrieved is relevant
    got_zero = reciprocal_rank(["P", "Q", "R"], relevant)
    assert got_zero == 0.0
    print(f"  reciprocal_rank(no hits) = {got_zero:.4f}  (hand-calc: 0.0)  OK")

    # --- NDCG@3, worked by hand ------------------------------------------#
    # ranked relevances (in retrieved order) = [2, 1, 0]
    # DCG@3 = (2^2-1)/log2(2) + (2^1-1)/log2(3) + (2^0-1)/log2(4)
    #       =    3/1          +    1/1.58496    +    0/2
    #       =    3.0          +    0.630930     +    0
    #       =    3.630930
    dcg = dcg_at_k([2, 1, 0], 3)
    assert abs(dcg - 3.630930) < 1e-5, f"DCG@3 expected 3.630930, got {dcg}"
    print(f"  dcg_at_k([2,1,0], 3) = {dcg:.6f}  (hand-calc: 3.630930)  OK")

    # IDCG@3: sorted grades from {A:2, B:1, C:1} descending = [2,1,1]
    # IDCG@3 = 3/1 + 1/1.58496 + 1/2.0 = 3.0 + 0.630930 + 0.5 = 4.130930
    idcg = dcg_at_k(sorted(relevant.values(), reverse=True), 3)
    assert abs(idcg - 4.130930) < 1e-5, f"IDCG@3 expected 4.130930, got {idcg}"
    print(f"  ideal dcg_at_k([2,1,1], 3) = {idcg:.6f}  (hand-calc: 4.130930)  OK")

    # NDCG@3 for ranked=[X(0),A(2),Y(0),B(1),Z(0)] -> top3 grades [0,2,0]
    ndcg = ndcg_at_k(ranked, relevant, 3)
    expected_ndcg = dcg_at_k([0, 2, 0], 3) / idcg
    assert abs(ndcg - expected_ndcg) < 1e-9
    print(f"  ndcg_at_k([X,A,Y,B,Z], relevant, 3) = {ndcg:.4f}  (= DCG@3/IDCG@3)  OK")

    # A perfect ranking must score EXACTLY 1.0 -- if this fails, the
    # normalization is broken, full stop.
    perfect_order = sorted(relevant, key=lambda d: -relevant[d])  # ["A","B","C"] or ["A","C","B"]
    perfect_ndcg = ndcg_at_k(perfect_order, relevant, 3)
    assert abs(perfect_ndcg - 1.0) < 1e-9, f"perfect ranking must score 1.0, got {perfect_ndcg}"
    print(f"  ndcg_at_k(perfect ordering, relevant, 3) = {perfect_ndcg:.4f}  (must be exactly 1.0)  OK")

    print("\n  All formulas match their textbook definitions. Proceeding to the demo.")


# =========================================================================== #
# DEMO 1 -- two retrievers, five queries, graded relevance judgments          #
# =========================================================================== #
# 8 documents in a small support-doc corpus. Grades: 0 = not relevant
# (omitted docs default to 0), 1 = somewhat relevant, 2 = highly relevant --
# the standard 3-point scale used in most graded-relevance IR test sets.
QUERY_JUDGMENTS: dict[str, dict[str, int]] = {
    "Q1": {"d1": 2, "d2": 1, "d3": 1},
    "Q2": {"d4": 2},
    "Q3": {"d5": 1, "d6": 2},
    "Q4": {"d7": 2, "d8": 1, "d2": 1},
    "Q5": {"d3": 2},
}

# System A: a hybrid+rerank retriever (see hybrid_search_and_rerank.py) --
# relevant documents cluster near the top, roughly in grade order.
SYSTEM_A_RESULTS: dict[str, list[str]] = {
    "Q1": ["d1", "d2", "d3", "d5", "d7"],
    "Q2": ["d4", "d1", "d2", "d3", "d5"],
    "Q3": ["d1", "d6", "d5", "d2", "d3"],
    "Q4": ["d2", "d7", "d1", "d8", "d3"],
    "Q5": ["d1", "d2", "d3", "d4", "d5"],
}

# System B: lexical-only (BM25-alone), the way it looks when a query
# paraphrases and shares little vocabulary with the target doc -- see
# hybrid_search_and_rerank.py for exactly this failure mode. Relevant docs
# are buried late or missing from the retrieved list entirely.
SYSTEM_B_RESULTS: dict[str, list[str]] = {
    "Q1": ["d4", "d5", "d1", "d6", "d2"],
    "Q2": ["d1", "d2", "d3", "d5", "d4"],
    "Q3": ["d1", "d2", "d3", "d4", "d5"],
    "Q4": ["d1", "d3", "d4", "d5", "d6"],
    "Q5": ["d1", "d2", "d4", "d5", "d6"],
}


def evaluate_system(results: dict[str, list[str]], k: int) -> dict[str, float]:
    recalls, rrs, ndcgs = [], [], []
    for qid, ranked in results.items():
        relevant = QUERY_JUDGMENTS[qid]
        recalls.append(recall_at_k(ranked, relevant, k))
        rrs.append(reciprocal_rank(ranked, relevant))
        ndcgs.append(ndcg_at_k(ranked, relevant, k))
    return {
        f"recall@{k}": _mean(recalls),
        "mrr": _mean(rrs),
        f"ndcg@{k}": _mean(ndcgs),
    }


def demo_retrieval_metrics() -> None:
    rule("DEMO 1 -- Recall@k / MRR / NDCG@k over 5 queries, two retrievers")
    print("  5 queries against an 8-doc corpus, graded relevance {0,1,2}.")
    print("  System A = hybrid+rerank-style (relevant docs near the top).")
    print("  System B = lexical-only-style (relevant docs buried or missed).\n")

    k = 3
    metrics_a = evaluate_system(SYSTEM_A_RESULTS, k)
    metrics_b = evaluate_system(SYSTEM_B_RESULTS, k)

    print(f"  {'system':<10} {f'recall@{k}':>10} {'mrr':>8} {f'ndcg@{k}':>9}")
    for name, m in (("System A", metrics_a), ("System B", metrics_b)):
        print(f"  {name:<10} {m[f'recall@{k}']:>10.3f} {m['mrr']:>8.3f} {m[f'ndcg@{k}']:>9.3f}")

    print("\n  Per-query breakdown for System A (where the metrics tell different stories):")
    print(f"  {'query':<6} {f'recall@{k}':>10} {'rr':>6} {f'ndcg@{k}':>9}")
    for qid, ranked in SYSTEM_A_RESULTS.items():
        relevant = QUERY_JUDGMENTS[qid]
        r = recall_at_k(ranked, relevant, k)
        rr = reciprocal_rank(ranked, relevant)
        n = ndcg_at_k(ranked, relevant, k)
        print(f"  {qid:<6} {r:>10.3f} {rr:>6.3f} {n:>9.3f}")
    print("  Q3: recall@3=1.0 (both relevant docs made the top-3) but MRR=0.500")
    print("  (the first hit landed at rank 2, not rank 1) -- recall alone would")
    print("  have told you Q3 went perfectly; it did not quite.")


# =========================================================================== #
# DEMO 2 -- a case built so recall@k and MRR flatly disagree on which         #
# system is "better", to make the blind spot in section 1/2 concrete          #
# =========================================================================== #
def demo_metrics_can_disagree() -> None:
    rule("DEMO 2 -- recall@k and MRR can rank two systems in OPPOSITE order")
    relevant = {"rX": 2, "rY": 2, "rZ": 2}  # 3 equally highly-relevant docs

    # Narrow: nails the single best-matching doc at rank 1, misses the other two.
    narrow = ["rX", "n1", "n2", "n3", "n4"]
    # Broad: finds all three relevant docs, but not until ranks 2-4.
    broad = ["n1", "rX", "rY", "rZ", "n2"]

    k = 5
    print(f"  relevant = {{rX:2, rY:2, rZ:2}}  (3 highly-relevant docs), k={k}\n")
    for name, ranked in (("Narrow", narrow), ("Broad ", broad)):
        r = recall_at_k(ranked, relevant, k)
        rr = reciprocal_rank(ranked, relevant)
        n = ndcg_at_k(ranked, relevant, k)
        print(f"  {name}: ranked={ranked}")
        print(f"          recall@{k}={r:.3f}   mrr={rr:.3f}   ndcg@{k}={n:.3f}")

    print("\n  Narrow WINS on MRR (1.0 vs 0.5) -- it put a relevant doc at rank 1.")
    print("  Broad  WINS on recall@5 (1.0 vs 0.33) -- it surfaced everything relevant.")
    print("  Neither number is 'wrong'; they measure different things. Report both,")
    print("  and know which one your product actually needs: a single-answer QA bot")
    print("  cares about MRR (only the first hit reaches the prompt if you rerank")
    print("  hard and truncate); a summarization-over-many-docs use case cares about")
    print("  recall (missing one of three relevant docs silently truncates the")
    print("  summary). NDCG is the compromise metric when you can't pick one.")


# =========================================================================== #
# SECTION 4 -- offline faithfulness checker (a RAGAS-style proxy)             #
# =========================================================================== #
_STOPWORDS = frozenset("""
a an the is are was were be been being this that these those to of in on for
with and or but if as by at from it its your you we our their his her they
not no can will would should could may might do does did have has had than
""".split())


def _tokens(text: str) -> list[str]:
    """Lowercase word/number tokens, punctuation stripped. Numbers are kept
    (not filtered as stopwords) on purpose: 'thirty days' vs 'forty-five
    days' must NOT count as overlapping just because both are 'days'."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _content_words(text: str) -> set[str]:
    return {t for t in _tokens(text) if t not in _STOPWORDS}


def _bigrams(text: str) -> set[tuple[str, str]]:
    toks = _tokens(text)  # keep stopwords here: bigrams encode local phrase
    return {(toks[i], toks[i + 1]) for i in range(len(toks) - 1)}


def _split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def sentence_support_score(sentence: str, context_chunks: list[str]) -> tuple[float, int]:
    """Score one sentence against every context chunk; return the best
    (score, chunk_index). The score blends two signals:

      - unigram coverage: fraction of the sentence's CONTENT words (stop-
        words removed) that appear anywhere in the chunk. Catches whether
        the topic and key entities/numbers are even present.
      - bigram Jaccard: overlap of adjacent word pairs, computed WITHOUT
        stopword removal, so it can see local phrase structure ("issued
        instead of" vs just the bag {issued, instead, of}). This is the
        (weak) stand-in for the fact that word ORDER carries meaning that
        a bag-of-words check throws away entirely.

    score = 0.6 * coverage + 0.4 * bigram_jaccard. The 0.6/0.4 split biases
    toward coverage (a paraphrase should still hit most content words) while
    still letting a sentence that shares a topic's vocabulary but rearranges
    it into a different claim ("full refund any time" vs "final sale, no
    returns") get penalized for near-zero bigram overlap.
    """
    s_words = _content_words(sentence)
    s_bigrams = _bigrams(sentence)
    best_score, best_idx = 0.0, -1
    for idx, chunk in enumerate(context_chunks):
        c_words = _content_words(chunk)
        c_bigrams = _bigrams(chunk)

        coverage = len(s_words & c_words) / len(s_words) if s_words else 0.0
        union = s_bigrams | c_bigrams
        bigram_jaccard = len(s_bigrams & c_bigrams) / len(union) if union else 0.0

        score = 0.6 * coverage + 0.4 * bigram_jaccard
        if score > best_score:
            best_score, best_idx = score, idx
    return best_score, best_idx


def check_faithfulness(answer: str, context_chunks: list[str],
                        threshold: float = 0.55) -> dict:
    """Split the answer into sentences and classify each as SUPPORTED or
    UNSUPPORTED by whichever context chunk scores it highest. Faithfulness
    is the fraction of sentences that are supported -- exactly the shape of
    RAGAS's faithfulness metric (supported claims / total claims), just with
    a lexical-overlap judge standing in for an LLM/NLI judge.

    CAVEATS -- read these before trusting this in a pipeline:
      - No negation handling. "The fee is $50" and "The fee is NOT $50"
        share almost every token and will score as strongly supporting each
        other. A real NLI judge distinguishes entailment from contradiction;
        this proxy cannot.
      - No true paraphrase detection. A faithful sentence written with
        completely different vocabulary than the context ("you're covered"
        for "eligible for a refund") can score UNSUPPORTED here even though
        an LLM judge would correctly call it faithful. This proxy trades
        recall of faithfulness for being free and instant.
      - It is a floor, not a ceiling: use it as a cheap pre-filter to catch
        egregious fabrication (invented numbers, invented policies) before
        spending LLM-judge budget on the harder semantic cases.
    """
    sentences = _split_sentences(answer)
    report = []
    for sentence in sentences:
        score, chunk_idx = sentence_support_score(sentence, context_chunks)
        supported = score >= threshold
        report.append({
            "sentence": sentence,
            "score": score,
            "supported": supported,
            "best_chunk": chunk_idx if chunk_idx >= 0 else None,
        })
    supported_count = sum(1 for r in report if r["supported"])
    faithfulness = supported_count / len(report) if report else 0.0
    return {"faithfulness": faithfulness, "sentences": report}


# =========================================================================== #
# DEMO 3 -- three answers over the same retrieved context: faithful,          #
# partially hallucinated, fully hallucinated                                 #
# =========================================================================== #
CONTEXT_CHUNKS = [
    "Standard returns are accepted within 30 days of the delivery date, "
    "provided the item is unused and in its original packaging.",
    "Store credit is issued instead of a refund when the original payment "
    "method can no longer be charged, such as an expired card.",
    "Electronics and opened software licenses are final sale and cannot be "
    "returned once the packaging seal is broken.",
]

QUESTION = "What is the return policy, and what happens if my card has expired?"

ANSWER_FAITHFUL = (
    "Standard returns are accepted within 30 days of delivery as long as the "
    "item is unused and in its original packaging. If your original payment "
    "card has expired, you will receive store credit instead of a refund. "
    "Electronics and opened software licenses are final sale once the "
    "packaging seal is broken."
)

ANSWER_PARTIAL = (
    "Standard returns are accepted within 30 days of delivery as long as the "
    "item is unused and in its original packaging. Electronics and opened "
    "software licenses are final sale once the packaging seal is broken. "
    "Returns made after the 30-day window are still accepted if you pay a "
    "15 percent restocking fee."
)

ANSWER_UNFAITHFUL = (
    "You can return any item at any time for a full refund, no questions "
    "asked. International shipping is free on all orders over fifty "
    "dollars. Our customer service team is available 24 hours a day by "
    "phone."
)


def demo_faithfulness() -> None:
    rule("DEMO 3 -- faithfulness checking: faithful vs partially vs fully hallucinated")
    print(f"  Question: {QUESTION}\n")
    print("  Retrieved context:")
    for i, c in enumerate(CONTEXT_CHUNKS):
        print(f"    [{i}] {c}")

    for label, answer in (
        ("FAITHFUL", ANSWER_FAITHFUL),
        ("PARTIAL (one fabricated sentence)", ANSWER_PARTIAL),
        ("UNFAITHFUL (fully hallucinated)", ANSWER_UNFAITHFUL),
    ):
        result = check_faithfulness(answer, CONTEXT_CHUNKS)
        print(f"\n  --- {label} --- faithfulness = {result['faithfulness']:.2f} "
              f"({sum(r['supported'] for r in result['sentences'])}/"
              f"{len(result['sentences'])} sentences supported)")
        for r in result["sentences"]:
            verdict = "SUPPORTED  " if r["supported"] else "UNSUPPORTED"
            chunk_ref = f"chunk[{r['best_chunk']}]" if r["best_chunk"] is not None else "no match"
            text = r["sentence"] if len(r["sentence"]) <= 66 else r["sentence"][:63] + "..."
            print(f"    {verdict}  score={r['score']:.2f}  {chunk_ref:<10}  {text}")

    print("\n  Faithfulness scores fall in the expected order (1.00 > 0.67 > 0.00)")
    print("  because the fabricated sentences share almost no content words or")
    print("  local phrasing with any retrieved chunk -- 'restocking fee' and")
    print("  'free international shipping' simply are not in the context, so no")
    print("  chunk can cover them no matter how the overlap threshold is tuned.")
    print("  A real RAGAS faithfulness run replaces sentence_support_score with an")
    print("  LLM call per decomposed claim; the SHAPE of the check -- decompose,")
    print("  verify each piece against context, average -- is identical. See")
    print("  notes/02-advanced-patterns-and-evaluation.md and ../../15-ai-evals/.")


def main() -> None:
    _self_check()
    demo_retrieval_metrics()
    demo_metrics_can_disagree()
    demo_faithfulness()
    print("\nDone. Retrieval metrics answer 'did we fetch the right evidence?';")
    print("faithfulness answers 'did the model stick to it?'. A RAG system can")
    print("fail either half independently -- measure both, always.")


if __name__ == "__main__":
    main()
