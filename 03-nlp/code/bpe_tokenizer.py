"""
Byte-Pair Encoding from scratch — the 150 lines that fix your intuition forever.

After running this you will understand why an LLM cannot count the r's in
"strawberry", why Hindi costs 4x more than English, and why a trailing space
changes your model's output.

    python code/bpe_tokenizer.py

Requires: nothing but the standard library.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

# A small corpus. Real tokenizers train on hundreds of GB; the algorithm is identical.
CORPUS = """
the quick brown fox jumps over the lazy dog. the dog barks and the fox runs.
tokenization is the process of converting text into tokens. a tokenizer maps
text to integers. tokenizers are trained on text. the tokenizer training
process merges frequent pairs. frequent pairs become single tokens. the
tokenization of rare words produces more tokens than common words. token
counts determine cost. cost determines what you can afford to send a model.
the model never sees characters, only tokens. this matters more than it sounds.
"""


# --------------------------------------------------------------------------- #
# Training                                                                     #
# --------------------------------------------------------------------------- #
def get_word_freqs(text: str) -> Counter:
    """Pre-tokenize on whitespace, marking word boundaries.

    The '</w>' end-of-word marker keeps 'dog' at the end of a word distinct
    from 'dog' inside 'dogma'. GPT-2-style byte-level BPE instead attaches a
    leading space to the token itself -- which is exactly why ' hello' and
    'hello' are DIFFERENT TOKENS and why a trailing space in your prompt can
    change the model's output.
    """
    return Counter(text.split())


def word_to_symbols(word: str) -> tuple[str, ...]:
    return tuple(word) + ("</w>",)


def count_pairs(splits: dict[tuple[str, ...], int]) -> Counter:
    pairs: Counter = Counter()
    for symbols, freq in splits.items():
        for a, b in zip(symbols, symbols[1:]):
            pairs[(a, b)] += freq
    return pairs


def merge_pair(pair: tuple[str, str], splits: dict) -> dict:
    a, b = pair
    merged = a + b
    out = {}
    for symbols, freq in splits.items():
        new, i = [], 0
        while i < len(symbols):
            if i < len(symbols) - 1 and symbols[i] == a and symbols[i + 1] == b:
                new.append(merged)
                i += 2
            else:
                new.append(symbols[i])
                i += 1
        out[tuple(new)] = freq
    return out


def train_bpe(text: str, num_merges: int = 120, verbose: bool = True):
    """The entire BPE algorithm: count pairs, merge the most frequent, repeat."""
    word_freqs = get_word_freqs(text)
    splits = {word_to_symbols(w): f for w, f in word_freqs.items()}

    vocab = set()
    for symbols in splits:
        vocab.update(symbols)

    merges: list[tuple[str, str]] = []
    for step in range(num_merges):
        pairs = count_pairs(splits)
        if not pairs:
            break
        best, freq = pairs.most_common(1)[0]
        if freq < 2:                     # nothing left worth merging
            break
        splits = merge_pair(best, splits)
        merges.append(best)
        vocab.add(best[0] + best[1])
        if verbose and step < 12:
            print(f"  merge {step:>3}: {best[0]!r} + {best[1]!r} -> {best[0] + best[1]!r}   (seen {freq}x)")
    if verbose:
        print(f"  ... {len(merges)} merges total, vocabulary of {len(vocab)} symbols")
    return merges, sorted(vocab)


# --------------------------------------------------------------------------- #
# Encoding / decoding                                                          #
# --------------------------------------------------------------------------- #
class BPETokenizer:
    def __init__(self, merges: list[tuple[str, str]], vocab: list[str]):
        self.merges = merges
        self.ranks = {pair: i for i, pair in enumerate(merges)}   # lower rank = merged earlier
        self.vocab = vocab
        self.stoi = {s: i for i, s in enumerate(vocab)}
        self.itos = {i: s for s, i in self.stoi.items()}

    def tokenize_word(self, word: str) -> list[str]:
        symbols = list(word_to_symbols(word))
        while len(symbols) > 1:
            # Apply the highest-priority (earliest-learned) merge available.
            candidates = [(self.ranks[p], i) for i, p in
                          enumerate(zip(symbols, symbols[1:])) if p in self.ranks]
            if not candidates:
                break
            _, i = min(candidates)
            symbols[i:i + 2] = [symbols[i] + symbols[i + 1]]
        return symbols

    def tokenize(self, text: str) -> list[str]:
        out: list[str] = []
        for w in text.split():
            out.extend(self.tokenize_word(w))
        return out

    def encode(self, text: str) -> list[int]:
        # Unknown symbols fall back to -1 here; real byte-level BPE can never
        # produce an unknown because every byte is in the base vocabulary.
        return [self.stoi.get(t, -1) for t in self.tokenize(text)]

    def decode(self, ids: list[int]) -> str:
        toks = [self.itos.get(i, "<unk>") for i in ids]
        return "".join(toks).replace("</w>", " ").strip()


# --------------------------------------------------------------------------- #
# Demos                                                                        #
# --------------------------------------------------------------------------- #
def rule(t):
    print("\n" + "=" * 72 + f"\n{t}\n" + "=" * 72)


def main() -> None:
    rule("1. TRAINING BPE  (watch the merges: characters -> pieces -> whole words)")
    merges, vocab = train_bpe(CORPUS, num_merges=150)
    tok = BPETokenizer(merges, vocab)

    rule("2. COMMON vs RARE WORDS")
    for w in ["the", "token", "tokenization", "tokenizer", "antidisestablishmentarianism", "xyzzy"]:
        pieces = tok.tokenize_word(w)
        print(f"  {w:<32} -> {len(pieces):>2} tokens  {pieces}")
    print("\n  Words the tokenizer saw often collapse to one token.")
    print("  Rare words shatter into pieces -- and cost proportionally more.")

    rule("3. WHY THE MODEL CANNOT COUNT LETTERS")
    for w in ["strawberry", "raspberry"]:
        pieces = tok.tokenize_word(w)
        print(f"  {w!r} -> {pieces}")
    print("\n  The model never receives the letter 'r'. It receives opaque integer")
    print("  IDs for multi-character chunks. Asking it to count letters is like")
    print("  asking you to count the pixels in a word you read at a glance.")

    rule("4. WHITESPACE IS PART OF THE TOKEN  (what OUR toy loses)")
    print(f"  ours: tokenize('dog')  -> {tok.tokenize('dog')}")
    print(f"  ours: tokenize(' dog') -> {tok.tokenize(' dog')}")
    print("  Identical -- because our pre-tokenizer calls .split() and throws")
    print("  whitespace away. That is a simplification, and it hides a real problem.")
    print()
    print("  Byte-level BPE (GPT-2 onward) does NOT throw it away. It encodes the")
    print("  leading space into the token itself, so with cl100k_base:")
    print("      'dog'  -> [18964]              one token, no space")
    print("      ' dog' -> [5679]               a DIFFERENT single token, with space")
    print("      'dog ' -> [18964, 220]         the trailing space is its own token")
    print()
    print("  Consequence: a prompt ending in a space forces the model to continue")
    print("  from a token boundary it almost never saw in training, and quality drops.")
    print("  Practical rule: never end a prompt with a trailing space before a completion.")
    print("  Verify it yourself with the tiktoken command at the end of this script.")

    rule("5. ROUND TRIP")
    s = "the tokenizer maps text to integers"
    ids = tok.encode(s)
    print(f"  text    : {s}")
    print(f"  tokens  : {tok.tokenize(s)}")
    print(f"  ids     : {ids}")
    print(f"  decoded : {tok.decode(ids)!r}")

    rule("6. COMPRESSION RATIO  (chars per token)")
    samples = {
        "English prose": "the quick brown fox jumps over the lazy dog",
        "Repeated common words": "the the the the the dog dog dog",
        "Rare/technical": "heteroskedasticity autoregressive quantization",
        "Digits": "3141592653589793238462643383279",
        "Code-ish": "def f(x): return x**2 + 1",
    }
    print(f"  {'sample':<24} {'chars':>6} {'tokens':>7} {'chars/token':>12}")
    for name, s in samples.items():
        n = len(tok.tokenize(s))
        print(f"  {name:<24} {len(s):>6} {n:>7} {len(s)/max(n,1):>12.2f}")
    print("\n  Higher chars/token = cheaper. This is why an English-trained")
    print("  vocabulary makes other languages 2-5x more expensive to serve,")
    print("  and why digits are pathologically expensive.")

    rule("7. VOCABULARY SIZE IS A TRADE-OFF")
    for n_merges in (10, 40, 100, 300):
        m, v = train_bpe(CORPUS, num_merges=n_merges, verbose=False)
        t2 = BPETokenizer(m, v)
        seq = len(t2.tokenize(CORPUS))
        print(f"  merges={n_merges:>4}  vocab={len(v):>4}  corpus encodes to {seq:>5} tokens")
    print("\n  Bigger vocabulary -> shorter sequences (cheaper attention, O(n^2))")
    print("                    -> bigger embedding + output matrices (more parameters)")
    print("  Real models land at 32k-256k. It is a genuine engineering trade-off.")

    out = Path(__file__).with_name("bpe_merges.json")
    out.write_text(json.dumps({"merges": [list(m) for m in merges],
                               "vocab_size": len(vocab)}, indent=2))
    print(f"\nSaved learned merges to {out.name}")
    print("\nNow compare against a real tokenizer:")
    print("  pip install tiktoken")
    print("  python -c \"import tiktoken; e=tiktoken.get_encoding('cl100k_base');"
          " print(e.encode('strawberry'), [e.decode([t]) for t in e.encode('strawberry')])\"")


if __name__ == "__main__":
    main()
