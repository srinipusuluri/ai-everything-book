"""
Decoding strategies, felt rather than read.

Uses a tiny character-level bigram model trained on a text sample -- small enough
to be instant, real enough that temperature and top-p visibly change the output.

    python code/sampling_strategies.py

Requires: numpy
"""
from __future__ import annotations

import numpy as np

rng = np.random.default_rng(42)

TEXT = (
    "the quick brown fox jumps over the lazy dog. the dog sleeps in the sun. "
    "the fox runs through the forest and the dog follows the fox. "
    "a quick fox is a happy fox. the lazy dog is a happy dog. "
    "the sun sets over the forest and the fox sleeps. the quick dog runs. "
    "the forest is quiet and the sun is warm and the dog dreams of the fox. "
) * 12


def rule(t: str) -> None:
    print("\n" + "=" * 74 + f"\n{t}\n" + "=" * 74)


# --------------------------------------------------------------------------- #
# A minimal "language model": character bigram counts                          #
# --------------------------------------------------------------------------- #
class BigramLM:
    def __init__(self, text: str, smoothing: float = 0.1):
        self.chars = sorted(set(text))
        self.V = len(self.chars)
        self.stoi = {c: i for i, c in enumerate(self.chars)}
        self.itos = {i: c for c, i in self.stoi.items()}
        counts = np.full((self.V, self.V), smoothing)
        for a, b in zip(text, text[1:]):
            counts[self.stoi[a], self.stoi[b]] += 1
        # Store LOGITS, because that is what a real model gives you.
        self.logits = np.log(counts)

    def next_logits(self, ch: str) -> np.ndarray:
        return self.logits[self.stoi.get(ch, 0)].copy()


# --------------------------------------------------------------------------- #
# The decoding pipeline, step by step                                          #
# --------------------------------------------------------------------------- #
def softmax(z):
    z = z - z.max()
    e = np.exp(z)
    return e / e.sum()


def apply_temperature(logits, T):
    if T <= 1e-6:                     # T -> 0 is greedy: a one-hot at the argmax
        out = np.full_like(logits, -np.inf)
        out[logits.argmax()] = 0.0
        return out
    return logits / T


def top_k_filter(logits, k):
    if k is None or k >= len(logits):
        return logits
    cut = np.partition(logits, -k)[-k]
    return np.where(logits >= cut, logits, -np.inf)


def top_p_filter(logits, p):
    """Nucleus sampling: keep the smallest set whose cumulative probability >= p."""
    if p is None or p >= 1.0:
        return logits
    probs = softmax(logits)
    order = np.argsort(-probs)
    cum = np.cumsum(probs[order])
    # Always keep at least the top token.
    keep_n = int(np.searchsorted(cum, p) + 1)
    keep = set(order[:keep_n].tolist())
    return np.array([l if i in keep else -np.inf for i, l in enumerate(logits)])


def min_p_filter(logits, min_p):
    """Keep tokens with prob >= min_p * p_max. Degrades more gracefully than top_p at high T."""
    if min_p is None:
        return logits
    probs = softmax(logits)
    return np.where(probs >= min_p * probs.max(), logits, -np.inf)


def repetition_penalty(logits, generated_ids, penalty):
    """Divide positive logits / multiply negative ones for tokens already seen."""
    if penalty is None or penalty == 1.0:
        return logits
    out = logits.copy()
    for i in set(generated_ids):
        out[i] = out[i] / penalty if out[i] > 0 else out[i] * penalty
    return out


def generate(lm, prompt="the ", n=90, T=1.0, top_k=None, top_p=None,
             min_p=None, rep_pen=None, seed=0):
    r = np.random.default_rng(seed)
    out = list(prompt)
    ids = [lm.stoi[c] for c in prompt if c in lm.stoi]
    for _ in range(n):
        logits = lm.next_logits(out[-1])
        logits = repetition_penalty(logits, ids[-12:], rep_pen)
        logits = apply_temperature(logits, T)
        logits = top_k_filter(logits, top_k)
        logits = top_p_filter(logits, top_p)
        logits = min_p_filter(logits, min_p)
        probs = softmax(logits)
        idx = int(r.choice(len(probs), p=probs))
        ids.append(idx)
        out.append(lm.itos[idx])
    return "".join(out)


