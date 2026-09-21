"""
Benchmark literacy demo -- why a single leaderboard number is misleading.

Two synthetic demonstrations, both built so you can see the mechanism, not just take
it on faith:

  1. CONTAMINATION / OVERFITTING: a model that "memorized" part of a public benchmark
     scores well on it, but its score collapses toward its true skill level when tested
     on held-out VARIANTS of the same problems (same underlying task, different surface
     form -- exactly what a decontamination check or a private eval set catches and a
     public leaderboard cannot).

  2. SAMPLING VARIANCE vs. A REAL CAPABILITY GAP: a small benchmark (small N) produces
     enough run-to-run noise that a tiny true skill difference between two models is
     often NOT distinguishable from noise -- until you either run enough trials or
     compute a confidence interval and check whether it excludes zero.

Neither demonstration needs a real model or an API key. "Problems" are Bernoulli trials
with a known ground-truth success probability, which is what lets us show the effect
precisely instead of asserting it.

    python code/benchmark_literacy_demo.py

Requires: nothing but the standard library.
"""
from __future__ import annotations

import random
import statistics
from dataclasses import dataclass

RANDOM_SEED = 42


def rule(t: str) -> None:
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


# --------------------------------------------------------------------------- #
# 1. CONTAMINATION: memorized problems inflate the public benchmark score.    #
# --------------------------------------------------------------------------- #
@dataclass
class ContaminatedModel:
    name: str
    true_skill: float          # real capability: P(solve a genuinely novel problem)
    memorized_recall: float    # P(get a MEMORIZED problem right, near-perfect if leaked)
    leak_fraction: float       # fraction of the PUBLIC benchmark that leaked into training


def simulate_public_benchmark(model: ContaminatedModel, n_problems: int, rng: random.Random) -> float:
    """The public benchmark: some fraction of its problems leaked into training data."""
    correct = 0
    for _ in range(n_problems):
        leaked = rng.random() < model.leak_fraction
        p_correct = model.memorized_recall if leaked else model.true_skill
        correct += rng.random() < p_correct
    return correct / n_problems


def simulate_held_out_variants(model: ContaminatedModel, n_problems: int, rng: random.Random) -> float:
    """
    Held-out variants: same underlying problem, reworded/restructured so memorization
    of the exact leaked text doesn't help. This is what decontamination-aware evals and
    "held-out check" test sets are for -- and it's exactly what a public leaderboard,
    run once against a fixed public set, cannot see.
    """
    correct = sum(rng.random() < model.true_skill for _ in range(n_problems))
    return correct / n_problems


def contamination_demo() -> None:
    rule("1. CONTAMINATION: THE PUBLIC SCORE VS. THE TRUE SCORE")
    rng = random.Random(RANDOM_SEED)
    n = 500

    models = [
        ContaminatedModel("clean-model", true_skill=0.62, memorized_recall=0.95, leak_fraction=0.00),
        ContaminatedModel("lightly-contaminated", true_skill=0.62, memorized_recall=0.95, leak_fraction=0.15),
        ContaminatedModel("heavily-contaminated", true_skill=0.62, memorized_recall=0.95, leak_fraction=0.45),
    ]

    print(f"  All three models share the SAME true skill (0.62). Only their exposure to")
    print(f"  leaked benchmark problems during training differs.\n")
    print(f"  {'model':<24}{'public score':>14}{'held-out score':>16}{'inflation':>12}")
    for m in models:
        public = simulate_public_benchmark(m, n, rng)
        held_out = simulate_held_out_variants(m, n, rng)
        inflation = public - held_out
        print(f"  {m.name:<24}{public:>14.3f}{held_out:>16.3f}{inflation:>12.3f}")

    print("\n  The 'heavily-contaminated' model looks meaningfully better on the public")
    print("  leaderboard than 'clean-model' -- despite having IDENTICAL true skill.")
    print("  The held-out variant score recovers the truth: ~0.62 for all three.")
    print("\n  This is not hypothetical: it is the exact mechanism behind Module 04's")
    print("  decontamination warning and Module 01's test-set-leakage lesson, replayed")
    print("  at the scale of an entire public benchmark. A single published leaderboard")
    print("  score cannot distinguish 'genuinely capable' from 'has seen this test before.'")
    print("  Mitigation: evaluate on a private, continuously refreshed held-out set")
    print("  (Module 15) that no model's training data could contain.")


