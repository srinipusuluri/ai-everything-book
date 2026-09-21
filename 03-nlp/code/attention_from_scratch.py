"""
Self-attention and a full transformer block, in NumPy.

Nine demos that each prove one claim from notes/02-transformers.md:
  1. attention as a soft dictionary lookup
  2. why we divide by sqrt(d_k)          <- the interview question
  3. the causal mask
  4. multi-head attention
  5. attention is order-blind without positions
  6. sinusoidal vs RoPE positional encoding
  7. a complete Pre-LN transformer block
  8. tensor shapes and where the memory goes
  9. the KV cache, measured

    python code/attention_from_scratch.py

Requires: numpy
"""
from __future__ import annotations

import numpy as np

rng = np.random.default_rng(0)
np.set_printoptions(precision=3, suppress=True, linewidth=120)


def rule(t: str) -> None:
    print("\n" + "=" * 74 + f"\n{t}\n" + "=" * 74)


# --------------------------------------------------------------------------- #
# Core ops                                                                     #
# --------------------------------------------------------------------------- #
def softmax(x, axis=-1):
    x = x - x.max(axis=axis, keepdims=True)      # stability: never exp() a big number
    e = np.exp(x)
    return e / e.sum(axis=axis, keepdims=True)


def scaled_dot_product_attention(Q, K, V, mask=None, scale=True):
    """Attention(Q,K,V) = softmax(Q K^T / sqrt(d_k)) V

    Shapes: Q (..., n_q, d_k)  K (..., n_k, d_k)  V (..., n_k, d_v)
            -> out (..., n_q, d_v),  weights (..., n_q, n_k)
    """
    d_k = Q.shape[-1]
    scores = Q @ np.swapaxes(K, -1, -2)
    if scale:
        scores = scores / np.sqrt(d_k)
    if mask is not None:
        # Add -inf BEFORE softmax. Zeroing weights AFTER softmax is wrong --
        # the surviving weights would no longer sum to 1.
        scores = np.where(mask, scores, -np.inf)
    weights = softmax(scores, axis=-1)
    return weights @ V, weights


def causal_mask(n: int) -> np.ndarray:
    """True where attention is ALLOWED: position i may see positions <= i."""
    return np.tril(np.ones((n, n), dtype=bool))


def layer_norm(x, eps=1e-5, gamma=None, beta=None):
    mu = x.mean(-1, keepdims=True)
    var = x.var(-1, keepdims=True)
    out = (x - mu) / np.sqrt(var + eps)
    if gamma is not None:
        out = out * gamma
    if beta is not None:
        out = out + beta
    return out


def gelu(x):
    return 0.5 * x * (1 + np.tanh(np.sqrt(2 / np.pi) * (x + 0.044715 * x ** 3)))


# --------------------------------------------------------------------------- #
# 1. Soft dictionary lookup                                                    #
# --------------------------------------------------------------------------- #
def demo_soft_lookup():
    rule("1. ATTENTION IS A SOFT DICTIONARY LOOKUP")
    # Four "records". Keys are one-hot-ish; values are what each record contributes.
    # Keys scaled up so the softmax is sharp enough to read; in a trained model
    # the learned projections produce exactly this kind of magnitude separation.
    K = np.eye(4) * 6.0
    V = np.array([[10., 0.], [20., 1.], [30., 2.], [40., 3.]])

    print("  A HARD lookup returns the value whose key matches exactly.")
    print("  Attention returns a WEIGHTED BLEND of all values.\n")
    for name, q in [("exact match on key 2", np.array([[0., 0., 6., 0.]])),
                    ("between keys 0 and 1", np.array([[4., 4., 0., 0.]])),
                    ("matches nothing",      np.array([[0., 0., 0., 0.]]))]:
        out, w = scaled_dot_product_attention(q, K, V)
        print(f"  query: {name:<22} weights={w[0]}  ->  value={out[0]}")
    print("\n  Row 3: a query matching nothing yields a uniform average --")
    print("  the softmax must put its probability mass somewhere. Real models")
    print("  learn 'attention sink' heads that dump this mass on token 0.")


