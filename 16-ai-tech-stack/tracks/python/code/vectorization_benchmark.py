"""
Vectorization, broadcasting, and the cost of a Python `for` loop.

Why this file exists
--------------------
"Python is slow" is imprecise. CPython's *interpreter* is slow; the numeric stack
underneath it is not. The skill that separates an AI engineer from someone who
merely writes Python is knowing exactly where the loop should live: in your code
(slow, flexible) or inside a compiled kernel (fast, rigid).

This script measures that gap on a real task -- pairwise squared Euclidean
distances between two sets of embedding-shaped vectors -- which is the inner loop
of k-NN, vector retrieval (Module 08) and every clustering algorithm you will meet.

Then it shows the flip side: broadcasting will happily compute the *wrong* answer
at full speed and never warn you.

    python code/vectorization_benchmark.py

Requires: numpy. Runs offline. ~5 seconds.
"""
from __future__ import annotations

import sys
import time
from typing import Callable

import numpy as np

rng = np.random.default_rng(0)


# --------------------------------------------------------------------------- #
# Timing helper                                                               #
# --------------------------------------------------------------------------- #
def bench(label: str, fn: Callable[[], np.ndarray], repeats: int = 3) -> tuple[float, np.ndarray]:
    """Return (best wall-clock seconds, result). Best-of-N, not mean: we want the
    machine's capability, not the average interference from other processes."""
    best = float("inf")
    out = None
    for _ in range(repeats):
        t0 = time.perf_counter()
        out = fn()
        best = min(best, time.perf_counter() - t0)
    return best, out


def human(seconds: float) -> str:
    if seconds >= 1:
        return f"{seconds:8.3f} s "
    if seconds >= 1e-3:
        return f"{seconds * 1e3:8.3f} ms"
    return f"{seconds * 1e6:8.3f} us"


# --------------------------------------------------------------------------- #
# 1. Four ways to compute the same matrix                                     #
# --------------------------------------------------------------------------- #
# A: 300 "query" vectors, B: 400 "document" vectors, 128 dims each.
# Result is a (300, 400) matrix of squared distances. 120,000 cells, 128 mults
# per cell = ~15M floating-point operations. Trivial for a CPU. Not trivial for
# an interpreter that has to box every float.
N_A, N_B, DIM = 300, 400, 128
A = rng.standard_normal((N_A, DIM))
B = rng.standard_normal((N_B, DIM))


def dist_pure_python() -> np.ndarray:
    """Nested loops over Python floats. The honest baseline everyone starts with."""
    a_list = A.tolist()
    b_list = B.tolist()
    out = [[0.0] * N_B for _ in range(N_A)]
    for i, ai in enumerate(a_list):
        row = out[i]
        for j, bj in enumerate(b_list):
            s = 0.0
            for k in range(DIM):
                d = ai[k] - bj[k]
                s += d * d
            row[j] = s
    return np.array(out)


def dist_numpy_loop() -> np.ndarray:
    """Loops in Python, arithmetic in NumPy. The trap: people think this is
    'vectorized' because numpy appears. It is 120,000 dispatches into C, each
    with fixed overhead of a few microseconds. The overhead is the whole cost."""
    out = np.empty((N_A, N_B))
    for i in range(N_A):
        for j in range(N_B):
            d = A[i] - B[j]
            out[i, j] = d @ d
    return out


def dist_broadcast() -> np.ndarray:
    """One loop removed by broadcasting.

    A[:, None, :] has shape (300, 1, 128)
    B[None, :, :] has shape (  1, 400, 128)
    -> the subtraction broadcasts to (300, 400, 128), then we sum over axis 2.

    Fast, and the clearest statement of intent. But look at that middle shape:
    300*400*128 float64 = 122.9 MB of temporary array for a 0.96 MB answer.
    Broadcasting materialises the intermediate. At embedding scale (100k x 100k)
    this is how you OOM a machine with one readable line of code.
    """
    diff = A[:, None, :] - B[None, :, :]
    return np.einsum("ijk,ijk->ij", diff, diff)


def dist_gemm() -> np.ndarray:
    """The algebraic trick: ||a-b||^2 = ||a||^2 - 2a.b + ||b||^2.

    Now the heavy part is a single matrix multiply, which NumPy hands to BLAS --
    multi-threaded, cache-blocked, SIMD-vectorised assembly. No large temporary.
    Peak extra memory is the (300, 400) output plus two tiny norm vectors.

    This is the same rewrite FAISS, scikit-learn and every vector DB use.
    """
    a2 = np.einsum("ij,ij->i", A, A)[:, None]      # (300, 1)
    b2 = np.einsum("ij,ij->i", B, B)[None, :]      # (1, 400)
    out = a2 - 2.0 * (A @ B.T) + b2
    # Catastrophic cancellation can push near-zero distances slightly negative.
    # Real libraries clip. If you ever see a NaN out of np.sqrt on distances,
    # this is why.
    return np.maximum(out, 0.0)