# --------------------------------------------------------------------------- #
# 2. SAMPLING VARIANCE vs. A REAL CAPABILITY GAP.                             #
# --------------------------------------------------------------------------- #
def run_benchmark(true_skill: float, n_problems: int, rng: random.Random) -> float:
    return sum(rng.random() < true_skill for _ in range(n_problems)) / n_problems


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval -- more honest than a naive +/- at small n or extreme p."""
    if n == 0:
        return (0.0, 0.0)
    phat = successes / n
    denom = 1 + z ** 2 / n
    center = (phat + z ** 2 / (2 * n)) / denom
    margin = (z * ((phat * (1 - phat) / n + z ** 2 / (4 * n ** 2)) ** 0.5)) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def variance_demo() -> None:
    rule("2. SAMPLING VARIANCE: IS THAT SCORE GAP REAL, OR NOISE?")
    rng = random.Random(RANDOM_SEED)

    model_a_skill = 0.70
    model_b_skill = 0.72   # a REAL but small difference -- 2 points of true capability
    n_repeats = 30

    for n_problems in (50, 200, 1000, 5000, 20_000):
        a_scores = [run_benchmark(model_a_skill, n_problems, rng) for _ in range(n_repeats)]
        b_scores = [run_benchmark(model_b_skill, n_problems, rng) for _ in range(n_repeats)]
        a_mean, a_std = statistics.mean(a_scores), statistics.pstdev(a_scores)
        b_mean, b_std = statistics.mean(b_scores), statistics.pstdev(b_scores)

        # One single "official" run each, the way a leaderboard reports it:
        one_a = run_benchmark(model_a_skill, n_problems, rng)
        one_b = run_benchmark(model_b_skill, n_problems, rng)
        ci_a = wilson_interval(round(one_a * n_problems), n_problems)
        ci_b = wilson_interval(round(one_b * n_problems), n_problems)
        overlap = not (ci_a[1] < ci_b[0] or ci_b[1] < ci_a[0])

        print(f"\n  n = {n_problems} problems/run  (true skill: A=0.70, B=0.72, true gap = 0.02)")
        print(f"    across {n_repeats} repeated runs: A = {a_mean:.3f} (+/-{a_std:.3f} sd)   "
              f"B = {b_mean:.3f} (+/-{b_std:.3f} sd)")
        print(f"    ONE reported run:               A = {one_a:.3f}  95% CI {ci_a[0]:.3f}-{ci_a[1]:.3f}")
        print(f"                                     B = {one_b:.3f}  95% CI {ci_b[0]:.3f}-{ci_b[1]:.3f}")
        print(f"    CIs overlap? {overlap}  ->  "
              + ("cannot conclude B > A from this run alone" if overlap
                 else "B's advantage is distinguishable from noise at this n"))

    print("\n  Watch the run-to-run standard deviation shrink as n grows, and watch the")
    print("  single-run confidence intervals stop overlapping only once n is large enough")
    print("  to resolve a 2-point true difference. At n=50-200 -- the size of many")
    print("  published benchmark subsets, and smaller than GPQA's ~450 questions -- a")
    print("  real 2-point gap is frequently indistinguishable from sampling noise.")
    print("\n  The practical rule: NEVER trust a single benchmark number without either")
    print("  (a) a confidence interval reported alongside it, or (b) a held-out check")
    print("  confirming the score isn't contaminated (demo 1). A leaderboard rank of")
    print("  '#3 vs #4' is frequently not a real, reproducible difference in capability.")


if __name__ == "__main__":
    contamination_demo()
    variance_demo()
    rule("TAKEAWAY")
    print("  A single leaderboard score answers neither 'is this real capability' nor")
    print("  'is this difference reproducible.' Before you let a benchmark move a model")
    print("  decision: check for contamination (a held-out variant check), and check for")
    print("  significance (a confidence interval or repeated runs). Then, per notes/02,")
    print("  use the leaderboard only to build a SHORTLIST -- decide with your own eval")
    print("  set (Module 15) and code/model_selection_scorer.py in this module.\n")
