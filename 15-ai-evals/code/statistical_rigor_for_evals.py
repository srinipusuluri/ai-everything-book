"""
Statistical rigor for eval scores -- confidence intervals, paired significance
tests, and the sample-size trap that makes most "we improved the eval by 2
points" claims meaningless.

An eval score is a SAMPLE STATISTIC, not a fact about your model. 50 examples
scored at 72% is an estimate of some underlying true accuracy, with real
sampling noise around it -- exactly like a poll of 50 voters. Treat it as a
point estimate with no uncertainty and you will ship a "regression" that was
never there, chase a "win" that was luck, and eventually stop trusting your
own eval suite (rightly).

This script demonstrates, with formulas checked against known reference
values:

  1. The Wilson score interval for a proportion (an eval accuracy IS a
     proportion) vs. the naive normal ("Wald") interval, and why Wilson wins.
  2. McNemar's test -- the correct paired test for "did prompt B fix examples
     prompt A got wrong, net of examples it broke" on the SAME eval set.
  3. A paired bootstrap for continuous scores (rubric/judge scores, not just
     binary correct/incorrect).
  4. The numerically undeniable point: "72% vs 74%" is noise at n=50 and a
     real, statistically significant difference at n=2000, for the EXACT
     SAME two underlying accuracies.
  5. Why re-running your eval set against many prompt variants and picking
     the best-looking one is p-hacking, and how often that trick manufactures
     a "significant" win out of pure noise.

Runs fully offline, no network, no API key.

    python code/statistical_rigor_for_evals.py

Requires: numpy, scipy (see requirements.txt).
"""
from __future__ import annotations

import numpy as np
from scipy import stats

RANDOM_STATE = 42
rng = np.random.default_rng(RANDOM_STATE)
rule = lambda t: print("\n" + "=" * 76 + f"\n{t}\n" + "=" * 76)