def section_one() -> None:
    print("=" * 74)
    print("1. Pairwise squared distances: (300 x 128) vs (400 x 128) -> (300, 400)")
    print("=" * 74)

    results: dict[str, tuple[float, np.ndarray]] = {}
    results["pure Python loops"] = bench("", dist_pure_python, repeats=1)
    results["NumPy inside a loop"] = bench("", dist_numpy_loop, repeats=1)
    results["broadcasting (300,400,128)"] = bench("", dist_broadcast, repeats=3)
    results["BLAS gemm identity"] = bench("", dist_gemm, repeats=5)

    baseline = results["pure Python loops"][0]
    reference = results["BLAS gemm identity"][1]

    print(f"{'approach':<30}{'best time':>12}{'speedup':>12}   correct?")
    print("-" * 74)
    for label, (secs, out) in results.items():
        ok = np.allclose(out, reference, atol=1e-8)
        print(f"{label:<30}{human(secs):>12}{baseline / secs:>11.1f}x   {'yes' if ok else 'NO'}")

    print()
    print("Read the table this way:")
    print("  * Loop -> NumPy-in-a-loop buys little. Per-call overhead dominates,")
    print("    so you paid for C dispatch 120,000 times and got C speed 0 times.")
    print("  * Broadcasting is the first real win: one dispatch, one kernel.")
    print("  * gemm wins again because BLAS is threaded and cache-aware, AND")
    print("    because it never allocates the 123 MB intermediate.")

    # ---- memory note, measured rather than asserted -----------------------
    tmp_bytes = N_A * N_B * DIM * A.dtype.itemsize
    out_bytes = N_A * N_B * A.dtype.itemsize
    print()
    print("MEMORY (the part benchmarks usually hide):")
    print(f"  broadcast intermediate : {tmp_bytes / 1e6:9.1f} MB")
    print(f"  final answer           : {out_bytes / 1e6:9.1f} MB")
    print(f"  ratio                  : {tmp_bytes / out_bytes:9.0f}x")
    print("  Scale N to 20,000 x 20,000 and the intermediate is 409 GB.")
    print("  Same line of code. Different outcome: your process is killed.")
    print("  Rule: if broadcasting adds a dimension, ask what it costs in bytes.")


# --------------------------------------------------------------------------- #
# 2. float32 vs float64 -- the speedup nobody bothers to take                 #
# --------------------------------------------------------------------------- #
def section_two() -> None:
    print()
    print("=" * 74)
    print("2. dtype is a performance decision")
    print("=" * 74)
    big_a = rng.standard_normal((1200, 512))
    big_b = rng.standard_normal((1200, 512))

    t64, _ = bench("", lambda: big_a @ big_b.T, repeats=5)
    a32, b32 = big_a.astype(np.float32), big_b.astype(np.float32)
    t32, _ = bench("", lambda: a32 @ b32.T, repeats=5)

    print(f"  float64 matmul : {human(t64)}   ({big_a.nbytes / 1e6:.1f} MB per operand)")
    print(f"  float32 matmul : {human(t32)}   ({a32.nbytes / 1e6:.1f} MB per operand)")
    print(f"  speedup        : {t64 / t32:.2f}x, half the memory, half the bandwidth")
    print()
    print("  NumPy defaults to float64. Every embedding model, every GPU tensor")
    print("  core, and every vector index you will use is float32 or smaller.")
    print("  Storing embeddings as float64 doubles your RAM bill for precision")
    print("  the model never had. Cast at the boundary: np.asarray(x, np.float32).")