# --------------------------------------------------------------------------- #
# 2. Why sqrt(d_k)                                                             #
# --------------------------------------------------------------------------- #
def demo_scaling():
    rule("2. WHY WE DIVIDE BY sqrt(d_k)  -- the variance argument")
    print("  Q.K sums d_k products of ~unit-variance terms, so Var(Q.K) ~ d_k.")
    print("  Logits therefore GROW with dimension, saturating softmax.\n")
    def stats(d_k, scale, trials=200):
        """Average over many random draws -- a single sample is too noisy to read."""
        stds, maxw, ents = [], [], []
        for _ in range(trials):
            q = rng.normal(size=(1, d_k))
            K = rng.normal(size=(50, d_k))
            raw = (q @ K.T)[0]
            if scale:
                raw = raw / np.sqrt(d_k)
            w = softmax(raw)
            stds.append(raw.std())
            maxw.append(w.max())
            ents.append(-(w * np.log(w + 1e-12)).sum())
        return np.mean(stds), np.mean(maxw), np.mean(ents)

    print(f"  {'d_k':>6} {'std(scores)':>12} {'max weight':>12} {'entropy':>9}  {'softmax gradient':>17}")
    for d_k in (4, 16, 64, 256, 1024):
        sd, p, ent = stats(d_k, scale=False)
        print(f"  {d_k:>6} {sd:>12.2f} {p:>12.4f} {ent:>9.3f}  {p*(1-p):>17.2e}")
    print("\n  As d_k grows, one weight -> 1.0, entropy -> 0, and the gradient p(1-p) -> 0.")
    print("  Attention would stop learning. Now WITH the 1/sqrt(d_k) scale:\n")
    print(f"  {'d_k':>6} {'std(scores)':>12} {'max weight':>12} {'entropy':>9}")
    for d_k in (4, 16, 64, 256, 1024):
        sd, p, ent = stats(d_k, scale=True)
        print(f"  {d_k:>6} {sd:>12.2f} {p:>12.4f} {ent:>9.3f}")
    print("\n  std stays ~1 and entropy stays healthy at every dimension. That is the whole point.")


# --------------------------------------------------------------------------- #
# 3. Causal mask                                                               #
# --------------------------------------------------------------------------- #
def demo_causal():
    rule("3. THE CAUSAL MASK")
    n, d = 6, 8
    X = rng.normal(size=(n, d))
    Wq, Wk, Wv = (rng.normal(size=(d, d)) * 0.3 for _ in range(3))
    Q, K, V = X @ Wq, X @ Wk, X @ Wv

    _, w_open = scaled_dot_product_attention(Q, K, V)
    _, w_causal = scaled_dot_product_attention(Q, K, V, mask=causal_mask(n))

    print("  Bidirectional weights (every token sees every token):")
    print(w_open)
    print("\n  Causal weights (upper triangle is exactly zero):")
    print(w_causal)
    print(f"\n  upper triangle sums to {np.triu(w_causal, 1).sum():.1e}  (exactly 0)")
    print("  rows still sum to 1: " + str(np.allclose(w_causal.sum(-1), 1.0)))
    print("\n  This is why a decoder-only LLM can train on ALL positions at once:")
    print("  every position predicts its next token without ever seeing the future.")


# --------------------------------------------------------------------------- #
# 4. Multi-head                                                                #
# --------------------------------------------------------------------------- #
class MultiHeadAttention:
    def __init__(self, d_model=64, n_heads=8, seed=1):
        assert d_model % n_heads == 0, "d_model must divide evenly into heads"
        r = np.random.default_rng(seed)
        self.h, self.d_model = n_heads, d_model
        self.d_head = d_model // n_heads
        s = 1 / np.sqrt(d_model)
        self.Wq, self.Wk, self.Wv, self.Wo = (r.normal(size=(d_model, d_model)) * s
                                              for _ in range(4))

    def split(self, x):                      # (n, d) -> (h, n, d_head)
        n = x.shape[0]
        return x.reshape(n, self.h, self.d_head).transpose(1, 0, 2)

    def merge(self, x):                      # (h, n, d_head) -> (n, d)
        h, n, dh = x.shape
        return x.transpose(1, 0, 2).reshape(n, h * dh)

    def __call__(self, X, mask=None):
        Q, K, V = self.split(X @ self.Wq), self.split(X @ self.Wk), self.split(X @ self.Wv)
        m = None if mask is None else mask[None, :, :]
        out, w = scaled_dot_product_attention(Q, K, V, mask=m)
        return self.merge(out) @ self.Wo, w


def demo_multihead():
    rule("4. MULTI-HEAD ATTENTION")
    n, d_model, h = 10, 64, 8
    X = rng.normal(size=(n, d_model))
    mha = MultiHeadAttention(d_model, h)
    out, w = mha(X, mask=causal_mask(n))
    print(f"  input  {X.shape}   d_model={d_model}, heads={h}, d_head={d_model // h}")
    print(f"  weights{w.shape}  <- one (n x n) attention matrix PER HEAD")
    print(f"  output {out.shape}   same shape as input: blocks are stackable\n")
    print("  Each head attends to a different pattern. Entropy per head on this input:")
    for i in range(h):
        wi = w[i]
        ent = float(np.mean([-(row[row > 0] * np.log(row[row > 0])).sum() for row in wi]))
        bar = "#" * int(ent * 12)
        print(f"    head {i}: mean entropy {ent:.3f}  {bar}")
    print("\n  Low entropy = a sharp, focused head. High = a diffuse, averaging head.")
    print("  In a trained model heads specialise: previous-token heads, syntax heads,")
    print("  induction heads (which is how in-context learning works -- Module 04).")