# --------------------------------------------------------------------------- #
# 1. Confidence intervals for a proportion (an eval accuracy IS a proportion) #
# --------------------------------------------------------------------------- #
def wald_ci(successes: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """The naive interval everyone reaches for first: p_hat +/- z * SE.

    Uses the SAMPLE proportion to estimate its own standard error, then
    assumes a normal shape. Both assumptions quietly break exactly where you
    need them most: small n, and p_hat near 0 or 1 (the accuracy range most
    eval suites live in once a system is any good).
    """
    p_hat = successes / n
    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    se = np.sqrt(p_hat * (1 - p_hat) / n)
    return p_hat - z * se, p_hat + z * se


def wilson_ci(successes: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Wilson score interval (Wilson, 1927).

    Instead of inverting the normal approximation around p_hat, it inverts
    the exact statement "how far can the true p be before p_hat becomes a
    surprising outcome" and solves the resulting quadratic in p. Net effect:
    the interval is automatically clipped to [0, 1], has near-nominal
    coverage even at small n, and does not collapse to a single point when
    p_hat is exactly 0 or 1 (Wald's does -- and a 0-width interval on 10
    examples is a lie, not a certainty).

    Formula (z = two-sided normal critical value):
        center = (p_hat + z^2/(2n)) / (1 + z^2/n)
        margin = z * sqrt(p_hat(1-p_hat)/n + z^2/(4n^2)) / (1 + z^2/n)
    """
    p_hat = successes / n
    z = stats.norm.ppf(1 - (1 - confidence) / 2)
    z2 = z * z
    denom = 1 + z2 / n
    center = (p_hat + z2 / (2 * n)) / denom
    margin = (z * np.sqrt(p_hat * (1 - p_hat) / n + z2 / (4 * n * n))) / denom
    return center - margin, center + margin


def _self_check_wilson() -> None:
    """Cross-check against the worked example on Wikipedia's Wilson score
    interval page: n=10, 8 successes, 95% CI ~= (0.49, 0.94)."""
    lo, hi = wilson_ci(8, 10, 0.95)
    assert abs(lo - 0.4902) < 5e-4 and abs(hi - 0.9434) < 5e-4, (lo, hi)


def ci_demo() -> None:
    rule("1. WILSON vs. NAIVE (WALD) CONFIDENCE INTERVAL")
    _self_check_wilson()
    print("  Formula self-check against a known reference value: PASSED\n")

    cases = [
        ("tiny eval, perfect score", 10, 10),
        ("tiny eval, near-perfect", 9, 10),
        ("typical eval slice", 36, 50),
        ("larger eval", 1440, 2000),
    ]
    print(f"  {'case':<28}{'n':>6}{'acc':>8}{'Wald 95% CI':>22}{'Wilson 95% CI':>22}")
    for name, k, n in cases:
        wa = wald_ci(k, n)
        wi = wilson_ci(k, n)
        print(f"  {name:<28}{n:>6}{k/n:>8.2%}"
              f"  [{wa[0]:>6.3f}, {wa[1]:>6.3f}]"
              f"    [{wi[0]:>6.3f}, {wi[1]:>6.3f}]")
    print("\n  Read the first row: 10/10 correct gives Wald a ZERO-WIDTH interval")
    print("  [1.000, 1.000] -- 'we are mathematically certain the true accuracy is")
    print("  100%' after ten examples. That is absurd on its face. Wilson gives")
    print("  [0.722, 1.000]: still good news, but honest about how little you")
    print("  actually know from 10 examples. This is why an eval report that only")
    print("  states a bare accuracy number, with no interval, should not be trusted.")


# --------------------------------------------------------------------------- #
# 2. McNemar's test -- the correct paired test for two systems, one eval set #
# --------------------------------------------------------------------------- #
def mcnemar_test(correct_a: np.ndarray, correct_b: np.ndarray) -> dict:
    """McNemar's test for paired binary outcomes (McNemar, 1947).

    You almost never want an unpaired test here. Prompt A and prompt B were
    graded on the SAME examples, so their scores are correlated (both find
    the easy examples easy). An unpaired test (e.g. a two-proportion z-test)
    throws that correlation away and is systematically underpowered relative
    to the paired alternative.

    McNemar's test looks ONLY at the discordant pairs -- examples where A and
    B disagree -- because examples where they agree carry no information
    about which one is better:

        b = # examples A got right and B got wrong
        c = # examples A got wrong and B got right

    Under H0 (A and B are equally good), b and c should each be about
    (b+c)/2. The continuity-corrected chi-square statistic is
        chi2 = (|b - c| - 1)^2 / (b + c),   df = 1
    For small b+c (< 25, the usual rule of thumb) the chi-square
    approximation is unreliable, so we use the exact two-sided binomial test
    of b against Binomial(b+c, 0.5) instead -- this is what statistical
    packages default to in that regime.
    """
    both_correct = int(np.sum(correct_a & correct_b))
    both_wrong = int(np.sum(~correct_a & ~correct_b))
    b = int(np.sum(correct_a & ~correct_b))   # A right, B wrong
    c = int(np.sum(~correct_a & correct_b))   # A wrong, B right
    n_discordant = b + c

    if n_discordant == 0:
        return dict(a_only=b, b_only=c, both_correct=both_correct, both_wrong=both_wrong,
                    method="degenerate (no discordant pairs)", statistic=0.0, p_value=1.0)

    if n_discordant < 25:
        # Exact binomial: is b surprising under Binomial(n_discordant, 0.5)?
        p_value = stats.binomtest(min(b, c), n_discordant, 0.5, alternative="two-sided").pvalue
        return dict(a_only=b, b_only=c, both_correct=both_correct, both_wrong=both_wrong,
                    method="exact binomial", statistic=float(min(b, c)), p_value=float(p_value))

    chi2 = (abs(b - c) - 1) ** 2 / n_discordant
    p_value = 1 - stats.chi2.cdf(chi2, df=1)
    return dict(a_only=b, b_only=c, both_correct=both_correct, both_wrong=both_wrong,
                method="chi-square (continuity corrected)", statistic=float(chi2), p_value=float(p_value))


def _self_check_mcnemar() -> None:
    """Two independent checks, one per branch.

    Exact branch: b=10, c=2 (12 discordant pairs, below the 25 threshold).
    scipy.stats.binomtest(2, 12, 0.5, two-sided) = 0.03857421875 -- this is
    the standard reference implementation of the exact sign test, used here
    only to validate the CALL, not the formula (there is no closed-form
    formula to hand-check for the exact test; that's the point of "exact").

    Chi-square branch: b=20, c=5 (25 discordant pairs, at/above threshold).
    Hand arithmetic: chi2 = (|20-5|-1)^2 / 25 = 14^2/25 = 7.84, and
    p = 1 - chi2.cdf(7.84, df=1) = 0.00511, which we also cross-check by
    hand via the df=1 identity p = 2*(1-Phi(sqrt(chi2))).
    """
    a1 = np.array([True] * 10 + [False] * 2 + [True] * 40 + [False] * 40)
    b1 = np.array([False] * 10 + [True] * 2 + [True] * 40 + [False] * 40)
    res1 = mcnemar_test(a1, b1)
    assert res1["a_only"] == 10 and res1["b_only"] == 2
    assert res1["method"] == "exact binomial"
    assert abs(res1["p_value"] - 0.03857421875) < 1e-6, res1["p_value"]

    a2 = np.array([True] * 20 + [False] * 5 + [True] * 37 + [False] * 38)
    b2 = np.array([False] * 20 + [True] * 5 + [True] * 37 + [False] * 38)
    res2 = mcnemar_test(a2, b2)
    assert res2["a_only"] == 20 and res2["b_only"] == 5
    assert res2["method"].startswith("chi-square")
    assert abs(res2["statistic"] - 7.84) < 1e-9, res2["statistic"]
    hand_p = 2 * (1 - stats.norm.cdf(np.sqrt(7.84)))
    assert abs(res2["p_value"] - hand_p) < 1e-9
    assert abs(res2["p_value"] - 0.005110) < 1e-5, res2["p_value"]


# --------------------------------------------------------------------------- #
# 3. Paired bootstrap -- for continuous (rubric / judge) scores              #
# --------------------------------------------------------------------------- #
def paired_bootstrap_ci(scores_a: np.ndarray, scores_b: np.ndarray,
                         n_boot: int = 10_000, confidence: float = 0.95) -> dict:
    """Bootstrap CI on the mean paired difference (B - A).

    Works for anything McNemar can't: continuous judge scores, rubric sums,
    RAGAS-style [0,1] metrics. Resample EXAMPLE INDICES (not the two score
    arrays independently) so the pairing -- and whatever correlation it
    carries -- survives into every resample.
    """
    n = len(scores_a)
    diffs = scores_b - scores_a
    observed = float(diffs.mean())
    idx = rng.integers(0, n, size=(n_boot, n))
    boot_means = diffs[idx].mean(axis=1)
    alpha = 1 - confidence
    lo, hi = np.percentile(boot_means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    p_value = float(2 * min((boot_means <= 0).mean(), (boot_means >= 0).mean()))
    return dict(observed_diff=observed, ci=(float(lo), float(hi)), p_value=min(p_value, 1.0))


def mcnemar_demo() -> None:
    rule("2. McNEMAR'S TEST -- PAIRED COMPARISON ON THE SAME EVAL SET")
    _self_check_mcnemar()
    print("  Formula self-check against a known textbook example: PASSED\n")

    print("  Two prompts graded on the SAME 30 examples:")
    a = np.array([True]*20 + [False]*10)                       # prompt A: 20/30
    b = np.array([True]*15 + [False]*5 + [True]*5 + [False]*5) # prompt B: 20/30, different mix
    res = mcnemar_test(a, b)
    print(f"    prompt A accuracy = {a.mean():.2%}   prompt B accuracy = {b.mean():.2%}  (tied!)")
    print(f"    A-right/B-wrong = {res['a_only']}   A-wrong/B-right = {res['b_only']}")
    print(f"    method = {res['method']}, p = {res['p_value']:.4f}")
    print("    Same accuracy, but WHICH examples each got right differs -- McNemar")
    print("    tells you whether that swap pattern is real or coin-flip noise.")

    print("\n  Continuous rubric scores (0-1), same 30 examples, paired bootstrap:")
    scores_a = rng.beta(6, 3, size=30)
    scores_b = scores_a + rng.normal(0.03, 0.05, size=30)   # small correlated bump
    boot = paired_bootstrap_ci(scores_a, scores_b)
    print(f"    mean(A) = {scores_a.mean():.3f}   mean(B) = {scores_b.mean():.3f}")
    print(f"    paired diff = {boot['observed_diff']:+.3f}   95% CI = "
          f"[{boot['ci'][0]:+.3f}, {boot['ci'][1]:+.3f}]   p ~= {boot['p_value']:.3f}")


# --------------------------------------------------------------------------- #
# 4. THE NUMBER EVERYONE GETS WRONG: 72% vs 74% at n=50 vs n=2000            #
# --------------------------------------------------------------------------- #
def simulate_paired_eval(n: int, acc_a: float, acc_b: float, agreement: float,
                          seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Simulate two models' correctness on the SAME n examples via a Gaussian
    copula, so each model has EXACTLY the target marginal accuracy (in
    expectation) while their per-example correctness is correlated.

    `agreement` (0..1) is the correlation between the two models' latent
    "did I get this one right" variables. In a real eval set this is high:
    both models nail the easy examples and stumble on the same hard ones.
    Treating the two accuracy estimates as independent throws that
    correlation away and understates your real statistical power -- another
    reason a paired test (McNemar) beats an unpaired one here.

    Construction: draw a shared latent factor and two independent factors,
    mix them by sqrt(rho)/sqrt(1-rho) so Corr(latent_a, latent_b) = rho, then
    threshold each (still marginally standard normal) at the z-score that
    gives the requested accuracy: P(latent > Phi^-1(1-acc)) = acc.
    """
    r = np.random.default_rng(seed)
    shared = r.normal(size=n)
    indiv_a = r.normal(size=n)
    indiv_b = r.normal(size=n)
    latent_a = np.sqrt(agreement) * shared + np.sqrt(1 - agreement) * indiv_a
    latent_b = np.sqrt(agreement) * shared + np.sqrt(1 - agreement) * indiv_b
    thresh_a = stats.norm.ppf(1 - acc_a)
    thresh_b = stats.norm.ppf(1 - acc_b)
    correct_a = latent_a > thresh_a
    correct_b = latent_b > thresh_b
    return correct_a, correct_b


def sample_size_demo() -> None:
    rule("3. SAMPLE SIZE IS NOT A DETAIL: 72% vs 74% AT n=50 vs n=2000")
    for n in (50, 2000):
        correct_a, correct_b = simulate_paired_eval(n, acc_a=0.72, acc_b=0.74,
                                                     agreement=0.6, seed=RANDOM_STATE)
        k_a, k_b = int(correct_a.sum()), int(correct_b.sum())
        wa = wilson_ci(k_a, n)
        wb = wilson_ci(k_b, n)
        mc = mcnemar_test(correct_a, correct_b)
        overlap = not (wa[1] < wb[0] or wb[1] < wa[0])
        print(f"\n  n = {n}")
        print(f"    prompt A: {k_a}/{n} = {k_a/n:.1%}   Wilson 95% CI = [{wa[0]:.3f}, {wa[1]:.3f}]")
        print(f"    prompt B: {k_b}/{n} = {k_b/n:.1%}   Wilson 95% CI = [{wb[0]:.3f}, {wb[1]:.3f}]")
        print(f"    CIs overlap: {overlap}")
        print(f"    McNemar ({mc['method']}): b={mc['a_only']} c={mc['b_only']}  p = {mc['p_value']:.4f}")
        verdict = "NOT statistically distinguishable" if mc["p_value"] >= 0.05 else "statistically SIGNIFICANT difference"
        print(f"    Verdict at alpha=0.05: {verdict}")
    print("\n  Same two true accuracies (72% vs 74%) both times. At n=50 the CIs")
    print("  swallow each other and McNemar can't reject 'these are the same prompt'.")
    print("  At n=2000 the exact same 2-point gap is unmistakable. The lesson is not")
    print("  'use more examples' in the abstract -- it's 'know your eval set's power")
    print("  before you trust a 2-point delta from it.' A rough rule of thumb: to")
    print("  reliably resolve a 2-point accuracy gap around 70-80%, you need roughly")
    print("  a few thousand examples, not fifty. Compute it, don't guess it.")


# --------------------------------------------------------------------------- #
# 5. p-hacking your own eval set                                             #
# --------------------------------------------------------------------------- #
def p_hacking_demo(n_examples: int = 50, n_variants: int = 40) -> None:
    rule("4. p-HACKING YOUR PROMPT AGAINST YOUR OWN EVAL SET")
    print(f"  Baseline prompt: true accuracy 70% on a {n_examples}-example eval set.")
    print(f"  We generate {n_variants} 'variant' prompts that are ACTUALLY IDENTICAL")
    print("  in true quality (70%) -- pure random rewording, zero real effect --")
    print("  score each against the SAME eval set, and keep whichever variant looks")
    print("  best. This is exactly what happens when you iterate a prompt by re-")
    print("  running it against one fixed 50-example set until the number goes up.\n")

    r = np.random.default_rng(7)
    baseline_correct = r.uniform(0, 1, n_examples) < 0.70
    baseline_acc = baseline_correct.mean()

    best_delta = -1.0
    best_p = 1.0
    significant_wins = 0
    for _ in range(n_variants):
        variant_correct = r.uniform(0, 1, n_examples) < 0.70   # same true quality
        mc = mcnemar_test(baseline_correct, variant_correct)
        delta = variant_correct.mean() - baseline_acc
        if mc["p_value"] < 0.05 and delta > 0:
            significant_wins += 1
        if delta > best_delta:
            best_delta = delta
            best_p = mc["p_value"]

    print(f"  Baseline accuracy: {baseline_acc:.1%}")
    print(f"  Of {n_variants} equally-good variants, {significant_wins} looked like a")
    print(f"  'significant improvement' (p < 0.05) purely from sampling noise.")
    print(f"  Best-looking variant: +{best_delta:.1%} accuracy, single-comparison p = {best_p:.4f}")
    print("\n  None of these variants are actually better. This is the same overfitting")
    print("  pathology as tuning hyperparameters against a small validation set in")
    print("  Module 01 -- except now the knob you're turning is prompt wording, and")
    print("  the fix is the same: hold out a locked test slice you touch rarely, widen")
    print("  the eval set, and correct for multiple comparisons (Bonferroni, or just")
    print("  distrust p-values produced by a search over many candidates).")


if __name__ == "__main__":
    ci_demo()
    mcnemar_demo()
    sample_size_demo()
    p_hacking_demo()
    print("\nDone. Now go re-read notes/02 section on statistical rigor.\n")
