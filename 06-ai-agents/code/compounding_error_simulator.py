"""
The compounding-error math, proven by Monte Carlo instead of just asserted.

The claim this script exists to make visceral: if an agent's per-step success
probability is p, and a task needs N steps where each step's correctness depends on
every step before it, end-to-end success is approximately p**N -- not p, not "pretty
good because each step is pretty good". Multiplication of probabilities below 1 is
merciless, and 95% per step, which SOUNDS excellent, is a coin flip by step 14.

Two models are simulated:
  1. NO RECOVERY -- a wrong step silently corrupts every step after it (the realistic
     case for e.g. a miscalculated intermediate number that no one checks). Success
     requires all N steps to be independently correct: P(success) = p**N.
  2. WITH RECOVERY -- some fraction `r` of failures are caught and fixed before they
     propagate (self-critique, a verifier step, a human check). This raises the
     EFFECTIVE per-step success rate to p_eff = p + (1-p)*r, and overall success is
     p_eff**N. Recovery helps, but unless r is large it barely dents the curve --
     which is the honest answer to "can't we just add a self-correction step?".

Both models are simulated with real random trials AND computed analytically, side by
side, so you can see the Monte Carlo estimate converge to the closed form. This is
also a small, clean example of *why* you'd bother simulating something you can already
compute: it's the same technique you reach for the moment recovery isn't a clean
independent-per-step probability (e.g. "a verifier catches errors 90% of the time but
only checks every 3rd step") and closed form gets ugly fast.

    python code/compounding_error_simulator.py

Requires: nothing outside the standard library.
"""
from __future__ import annotations

import random
import statistics

TRIALS = 200_000
SEED = 42


# --------------------------------------------------------------------------------- #
# The core model.                                                                    #
# --------------------------------------------------------------------------------- #

def analytic_success(p: float, n_steps: int, recovery: float = 0.0) -> float:
    """Closed form: an independent per-step success chance, N steps, optional recovery."""
    p_eff = p + (1 - p) * recovery
    return p_eff ** n_steps


def simulate_trajectory(p: float, n_steps: int, recovery: float, rng: random.Random) -> bool:
    """Run one agent trajectory. Each step independently succeeds with probability p.
    A step that fails is 'fixed' (counts as a success) with probability `recovery` --
    otherwise the whole trajectory is corrupted and the task fails, full stop, even if
    later steps would have gone fine. That's the compounding-error part: step 7 does
    not get a fair chance once step 2 silently returned a wrong number."""
    for _ in range(n_steps):
        step_ok = rng.random() < p
        if not step_ok:
            recovered = rng.random() < recovery
            if not recovered:
                return False
    return True


def simulate_success_rate(p: float, n_steps: int, recovery: float, trials: int,
                           rng: random.Random) -> float:
    successes = sum(simulate_trajectory(p, n_steps, recovery, rng) for _ in range(trials))
    return successes / trials


# --------------------------------------------------------------------------------- #
# Presentation helpers.                                                              #
# --------------------------------------------------------------------------------- #

def rule(title: str) -> None:
    print("\n" + "=" * 78 + f"\n{title}\n" + "=" * 78)


def bar(frac: float, width: int = 40) -> str:
    filled = round(frac * width)
    return "#" * filled + "." * (width - filled)