# --------------------------------------------------------------------------- #
# 5 & 6. Positions                                                             #
# --------------------------------------------------------------------------- #
def demo_permutation():
    rule("5. ATTENTION IS ORDER-BLIND")
    n, d = 5, 16
    X = rng.normal(size=(n, d))
    mha = MultiHeadAttention(d, 4)
    out_a, _ = mha(X)
    perm = np.array([3, 0, 4, 1, 2])
    out_b, _ = mha(X[perm])
    print(f"  attention(shuffle(X)) == shuffle(attention(X))? {np.allclose(out_b, out_a[perm])}")
    print("\n  Self-attention is permutation-EQUIVARIANT: it has no idea what order")
    print("  the tokens came in. 'dog bites man' and 'man bites dog' are identical to it.")
    print("  Position information must be injected explicitly. Hence: positional encoding.")


def sinusoidal_pe(n, d):
    pos = np.arange(n)[:, None]
    i = np.arange(0, d, 2)[None, :]
    angle = pos / np.power(10000, i / d)
    pe = np.zeros((n, d))
    pe[:, 0::2] = np.sin(angle)
    pe[:, 1::2] = np.cos(angle)
    return pe


def apply_rope(x, base=10000.0):
    """Rotary position embedding: rotate each 2-D pair by m*theta_i.

    A dot product between two rotated vectors depends only on the DIFFERENCE of
    their angles -- so attention becomes a function of RELATIVE position, with
    zero extra parameters. This is what Llama/Qwen/Mistral use, and what gets
    manipulated (position interpolation, NTK scaling, YaRN) to extend context.
    """
    n, d = x.shape
    assert d % 2 == 0
    pos = np.arange(n)[:, None]
    theta = 1.0 / (base ** (np.arange(0, d, 2) / d))[None, :]
    ang = pos * theta                       # (n, d/2)
    cos, sin = np.cos(ang), np.sin(ang)
    x_even, x_odd = x[:, 0::2], x[:, 1::2]
    out = np.empty_like(x)
    out[:, 0::2] = x_even * cos - x_odd * sin
    out[:, 1::2] = x_even * sin + x_odd * cos
    return out


def demo_positional():
    rule("6. POSITIONAL ENCODING: SINUSOIDAL vs ROPE")
    n, d = 12, 32
    pe = sinusoidal_pe(n, d)
    print("  Sinusoidal: added to the embeddings. Similarity between positions")
    print("  decays smoothly with distance (cosine similarity to position 0):")
    sims = pe @ pe[0] / (np.linalg.norm(pe, axis=1) * np.linalg.norm(pe[0]) + 1e-9)
    print("   ", np.round(sims, 3))

    print("\n  RoPE: ROTATES q and k instead of adding to them. The key property is")
    print("  that q_m . k_n depends only on (m - n). Verify on random vectors:")
    q = rng.normal(size=(1, d))
    k = rng.normal(size=(1, d))
    def rot_dot(m, n_):
        qm = apply_rope(np.repeat(q, m + 1, 0))[m:m + 1]
        kn = apply_rope(np.repeat(k, n_ + 1, 0))[n_:n_ + 1]
        return float((qm @ kn.T).item())
    print(f"    positions (2, 5)  offset -3 : {rot_dot(2, 5):+.6f}")
    print(f"    positions (7, 10) offset -3 : {rot_dot(7, 10):+.6f}   <- identical")
    print(f"    positions (2, 9)  offset -7 : {rot_dot(2, 9):+.6f}   <- different offset, different value")
    print("\n  Relative position, for free, with no extra parameters. That is RoPE.")


# --------------------------------------------------------------------------- #
# 7. A full block                                                              #
# --------------------------------------------------------------------------- #
class TransformerBlock:
    """Pre-LN block:  h = x + MHA(LN(x));  out = h + FFN(LN(h))"""

    def __init__(self, d_model=64, n_heads=8, d_ff=None, seed=2, use_ln=True):
        r = np.random.default_rng(seed)
        self.use_ln = use_ln
        d_ff = d_ff or 4 * d_model
        self.mha = MultiHeadAttention(d_model, n_heads, seed=seed)
        s = 1 / np.sqrt(d_model)
        self.W1 = r.normal(size=(d_model, d_ff)) * s
        self.b1 = np.zeros(d_ff)
        self.W2 = r.normal(size=(d_ff, d_model)) * s
        self.b2 = np.zeros(d_model)
        self.n_params = 4 * d_model * d_model + d_model * d_ff * 2 + d_ff + d_model

    def __call__(self, x, mask=None):
        norm = layer_norm if self.use_ln else (lambda z: z)
        a, _ = self.mha(norm(x), mask=mask)
        h = x + a                                        # residual 1
        f = gelu(norm(h) @ self.W1 + self.b1) @ self.W2 + self.b2
        return h + f                                     # residual 2