# --------------------------------------------------------------------------- #
# 3. The deliberate broadcasting bug                                          #
# --------------------------------------------------------------------------- #
def section_three() -> None:
    print()
    print("=" * 74)
    print("3. The silent broadcasting bug (this one has shipped to production)")
    print("=" * 74)

    # Five documents, three-dimensional embeddings. We want to mean-centre them:
    # subtract the per-column mean so each dimension has mean zero.
    emb = np.array(
        [[1.0, 10.0, 100.0],
         [2.0, 20.0, 200.0],
         [3.0, 30.0, 300.0],
         [4.0, 40.0, 400.0],
         [5.0, 50.0, 500.0]]
    )

    col_mean = emb.mean(axis=0)          # shape (3,)  -- one mean per dimension. Correct.
    row_mean = emb.mean(axis=1)          # shape (5,)  -- one mean per document. Wrong axis.

    correct = emb - col_mean             # (5,3) - (3,) -> broadcasts along rows. Right.

    print("  emb.shape      =", emb.shape)
    print("  col_mean.shape =", col_mean.shape, " <- axis=0, one per dimension (what we want)")
    print("  row_mean.shape =", row_mean.shape, " <- axis=1, one per document (what we typed)")
    print()
    print("  Correct centring, emb - col_mean, column means now:", np.round(correct.mean(axis=0), 10))

    # Now the bug. A five-row matrix and a five-element vector. `emb - row_mean`
    # would raise, because (5,3) and (5,) cannot align -- broadcasting compares
    # trailing dimensions, and 3 != 5. Good: an exception is a gift.
    try:
        _ = emb - row_mean
    except ValueError as e:
        print()
        print("  emb - row_mean raises, which is the GOOD case:")
        print(f"    ValueError: {e}")

    # The dangerous case is when the shapes happen to be compatible. Here is the
    # exact same mistake on a square batch -- and now nothing complains.
    square = np.array(
        [[1.0, 10.0, 100.0],
         [2.0, 20.0, 200.0],
         [3.0, 30.0, 300.0]]
    )
    by_col = square - square.mean(axis=0)            # intended
    by_row = square - square.mean(axis=1)            # typo: axis=1
    print()
    print("  Now make the batch square (3x3) -- the shapes align by accident:")
    print("    intended (axis=0) column means:", np.round(by_col.mean(axis=0), 10))
    print("    typo     (axis=1) column means:", np.round(by_row.mean(axis=0), 10))
    print("    identical results?", np.allclose(by_col, by_row))
    print()
    print("  No exception. No warning. Correct dtype, correct shape, wrong numbers.")
    print("  Your model trains, your loss goes down, your eval is quietly 4% worse")
    print("  and you spend a week blaming the learning rate.")

    # The fix: keepdims, which makes the intent unambiguous and the broken case loud.
    kept = square.mean(axis=1, keepdims=True)        # (3, 1) -- explicitly a column
    print()
    print("  THE FIX -- always reduce with keepdims=True:")
    print(f"    square.mean(axis=1).shape            = {square.mean(axis=1).shape}   (rank-1, will silently align)")
    print(f"    square.mean(axis=1, keepdims=True)   = {kept.shape}  (rank-2, aligns only one way)")
    print("  Then `square - kept` means per-row centring and can never mean anything else.")
    print()
    print("  Defensive habits that cost nothing:")
    print("    * keepdims=True on every reduction you will broadcast against")
    print("    * assert arr.shape == (n, d) at function boundaries")
    print("    * name arrays for their shape: emb_nd, mean_1d, logits_bkv")
    print("    * never test a pipeline with a square batch -- 32x32 hides everything")


# --------------------------------------------------------------------------- #
# 4. When to leave Python entirely                                            #
# --------------------------------------------------------------------------- #
def section_four() -> None:
    print()
    print("=" * 74)
    print("4. When vectorizing is not enough")
    print("=" * 74)
    print("""
  Vectorization works when the operation is uniform over a big array. It fails on
  branch-heavy, sequential, or irregular work -- tokenizers, tree traversal,
  graph walks, custom samplers. For those, escaping the interpreter means:

    Numba          @njit on numeric loops. Minutes to adopt, 10-100x, stays in
                   your .py file. First thing to try.
    Cython         Typed superset of Python, compiled. More ceremony, more control.
    Rust + PyO3    What the modern stack actually did: tokenizers, polars, ruff,
                   uv and pydantic-core are all Rust behind a Python API.
    C++ ext        When you are wrapping something that already exists.
    torch.compile  For tensor code that already runs on torch; fuses kernels.
    JAX jit        Trace-and-compile via XLA, if you can write pure functions.

  Decision rule, in order:
    1. Profile. You are wrong about where the time goes. Always.
    2. Can it be one array operation? Do that. Cheapest win available.
    3. Is the array huge? Check the temporaries, then batch or use a gemm identity.
    4. Is it IO-bound, not CPU-bound? You do not need speed, you need asyncio.
       See async_llm_client.py -- for LLM calls this is almost always the answer.
    5. Only now reach for a compiled path.

  The failure mode to avoid is step 5 before step 1: three days rewriting a
  function in Rust that accounted for 4% of runtime.
""".rstrip())


def main() -> int:
    print()
    print(f"Python {sys.version.split()[0]} | NumPy {np.__version__}")
    section_one()
    section_two()
    section_three()
    section_four()
    print()
    print("Three things worth remembering: leaving the interpreter is worth one")
    print("to two orders of magnitude, reaching BLAS is worth another, and the")
    print("price of broadcasting is paid in bytes for the dimension you added.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