def main() -> None:
    rng = random.Random(SEED)

    # ----------------------------------------------------------------------- #
    rule("1. NO RECOVERY -- Monte Carlo vs. the closed form p**N")
    print(f"  {TRIALS:,} simulated trajectories per cell. 'sim' should track 'p**N' closely.\n")
    print(f"  {'p':>6} {'N':>4} {'p**N (analytic)':>16} {'simulated':>10} {'diff':>8}")
    ps = [0.99, 0.95, 0.90, 0.85, 0.80]
    ns = [1, 5, 10, 20, 50]
    for p in ps:
        for n in ns:
            analytic = analytic_success(p, n)
            sim = simulate_success_rate(p, n, recovery=0.0, trials=TRIALS, rng=rng)
            print(f"  {p:>6.2f} {n:>4} {analytic:>16.4f} {sim:>10.4f} {abs(analytic - sim):>8.4f}")
        print()
    print("  The 'diff' column stays small (Monte Carlo noise at this trial count is")
    print("  roughly +/-0.002-0.005). The simulation and the formula agree because they")
    print("  are describing the same thing: independent per-step correctness multiplies.")

    # ----------------------------------------------------------------------- #
    rule("2. THE NUMBER THAT SHOULD WORRY YOU")
    p, n = 0.95, 20
    result = analytic_success(p, n)
    print(f"  A per-step accuracy of {p:.0%} sounds like an A+. Chain {n} such steps:")
    print(f"    {p} ** {n} = {result:.4f}  ->  end-to-end task success = {result:.1%}")
    print(f"    ...which means the task FAILS {1 - result:.1%} of the time.")
    print("  This is not a pathological model. A 20-step agent is a modest tool-use")
    print("  session: read a file, plan, call 4-5 tools, check results, write output.")
    print("  '95% accurate per step' quietly became 'wrong more often than right'.")

    # ----------------------------------------------------------------------- #
    rule("3. THE DECAY CURVE FOR A FEW PER-STEP ACCURACIES")
    print(f"  {'N':>3}  " + "  ".join(f"p={p:<5.2f}" for p in [0.99, 0.97, 0.95, 0.90]))
    for n in [1, 2, 3, 5, 7, 10, 15, 20, 30, 50]:
        cells = [f"{analytic_success(p, n):.3f}" for p in [0.99, 0.97, 0.95, 0.90]]
        print(f"  {n:>3}  " + "      ".join(cells))
    print("\n  Visualised for p=0.95, N=1..30 (each # is 2.5% success probability):")
    for n in [1, 2, 3, 5, 7, 10, 14, 20, 25, 30]:
        s = analytic_success(0.95, n)
        print(f"  N={n:>2}  {bar(s)}  {s:.1%}")
    print("\n  The curve is not gentle. It falls off a cliff in the first ~15 steps,")
    print("  then grinds slowly toward zero. Most of the damage happens early.")

    # ----------------------------------------------------------------------- #
    rule("4. DOES ERROR RECOVERY SAVE YOU? (self-critique / verifier step)")
    print("  Model: a failed step is caught and fixed with probability `recovery`,")
    print("  which raises the EFFECTIVE per-step success to p_eff = p + (1-p)*recovery.\n")
    p, n = 0.90, 20
    print(f"  Fixed: p={p}, N={n} steps. Varying recovery quality:")
    print(f"  {'recovery':>10} {'p_eff':>8} {'analytic':>10} {'simulated':>10}")
    for recovery in [0.0, 0.25, 0.5, 0.75, 0.9, 0.99]:
        p_eff = p + (1 - p) * recovery
        analytic = analytic_success(p, n, recovery)
        sim = simulate_success_rate(p, n, recovery, trials=TRIALS, rng=rng)
        print(f"  {recovery:>10.2f} {p_eff:>8.3f} {analytic:>10.3f} {sim:>10.3f}")
    print("\n  Recovery has to be nearly PERFECT (>90%) before a 20-step, 90%-per-step")
    print("  agent clears 80% end-to-end. A 'pretty good' verifier (catches 50-75% of")
    print("  errors) barely moves the needle -- it raises p_eff from 0.90 to 0.95-0.975,")
    print("  and you already saw above what 0.95^20 looks like.")

    # ----------------------------------------------------------------------- #
    rule("5. THE ENGINEERING CONCLUSIONS")
    print("  - Shrink N. Fewer, coarser-grained steps beat many fine-grained ones for")
    print("    the same total capability. This is the real argument for giving an agent")
    print("    a well-designed high-level tool instead of five low-level ones.")
    print("  - Push p up per step before anything else -- better tool descriptions,")
    print("    narrower tool surface, structured output -- see notes/02, tool design.")
    print("  - Recovery mechanisms (self-critique, verifiers, human-in-the-loop) help")
    print("    but do not repeal the math; budget for them to be VERY good, not merely")
    print("    present. A 'looks-right' verifier is a rounding error on this curve.")
    print("  - Measure end-to-end task success, not average per-step accuracy -- a")
    print("    dashboard of 95%-ish step scores can hide a 35% task success rate. This")
    print("    is exactly the trap ../15-ai-evals/ exists to catch (see notes/02 section 4).")


if __name__ == "__main__":
    main()
