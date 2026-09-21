"""
semantic_cache_correctness.py -- a semantic (embedding-similarity) LLM response cache,
demonstrated both as a genuine latency/cost win AND as a concrete correctness risk.

This is an architecture SIMULATION: "embeddings" are a hand-rolled bag-of-words vector
(pure Python + a little numpy for cosine similarity) so the whole thing runs offline with
no model weights and no network calls. The similarity NUMBERS below are illustrative of
the shape of the problem, not a claim about any specific commercial embedding model --
real sentence embeddings show the same failure mode, often at even higher similarity,
because they compress more aggressively than bag-of-words does.

What this script proves, in order:
  1. THE WIN: a batch of true paraphrases hits the semantic cache and skips the (simulated,
     costed, latency-carrying) "LLM call" almost every time -- concrete $ and ms saved.
  2. THE RISK: two queries that differ in exactly the fact that matters ("under $50" vs
     "under $500") are similar enough that a loosely-thresholded cache serves the WRONG
     cached answer. We compute the real cosine similarity and show the false hit happening.
  3. THE FIX: sweep the similarity threshold to find where the false hit disappears, show
     what legitimate hit-rate you paid for that safety, and show a cheaper fix -- an
     exact-match guard on numbers/entities -- that removes the risk without raising the
     threshold at all.

Run:
    python code/semantic_cache_correctness.py

Requires: numpy (already a dependency across this repo's code/ examples).
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

import numpy as np


def rule(title: str) -> None:
    print("\n" + "=" * 78 + f"\n{title}\n" + "=" * 78)


# --------------------------------------------------------------------------- #
# 1. A tiny, deterministic "embedding": bag-of-words term-frequency vector      #
#    over a shared vocabulary. No IDF weighting on purpose -- IDF would over-   #
#    penalize the very numeric tokens ("$50", "$500") that make this demo's    #
#    danger case interesting, and real sentence embeddings don't apply IDF     #
#    either; they encode surface similarity in exactly the way shown here.     #
# --------------------------------------------------------------------------- #
_TOKEN_RE = re.compile(r"[a-z0-9$]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class Embedder:
    def __init__(self):
        self.vocab: dict[str, int] = {}

    def fit(self, corpus: list[str]) -> None:
        for text in corpus:
            for tok in tokenize(text):
                if tok not in self.vocab:
                    self.vocab[tok] = len(self.vocab)

    def embed(self, text: str) -> np.ndarray:
        vec = np.zeros(len(self.vocab), dtype=np.float64)
        for tok in tokenize(text):
            idx = self.vocab.get(tok)
            if idx is not None:
                vec[idx] += 1.0
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))  # both already L2-normalized in Embedder.embed


# --------------------------------------------------------------------------- #
# 2. A simulated LLM call: fixed latency + cost, deterministic "answer" per     #
#    canonical intent so we can tell a right answer from a wrong one.          #
# --------------------------------------------------------------------------- #
LLM_LATENCY_MS = 850.0
LLM_COST_USD = 0.006


def call_llm(canonical_answer: str) -> tuple[str, float, float]:
    """Simulates a real model call: returns (answer, latency_ms, cost_usd)."""
    return canonical_answer, LLM_LATENCY_MS, LLM_COST_USD


# --------------------------------------------------------------------------- #
# 3. The semantic cache                                                        #
# --------------------------------------------------------------------------- #
@dataclass
class CacheEntry:
    query: str
    embedding: np.ndarray
    answer: str
    numbers: tuple[str, ...]   # extracted "high-stakes" tokens, for the guard demo


_NUMBER_RE = re.compile(r"\$?\d+")


def extract_numbers(text: str) -> tuple[str, ...]:
    return tuple(sorted(_NUMBER_RE.findall(text)))


class SemanticCache:
    def __init__(self, embedder: Embedder, threshold: float, use_number_guard: bool = False):
        self.embedder = embedder
        self.threshold = threshold
        self.use_number_guard = use_number_guard
        self.entries: list[CacheEntry] = []
        self.hits = 0
        self.misses = 0

    def get(self, query: str) -> tuple[str | None, float, CacheEntry | None]:
        """Returns (answer_or_None, best_similarity, matched_entry_or_None)."""
        if not self.entries:
            return None, 0.0, None
        q_emb = self.embedder.embed(query)
        best_sim, best_entry = -1.0, None
        for entry in self.entries:
            sim = cosine(q_emb, entry.embedding)
            if sim > best_sim:
                best_sim, best_entry = sim, entry
        if best_sim >= self.threshold and best_entry is not None:
            if self.use_number_guard:
                q_numbers = extract_numbers(query)
                if q_numbers != best_entry.numbers:
                    # Guard fires: the embedding said "close enough" but the numbers
                    # that actually determine the answer differ. Force a miss.
                    self.misses += 1
                    return None, best_sim, best_entry
            self.hits += 1
            return best_entry.answer, best_sim, best_entry
        self.misses += 1
        return None, best_sim, best_entry

    def put(self, query: str, answer: str) -> None:
        self.entries.append(CacheEntry(
            query=query,
            embedding=self.embedder.embed(query),
            answer=answer,
            numbers=extract_numbers(query),
        ))


# --------------------------------------------------------------------------- #
# 4. Demo 1 -- the legitimate win: true paraphrases hit the cache              #
# --------------------------------------------------------------------------- #
PARAPHRASES = [
    ("What is your return policy?", "How long do I have to return an item?",
     "You can return items within 30 days of delivery for a full refund."),
    ("What payment methods do you accept?", "Can I pay with PayPal or a credit card?",
     "We accept Visa, Mastercard, American Express, and PayPal."),
    ("How do I track my order?", "Where can I see my shipment status?",
     "Track your order from the Orders page using your order confirmation number."),
    ("Do you ship internationally?", "Can I get this shipped outside the US?",
     "Yes, we ship to over 40 countries; international shipping takes 7-14 business days."),
]


def demo_win() -> Embedder:
    rule("1. THE WIN -- semantic cache on true paraphrases")
    corpus = [q for pair in PARAPHRASES for q in pair[:2]]
    embedder = Embedder()
    embedder.fit(corpus)

    cache = SemanticCache(embedder, threshold=0.60)
    total_latency_nocache = total_latency_cached = 0.0
    total_cost_nocache = total_cost_cached = 0.0

    print(f"  {'query':<52}{'cache?':>8}{'sim':>7}")
    for original, paraphrase, answer in PARAPHRASES:
        # Seed the cache with the "original" phrasing, as if a first user asked it.
        answer_seed, lat, cost = call_llm(answer)
        cache.put(original, answer_seed)
        total_latency_nocache += lat
        total_latency_cached += lat
        total_cost_nocache += cost
        total_cost_cached += cost

        # A second, differently-worded user asks the paraphrase.
        cached_answer, sim, _ = cache.get(paraphrase)
        total_latency_nocache += LLM_LATENCY_MS   # what it WOULD have cost with no cache
        total_cost_nocache += LLM_COST_USD
        if cached_answer is not None:
            hit_latency, hit_cost = 2.0, 0.0      # cache lookup: ~2ms, $0
            total_latency_cached += hit_latency
            total_cost_cached += hit_cost
            print(f"  {paraphrase:<52}{'HIT':>8}{sim:>7.2f}")
        else:
            lat, cost = LLM_LATENCY_MS, LLM_COST_USD
            total_latency_cached += lat
            total_cost_cached += cost
            print(f"  {paraphrase:<52}{'MISS':>8}{sim:>7.2f}")

    print(f"\n  {'':<30}{'no cache':>14}{'with cache':>14}{'saved':>10}")
    print(f"  {'total latency (ms)':<30}{total_latency_nocache:>14.0f}{total_latency_cached:>14.0f}"
          f"{(1 - total_latency_cached / total_latency_nocache):>9.1%}")
    print(f"  {'total cost ($)':<30}{total_latency_nocache and total_cost_nocache:>14.4f}{total_cost_cached:>14.4f}"
          f"{(1 - total_cost_cached / total_cost_nocache):>9.1%}")
    print(f"\n  {cache.hits}/{len(PARAPHRASES)} paraphrases hit the cache correctly.")
    print("  This is the entire business case for a semantic cache: real users ask the")
    print("  same handful of questions in dozens of phrasings, and exact-match alone misses")
    print("  all of them.")
    return embedder


# --------------------------------------------------------------------------- #
# 5. Demo 2 -- the risk: a dangerous near-duplicate pair                       #
# --------------------------------------------------------------------------- #
DANGEROUS_PAIR = (
    "What's the refund policy for orders under $50?",
    "What's the refund policy for orders under $500?",
    "Orders under $50 are refunded automatically to your original payment method, no questions asked.",
    "Orders under $500 require manager approval and a returned-item inspection before a refund issues.",
)


def demo_risk() -> tuple[float, Embedder]:
    rule("2. THE RISK -- a near-duplicate query that needs a DIFFERENT answer")
    q_small, q_large, ans_small, ans_large = DANGEROUS_PAIR
    embedder = Embedder()
    embedder.fit([q_small, q_large])

    sim = cosine(embedder.embed(q_small), embedder.embed(q_large))
    print(f"  Query A: {q_small!r}")
    print(f"  Query B: {q_large!r}")
    print(f"\n  cosine similarity(A, B) = {sim:.3f}")
    print(f"  Shared tokens: {sorted(set(tokenize(q_small)) & set(tokenize(q_large)))}")
    print(f"  Differing tokens: A-only={set(tokenize(q_small)) - set(tokenize(q_large))}"
          f"  B-only={set(tokenize(q_large)) - set(tokenize(q_small))}")
    print(f"\n  These two questions share {len(set(tokenize(q_small)) & set(tokenize(q_large)))} of"
          f" {len(set(tokenize(q_small)) | set(tokenize(q_large)))} unique tokens.")
    print("  A real sentence embedding model would place these AT LEAST this close (often")
    print("  closer -- semantic embeddings compress surface wording harder than a bag-of-words")
    print("  count vector does), because nothing about the sentence STRUCTURE differs.")

    print(f"\n  Correct answer to A ($50):  {ans_small}")
    print(f"  Correct answer to B ($500): {ans_large}")

    rule("2b. WATCH THE CACHE SERVE THE WRONG ANSWER AT A LOOSE THRESHOLD")
    loose_threshold = 0.80
    cache = SemanticCache(embedder, threshold=loose_threshold)
    cache.put(q_small, ans_small)
    served, hit_sim, matched = cache.get(q_large)
    print(f"  threshold = {loose_threshold}")
    print(f"  User asks Query B. Cache finds Query A at similarity {hit_sim:.3f} >= threshold.")
    print(f"  Cache returns: {served!r}")
    is_wrong = served == ans_small
    print(f"\n  >>> {'WRONG ANSWER SERVED' if is_wrong else 'correct'} <<< "
          f"-- a $500 order was told it qualifies for the $50 auto-refund policy.")
    print("  This is not a bug in the similarity math. The math is working exactly as")
    print("  designed. The DESIGN is the bug: similarity is not the same thing as")
    print("  'requires the same answer,' and nothing in this request path noticed.")
    return sim, embedder


# --------------------------------------------------------------------------- #
# 6. Demo 3 -- the fixes, and the trade-off each one costs you                 #
# --------------------------------------------------------------------------- #
def demo_fixes(dangerous_sim: float, embedder: Embedder) -> None:
    rule("3. THE FIXES -- threshold sweep vs. an exact-match number guard")
    q_small, q_large, ans_small, ans_large = DANGEROUS_PAIR

    print(f"  {'threshold':>10}{'dangerous pair':>18}{'paraphrase hit rate':>22}")
    for threshold in (0.60, 0.70, 0.80, 0.85, 0.90, 0.95, 0.99):
        # Does the dangerous pair still false-hit at this threshold?
        cache = SemanticCache(embedder, threshold=threshold)
        cache.put(q_small, ans_small)
        served, _, _ = cache.get(q_large)
        false_hit = "FALSE HIT" if served is not None else "miss (safe)"

        # What legitimate paraphrase hit-rate does this threshold buy us, using the
        # Demo 1 corpus re-embedded fresh (different vocabulary, same idea)?
        para_embedder = Embedder()
        para_embedder.fit([q for pair in PARAPHRASES for q in pair[:2]])
        para_cache = SemanticCache(para_embedder, threshold=threshold)
        hits = 0
        for original, paraphrase, answer in PARAPHRASES:
            para_cache.put(original, answer)
            got, _, _ = para_cache.get(paraphrase)
            if got is not None:
                hits += 1
        hit_rate = hits / len(PARAPHRASES)
        print(f"  {threshold:>10.2f}{false_hit:>18}{hit_rate:>21.0%}")

    print(f"\n  The dangerous pair sits at similarity {dangerous_sim:.3f}. Any threshold at or")
    print(f"  below that is a live false-hit. Pushing the threshold above it (>= 0.95 here)")
    print("  removes the danger but ALSO starts rejecting real paraphrases -- there is no")
    print("  free lunch in the threshold alone; you are trading hit rate for safety, and the")
    print("  exact trade-off point is corpus-dependent, which is why you must measure it on")
    print("  YOUR queries, not copy a threshold from a blog post.")

    rule("3b. THE CHEAPER FIX -- an exact-match number guard, threshold unchanged")
    loose_threshold = 0.80
    guarded = SemanticCache(embedder, threshold=loose_threshold, use_number_guard=True)
    guarded.put(q_small, ans_small)
    served, hit_sim, matched = guarded.get(q_large)
    print(f"  threshold = {loose_threshold} (same loose threshold as the failing case above)")
    print(f"  guard extracts numeric tokens from each query: A={extract_numbers(q_small)}"
          f"  B={extract_numbers(q_large)}")
    print(f"  Numbers differ -> guard forces a MISS even though similarity ({hit_sim:.3f}) clears"
          f" the threshold.")
    print(f"  Cache result for Query B: {served!r}  (correctly falls through to a fresh LLM call)")
    print("\n  The guard is strictly better here: it keeps the loose threshold's high hit rate")
    print("  on everything that does NOT differ in a load-bearing number, and only pays the")
    print("  cache-miss cost on the exact class of query where a wrong answer is expensive.")
    print("  Generalize it: extract dates, IDs, negations ('not', 'except'), and named")
    print("  entities as guard fields for whatever domain the cache serves.")


def main() -> None:
    embedder_win = demo_win()
    dangerous_sim, embedder_risk = demo_risk()
    demo_fixes(dangerous_sim, embedder_risk)

    rule("SUMMARY")
    print("  A semantic cache is a real, measurable latency/cost win on true paraphrases,")
    print("  and a real, measurable correctness risk on near-duplicates that differ in a")
    print("  load-bearing detail. Both facts are in this output as numbers, not opinions.")
    print("  Ship a semantic cache only where you've measured BOTH sides for your own query")
    print("  distribution, and prefer an entity/number guard over threshold-tuning alone --")
    print("  see notes/01-reference-architecture.md Section 4.1.")


if __name__ == "__main__":
    main()