# --------------------------------------------------------------------------- #
# Demos                                                                        #
# --------------------------------------------------------------------------- #
def main() -> None:
    lm = BigramLM(TEXT)

    rule("1. THE PIPELINE, ON ONE DISTRIBUTION")
    logits = lm.next_logits("t")
    print("  After 't', the top candidates in the raw distribution:")
    p = softmax(logits)
    for i in np.argsort(-p)[:6]:
        print(f"    {lm.itos[i]!r:>5}  p={p[i]:.4f}  logit={logits[i]:+.3f}")
    print("\n  Now watch temperature reshape it:")
    print(f"  {'T':>6}  {'top prob':>9}  {'entropy':>8}  {'effective choices':>18}")
    for T in (0.1, 0.5, 1.0, 1.5, 3.0):
        q = softmax(apply_temperature(logits, T))
        ent = float(-(q[q > 0] * np.log(q[q > 0])).sum())
        print(f"  {T:>6.1f}  {q.max():>9.4f}  {ent:>8.3f}  {np.exp(ent):>18.2f}")
    print("\n  'Effective choices' = exp(entropy). At T=0.1 the model has ~1 option;")
    print("  at T=3.0 it is choosing among many. That is the whole of temperature.")

    rule("2. TEMPERATURE, GENERATED")
    for T in (0.01, 0.3, 0.7, 1.0, 1.6, 2.5):
        s = generate(lm, T=T, n=72, seed=7).replace("\n", " ")
        print(f"  T={T:<5} {s}")
    print("\n  Low T: repetitive and safe. High T: novel and incoherent.")
    print("  There is no 'best' value -- there is a value that matches your task.")

    rule("3. TOP-K vs TOP-P: WHY ADAPTIVE WINS")
    for ch in ("t", "q", " "):
        pr = softmax(lm.next_logits(ch))
        n_for_90 = int(np.searchsorted(np.cumsum(np.sort(pr)[::-1]), 0.9) + 1)
        ent = float(-(pr[pr > 0] * np.log(pr[pr > 0])).sum())
        print(f"  after {ch!r}: entropy={ent:.3f}, tokens needed for 90% mass = {n_for_90}")
    print("\n  A fixed top_k=10 is too generous after a confident context and too")
    print("  stingy after an uncertain one. top_p adapts automatically. Use top_p.")

    rule("4. SAMPLING PRESETS SIDE BY SIDE")
    presets = [
        ("greedy (T=0)",            dict(T=0.01)),
        ("factual (T=0.2, p=0.9)",  dict(T=0.2, top_p=0.9)),
        ("balanced (T=0.7, p=0.95)", dict(T=0.7, top_p=0.95)),
        ("creative (T=1.1, p=0.95)", dict(T=1.1, top_p=0.95)),
        ("top_k=3",                 dict(T=1.0, top_k=3)),
        ("min_p=0.1 @ T=1.5",       dict(T=1.5, min_p=0.1)),
        ("no filter @ T=1.5",       dict(T=1.5)),
    ]
    for name, kw in presets:
        print(f"  {name:<26} {generate(lm, n=64, seed=3, **kw)}")
    print("\n  Compare the last two rows: min_p keeps high temperature usable by")
    print("  cutting the long tail of near-zero-probability garbage.")

    rule("5. THE REPETITION TRAP")
    print(f"  greedy, no penalty : {generate(lm, T=0.01, n=80, seed=1)}")
    print(f"  greedy, rep_pen 1.3: {generate(lm, T=0.01, n=80, rep_pen=1.3, seed=1)}")
    print("\n  Greedy decoding falls into a loop. The penalty breaks the tight loop --")
    print("  and then finds a LONGER one. That is exactly what happens in practice:")
    print("  repetition penalties move the degeneracy around rather than curing it.")
    print("  The real fix is sampling (T > 0) plus top_p.")
    print("  And NEVER use a repetition penalty for code or JSON: repeated identifiers,")
    print("  braces and quotes are required, and penalising them corrupts the output.")

    rule("6. DETERMINISM")
    a = generate(lm, T=0.01, n=50, seed=1)
    b = generate(lm, T=0.01, n=50, seed=99)
    c = generate(lm, T=0.9, n=50, seed=1)
    d = generate(lm, T=0.9, n=50, seed=99)
    print(f"  T=0.01, two different seeds -> identical? {a == b}")
    print(f"  T=0.9,  two different seeds -> identical? {c == d}")
    print("\n  Note the caveat for real systems: even at temperature 0, hosted models")
    print("  are not bit-reproducible. Batching, kernel selection and hardware change")
    print("  floating-point reduction order. Never write a test that asserts exact")
    print("  string equality against a hosted LLM. Assert properties instead.")

    rule("7. WHAT CONSTRAINED DECODING DOES")
    print("  Structured output works by masking logits so that only tokens VALID")
    print("  under a grammar can be sampled. Sketch:\n")
    print("      allowed = grammar.allowed_next_tokens(state)")
    print("      logits[~allowed] = -inf            # exactly what top_k does above")
    print("      token = sample(softmax(logits))")
    print("      state = grammar.advance(state, token)\n")
    print("  Malformed JSON stops being unlikely and becomes IMPOSSIBLE.")
    print("  Tools: Outlines, XGrammar, llama.cpp GBNF, and provider 'JSON mode'.")
    print("  If you parse model output in production, you should be using this.")


if __name__ == "__main__":
    main()