def demo_block():
    rule("7. A COMPLETE PRE-LN TRANSFORMER BLOCK")
    n, d_model, h = 16, 64, 8
    x = rng.normal(size=(n, d_model))
    blocks = [TransformerBlock(d_model, h, seed=i) for i in range(6)]
    mask = causal_mask(n)

    no_ln = [TransformerBlock(d_model, h, seed=i, use_ln=False) for i in range(6)]

    print("  Activation scale through depth, with and without LayerNorm:\n")
    print(f"  {'layer':>6} {'std (Pre-LN)':>14} {'std (no LN)':>14}")
    print(f"  {'input':>6} {x.std():>14.3f} {x.std():>14.3f}")
    a_cur, b_cur = x, x
    for i in range(6):
        a_cur = blocks[i](a_cur, mask=mask)
        b_cur = no_ln[i](b_cur, mask=mask)
        print(f"  {i:>6} {a_cur.std():>14.3f} {b_cur.std():>14.3e}")
    print("\n  With Pre-LN the scale creeps up roughly linearly -- residual streams")
    print("  accumulate, and that is expected and trainable.")
    print("  Without it, each block multiplies the scale and you get exponential")
    print("  blow-up within six layers. Now imagine eighty. That is why LayerNorm")
    print("  is not optional, and why its PLACEMENT (Pre- vs Post-LN) mattered enough")
    print("  to change the whole field's default.")

    b = blocks[0]
    attn_p = 4 * d_model * d_model
    ffn_p = 2 * d_model * (4 * d_model)
    print(f"\n  parameters per block: attention {attn_p:,}  FFN {ffn_p:,}"
          f"  -> FFN is {ffn_p / (attn_p + ffn_p):.0%} of the block")
    print("  In a real LLM the FFN holds ~2/3 of all parameters, and appears to be")
    print("  where most factual knowledge lives.")


# --------------------------------------------------------------------------- #
# 8 & 9. Memory                                                                #
# --------------------------------------------------------------------------- #
def demo_shapes_and_memory():
    rule("8. WHERE THE MEMORY GOES: the (B, h, n, n) tensor")
    print(f"  {'batch':>6}{'heads':>7}{'seq':>8}{'attn matrix (fp16)':>22}")
    for B, h, n in [(1, 32, 1024), (8, 32, 1024), (8, 32, 8192), (8, 32, 32768)]:
        gb = B * h * n * n * 2 / 1e9
        note = "  <- one layer!" if gb > 10 else ""
        print(f"  {B:>6}{h:>7}{n:>8}{gb:>19.2f} GB{note}")
    print("\n  Quadratic in sequence length. FlashAttention computes EXACTLY this")
    print("  attention without ever materialising that matrix in HBM -- it tiles the")
    print("  computation and keeps blocks in SRAM. Same math, ~2-4x faster, far less memory.")

    rule("9. THE KV CACHE, MEASURED")
    print("  cache = 2 * layers * kv_heads * d_head * seq * batch * bytes\n")
    print(f"  {'config':<34}{'seq':>8}{'batch':>7}{'KV cache':>12}")
    configs = [
        ("8B MHA   (32L, 32kv, 128d)", 32, 32, 128),
        ("8B GQA   (32L,  8kv, 128d)", 32, 8, 128),
        ("8B MQA   (32L,  1kv, 128d)", 32, 1, 128),
        ("70B GQA  (80L,  8kv, 128d)", 80, 8, 128),
    ]
    for name, L, kv, dh in configs:
        for seq, bs in [(4096, 1), (32768, 1), (32768, 16)]:
            gb = 2 * L * kv * dh * seq * bs * 2 / 1e9
            print(f"  {name:<34}{seq:>8}{bs:>7}{gb:>10.2f} GB")
        print()
    print("  Read the first block: switching MHA -> GQA cuts the cache 4x at identical")
    print("  quality-per-parameter. That is the entire reason GQA exists.")
    print("  KV cache -- not weights -- is what caps your concurrency in production.")


if __name__ == "__main__":
    demo_soft_lookup()
    demo_scaling()
    demo_causal()
    demo_multihead()
    demo_permutation()
    demo_positional()
    demo_block()
    demo_shapes_and_memory()
    print("\nYou have now implemented every component of a transformer.")
    print("Module 04 is what happens when you stack 80 of these and train on 15T tokens.\n")
