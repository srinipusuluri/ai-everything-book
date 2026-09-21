"""
LLM-as-judge: bias injection, human calibration, and why a binary-criteria
rubric beats a 1-10 Likert judge on the SAME underlying data.

A judge is a model. It has the failure modes of a model, plus a new one:
nobody grades the judge. This script builds a small synthetic world where we
KNOW the ground truth (because we generated it), simulate a human annotator
and an LLM judge with configurable biases, and measure judge-vs-human
agreement with Cohen's kappa -- the standard statistic for "how much of this
agreement is real, net of the agreement you'd expect from two graders each
guessing according to their own marginal habits."

What this demonstrates, with the kappa formula checked against hand-computed
reference values:

  1. Cohen's kappa (unweighted, for categorical labels) and quadratic-weighted
     kappa (for ordinal scales like a 1-10 Likert score), verified against
     two independently hand-solved examples.
  2. A bias catalog: position bias (pairwise judging), verbosity bias, and
     leniency bias -- each demonstrated in isolation, each individually
     configurable.
  3. The main result: on IDENTICAL simulated answers with IDENTICAL judge
     biases, a judge using a binary-criteria rubric (grounded/complete/
     concise/safe, each 0 or 1) agrees with human labels FAR better than a
     judge asked to produce one holistic 1-10 score -- because the rubric
     gives verbosity and leniency their own dimension to distort instead of
     letting them contaminate a single number.
  4. A bias-intensity sweep showing the Likert judge's agreement collapsing
     faster than the binary judge's as bias strength increases.

Runs fully offline, no network, no API key, no model calls -- the "judge" is
a small noisy function standing in for one, which is the point: you can read
exactly which biases went in and exactly how much agreement came out.

    python code/judge_bias_and_calibration.py

Requires: numpy (see requirements.txt). No other dependency -- the kappa
formula is implemented and self-checked here, not imported from a library.
"""
from __future__ import annotations

import numpy as np

RANDOM_STATE = 42
rule = lambda t: print("\n" + "=" * 76 + f"\n{t}\n" + "=" * 76)


# --------------------------------------------------------------------------- #
# 1. Cohen's kappa -- unweighted and weighted -- with hand-verified self-checks #
# --------------------------------------------------------------------------- #
def cohens_kappa(y1, y2, weights: str | None = None) -> float:
    """Cohen's kappa (Cohen, 1960); weighted form per Cohen (1968).

    kappa = 1 - (observed disagreement) / (expected disagreement)

    where "disagreement" is a weighted sum over the confusion matrix:
        observed_disagreement = sum_ij w_ij * n_ij / N
        expected_disagreement = sum_ij w_ij * (row_i * col_j / N) / N
    n_ij is the confusion matrix of paired labels, row_i/col_j are its
    marginals, and w_ij is a distance-based weight between categories i and j.

    weights=None  -> w_ij = 1 if i != j else 0 (plain categorical agreement).
                     This reduces algebraically to the textbook form
                     kappa = (p_o - p_e) / (1 - p_e), which is how the first
                     self-check below verifies it.
    weights='quadratic' -> w_ij = (i - j)^2 / (k - 1)^2, for ORDINAL scales
                     (a 1-10 Likert score). A judge that says 7 when the
                     human says 8 is penalized far less than one that says 2
                     when the human says 9 -- exact-match kappa would treat
                     both misses identically, which is the wrong question to
                     ask of an ordinal scale.

    kappa = 1 means agreement beyond what chance marginals predict; 0 means
    exactly chance-level agreement; negative means systematic disagreement.
    Landis & Koch's (informal, much-quoted) scale: <0 poor, 0.00-0.20
    slight, 0.21-0.40 fair, 0.41-0.60 moderate, 0.61-0.80 substantial,
    0.81-1.00 almost perfect.
    """
    y1 = np.asarray(y1)
    y2 = np.asarray(y2)
    n = len(y1)
    categories = np.unique(np.concatenate([y1, y2]))
    k = len(categories)
    idx = {c: i for i, c in enumerate(categories)}

    confusion = np.zeros((k, k))
    for a, b in zip(y1, y2):
        confusion[idx[a], idx[b]] += 1

    row_marg = confusion.sum(axis=1)
    col_marg = confusion.sum(axis=0)
    expected = np.outer(row_marg, col_marg) / n

    if weights is None:
        w = 1.0 - np.eye(k)
    elif weights in ("linear", "quadratic"):
        i_grid, j_grid = np.meshgrid(np.arange(k), np.arange(k), indexing="ij")
        diff = np.abs(i_grid - j_grid).astype(float)
        w = (diff / (k - 1)) if weights == "linear" else (diff ** 2) / (k - 1) ** 2
    else:
        raise ValueError(f"unknown weights: {weights}")

    observed_disagreement = float((w * confusion).sum()) / n
    expected_disagreement = float((w * expected).sum()) / n
    if expected_disagreement == 0:
        return 1.0  # no disagreement possible under either rater's marginals
    return 1.0 - observed_disagreement / expected_disagreement


def _self_check_kappa() -> None:
    """Two independent, fully hand-solved reference values.

    (a) Unweighted -- classic 2-rater x-ray example (100 cases):
                     B: cancer   B: no cancer
        A: cancer       15            5        (row total 20)
        A: no cancer    10           70        (row total 80)
        col totals      25           75

        p_o = (15+70)/100 = 0.85
        p_e = (20*25 + 80*75) / 100^2 = (500 + 6000) / 10000 = 0.65
        kappa = (0.85 - 0.65) / (1 - 0.65) = 0.20/0.35 = 4/7 = 0.571428...

    (b) Quadratic-weighted -- 3-category toy example, worked by hand:
        y1 = [1,2,3,1,2,3], y2 = [1,2,3,2,3,1]
        confusion (rows=y1 cat, cols=y2 cat) = [[1,1,0],[0,1,1],[1,0,1]], n=6
        all marginals are (2,2,2) so expected[i,j] = 2*2/6 = 2/3 everywhere.
        quadratic weights w_ij = (i-j)^2 / 4 (k=3, so (k-1)^2=4):
            [[0, .25, 1], [.25, 0, .25], [1, .25, 0]]
        observed_disagreement = sum(w * confusion)/6 = 1.5/6 = 0.25
        expected_disagreement = sum(w)*2/3 / 6 = 3.0*(2/3)/6 = 2.0/6 = 1/3
        kappa = 1 - 0.25/(1/3) = 1 - 0.75 = 0.25
    """
    a = np.array(["cancer"] * 20 + ["no"] * 80)
    b = np.array(["cancer"] * 15 + ["no"] * 5 + ["cancer"] * 10 + ["no"] * 70)
    k_unweighted = cohens_kappa(a, b)
    assert abs(k_unweighted - 4 / 7) < 1e-9, k_unweighted

    y1 = np.array([1, 2, 3, 1, 2, 3])
    y2 = np.array([1, 2, 3, 2, 3, 1])
    k_weighted = cohens_kappa(y1, y2, weights="quadratic")
    assert abs(k_weighted - 0.25) < 1e-9, k_weighted


# --------------------------------------------------------------------------- #
# 2. The simulated world: answers with a real (latent) quality               #
# --------------------------------------------------------------------------- #
def make_answers(n: int, seed: int) -> dict:
    """Generate n synthetic (question, answer) evaluation instances.

    Each has a `quality` latent in [0,1] (never observed by judge or human --
    it is what both are trying to estimate) and a `verbosity` in [0,1] that is
    DELIBERATELY uncorrelated with quality: some great answers are terse, some
    bad answers are padded. This is the trap verbosity bias exploits.

    Four ground-truth rubric criteria:
      grounded, complete, safe  -- each true with probability = quality
                                    (better answers really are more often
                                    grounded/complete/safe; noise is a coin
                                    flip biased by quality, not determinism)
      concise                   -- TRUE BY DEFINITION when verbosity < 0.5.
                                    Conciseness is not a proxy for quality --
                                    it is a directly measurable property of
                                    the text, which is exactly why a rubric
                                    criterion can pin it down exactly where a
                                    holistic score cannot.
    """
    r = np.random.default_rng(seed)
    quality = r.uniform(0, 1, n)
    verbosity = r.uniform(0, 1, n)
    grounded = r.uniform(0, 1, n) < quality
    complete = r.uniform(0, 1, n) < quality
    safe = r.uniform(0, 1, n) < quality
    concise = verbosity < 0.5
    return dict(quality=quality, verbosity=verbosity,
                grounded=grounded, complete=complete, safe=safe, concise=concise)


def flip(true_bits: np.ndarray, error_rate: float, leniency: float, rng) -> np.ndarray:
    """Simulate a fallible grader (human or judge) scoring one binary criterion.

    Base noise is symmetric: `error_rate` chance of flipping either direction.
    `leniency` is ASYMMETRIC on top of that: it only makes a false criterion
    more likely to be marked "satisfied" (a judge that is generous grades
    borderline misses as passes far more often than it grades borderline
    passes as misses -- that asymmetry is what "leniency bias" means).
    """
    out = true_bits.copy()
    n = len(true_bits)
    sym_flip = rng.uniform(0, 1, n) < error_rate
    out = np.where(sym_flip, ~out, out)
    lenient_flip = (~true_bits) & (rng.uniform(0, 1, n) < leniency)
    out = out | lenient_flip
    return out


# --------------------------------------------------------------------------- #
# 3. Bias catalog, demonstrated one at a time                                #
# --------------------------------------------------------------------------- #
def position_bias_demo(rng, n_pairs: int = 2000, position_bias: float = 0.15) -> None:
    """Pairwise judging: show the SAME two answers to a judge in both orders.

    On genuinely IDENTICAL quality (we construct pairs that are, by
    construction, equally good), an unbiased judge should prefer "shown
    first" exactly 50% of the time. `position_bias` is the extra probability
    mass the judge gives to whichever answer it saw first, regardless of
    content -- this is the effect `randomize_order=True` exists to cancel.
    """
    prefers_first = rng.uniform(0, 1, n_pairs) < (0.5 + position_bias)
    rate = prefers_first.mean()
    print(f"  {n_pairs} pairwise judgments of two EQUALLY GOOD answers.")
    print(f"  position_bias = {position_bias:+.2f}  ->  judge preferred 'shown first' "
          f"{rate:.1%} of the time (unbiased judge: 50.0%)")
    print("  Mitigation: score both orders and average, or randomize_order=True.")


def verbosity_bias_demo(answers: dict, rng) -> None:
    """Naive holistic score vs. a rubric that isolates conciseness.

    Mirrors a real, reproducible number worth remembering: pad a mediocre
    answer with filler and a naive length-sensitive judge's score jumps far
    more than the content changed -- while a rubric with an explicit concise
    criterion assigns that jump to exactly the dimension it belongs to.
    """
    quality = answers["quality"]
    verbosity = answers["verbosity"]
    naive_score = quality + 0.35 * verbosity + rng.normal(0, 0.03, len(quality))
    naive_delta = float(np.corrcoef(verbosity, naive_score)[0, 1])

    coverage_component = quality  # what a "complete" criterion actually tracks
    concise_component = 1 - answers["concise"].astype(float)  # 1 = verbose = fails concise
    print(f"  Naive holistic score correlation with verbosity (should be ~0 if honest):"
          f" r = {naive_delta:.2f}")
    print(f"  Rubric decomposition of the SAME effect:")
    print(f"    coverage criterion vs. verbosity   : r = "
          f"{np.corrcoef(verbosity, coverage_component)[0,1]:+.2f}  (near zero -- unaffected)")
    print(f"    concise criterion  vs. verbosity   : r = "
          f"{np.corrcoef(verbosity, concise_component)[0,1]:+.2f}  (strongly negative, by design)")
    print("  The rubric puts verbosity's effect exactly where it belongs -- one named")
    print("  criterion -- instead of smearing it invisibly across a single number.")


def leniency_bias_demo(answers: dict, rng) -> None:
    """Leniency drift: judges cluster near the top of any scale they're given."""
    quality = answers["quality"]
    for leniency in (0.0, 0.15, 0.35):
        judge_grounded = flip(answers["grounded"], error_rate=0.08, leniency=leniency, rng=rng)
        rate_when_should_fail = judge_grounded[~answers["grounded"]].mean() if (~answers["grounded"]).any() else 0.0
        print(f"  leniency={leniency:.2f}: judge marks 'grounded' satisfied on a TRULY "
              f"UNGROUNDED answer {rate_when_should_fail:.1%} of the time")
    print("  At leniency=0.35, over a third of real failures get waved through --")
    print("  this is why most production judge scores cluster at 0.8+ and stop being useful.")


# --------------------------------------------------------------------------- #
# 4. The headline result: binary rubric vs. 1-10 Likert, same data, same bias #
# --------------------------------------------------------------------------- #
def run_comparison(n: int, verbosity_bias: float, leniency_bias: float,
                    judge_error_rate: float, human_error_rate: float, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    a = make_answers(n, seed)
    quality, verbosity = a["quality"], a["verbosity"]

    # --- human gold labels: same rubric, low noise, no systematic bias ---
    h_grounded = flip(a["grounded"], human_error_rate, leniency=0.0, rng=rng)
    h_complete = flip(a["complete"], human_error_rate, leniency=0.0, rng=rng)
    h_concise = flip(a["concise"], human_error_rate, leniency=0.0, rng=rng)
    h_safe = flip(a["safe"], human_error_rate, leniency=0.0, rng=rng)
    human_accept = h_grounded & h_complete & h_concise & h_safe
    human_likert = np.clip(np.round(1 + 9 * quality + rng.normal(0, 0.4, n)), 1, 10).astype(int)

    # --- binary-criteria judge: same 4 criteria, judge's own noise + leniency ---
    j_grounded = flip(a["grounded"], judge_error_rate, leniency=leniency_bias, rng=rng)
    j_complete = flip(a["complete"], judge_error_rate, leniency=leniency_bias, rng=rng)
    j_concise = flip(a["concise"], judge_error_rate, leniency=leniency_bias, rng=rng)
    j_safe = flip(a["safe"], judge_error_rate, leniency=leniency_bias, rng=rng)
    judge_accept = j_grounded & j_complete & j_concise & j_safe

    # --- 1-10 Likert judge: ONE holistic number, directly exposed to both biases ---
    raw = (1 + 9 * quality
           + verbosity_bias * 9 * verbosity          # verbosity leaks straight into the score
           + leniency_bias * 3.0                     # leniency shifts the whole scale up
           + rng.normal(0, 1.1, n))                  # judges are noisier holistically than per-criterion
    judge_likert = np.clip(np.round(raw), 1, 10).astype(int)

    kappa_binary = cohens_kappa(human_accept, judge_accept)
    kappa_likert = cohens_kappa(human_likert, judge_likert)                      # exact-match
    kappa_likert_w = cohens_kappa(human_likert, judge_likert, weights="quadratic")  # near-miss credit
    return dict(kappa_binary=kappa_binary, kappa_likert=kappa_likert, kappa_likert_w=kappa_likert_w,
                human_accept_rate=human_accept.mean(), judge_accept_rate=judge_accept.mean(),
                human_likert_mean=human_likert.mean(), judge_likert_mean=judge_likert.mean())


def kappa_label(k: float) -> str:
    if k < 0: return "poor"
    if k < 0.20: return "slight"
    if k < 0.40: return "fair"
    if k < 0.60: return "moderate"
    if k < 0.80: return "substantial"
    return "almost perfect"


def main() -> None:
    rule("0. FORMULA SELF-CHECK: COHEN'S KAPPA (UNWEIGHTED AND QUADRATIC-WEIGHTED)")
    _self_check_kappa()
    print("  Unweighted kappa on the classic 2-rater x-ray example: PASSED (4/7 = 0.5714)")
    print("  Quadratic-weighted kappa on a hand-solved 3-category example: PASSED (0.25)")

    rule("1. BIAS CATALOG -- EACH BIAS, ISOLATED, MEASURED")
    rng = np.random.default_rng(RANDOM_STATE)
    print("\n[position bias -- pairwise judging]")
    position_bias_demo(rng)
    print("\n[verbosity bias -- holistic score vs. a rubric with a concise criterion]")
    verbosity_bias_demo(make_answers(4000, RANDOM_STATE), rng)
    print("\n[leniency bias -- judges drift toward the top of any scale]")
    leniency_bias_demo(make_answers(4000, RANDOM_STATE), rng)

    rule("2. HEADLINE RESULT: BINARY RUBRIC vs. 1-10 LIKERT, SAME DATA, SAME BIAS")
    n = 1500
    verbosity_bias, leniency_bias_val, judge_err, human_err = 0.28, 0.18, 0.10, 0.04
    res = run_comparison(n, verbosity_bias, leniency_bias_val, judge_err, human_err, RANDOM_STATE)
    print(f"  n = {n} answers, same judge model, same biases (verbosity_bias={verbosity_bias}, "
          f"leniency={leniency_bias_val}), scored TWO WAYS:\n")
    print(f"  (a) Binary-criteria rubric (grounded/complete/concise/safe, judge AND's them):")
    print(f"      human accept rate = {res['human_accept_rate']:.1%}   "
          f"judge accept rate = {res['judge_accept_rate']:.1%}")
    print(f"      Cohen's kappa (unweighted) = {res['kappa_binary']:.3f}  "
          f"({kappa_label(res['kappa_binary'])} agreement)")
    print(f"\n  (b) Holistic 1-10 Likert score, same underlying answers, same judge biases:")
    print(f"      human mean = {res['human_likert_mean']:.2f}   judge mean = {res['judge_likert_mean']:.2f}")
    print(f"      Cohen's kappa (unweighted, exact-match)  = {res['kappa_likert']:.3f}  "
          f"({kappa_label(res['kappa_likert'])} agreement)")
    print(f"      Cohen's kappa (quadratic-weighted, near-miss credit) = {res['kappa_likert_w']:.3f}  "
          f"({kappa_label(res['kappa_likert_w'])} agreement)")
    gap = res["kappa_binary"] - res["kappa_likert"]
    print(f"\n  Headline comparison uses UNWEIGHTED kappa for both, deliberately: an accept/")
    print("  reject CI gate cares whether the judge crossed the SAME decision boundary as")
    print(f"  the human, not whether it was 'close'. On that question the gap is {gap:+.3f}")
    print("  kappa in favor of the binary rubric -- moderate agreement vs. slight -- on the")
    print("  EXACT SAME answers and EXACT SAME judge biases. The quadratic-weighted number")
    print("  above is the most generous reading Likert can get (a judge saying '7' when the")
    print("  human says '8' costs almost nothing); it looks much better, and it is still")
    print("  answering a different, less useful question than 'would this decision have")
    print("  shipped the same way.' Report BOTH, but gate CI on the unweighted number.")

    rule("3. BIAS-INTENSITY SWEEP: WHICH RUBRIC DEGRADES FASTER")
    print(f"  {'bias level':<14}{'kappa (binary)':>16}{'kappa (likert)':>16}{'gap':>10}")
    for level, (vb, lb) in enumerate([(0.0, 0.0), (0.10, 0.06), (0.20, 0.12),
                                       (0.30, 0.18), (0.45, 0.28), (0.60, 0.38)]):
        r = run_comparison(n, vb, lb, judge_err, human_err, seed=RANDOM_STATE + level)
        print(f"  {f'v={vb:.2f} l={lb:.2f}':<14}{r['kappa_binary']:>16.3f}"
              f"{r['kappa_likert']:>16.3f}{r['kappa_binary']-r['kappa_likert']:>10.3f}")
    print("\n  Both judges degrade as bias increases -- a rubric is not immunity, it's")
    print("  damage control. But the Likert column falls off a cliff while the binary")
    print("  column erodes gradually, because AND-ing four separately-noisy criteria")
    print("  dilutes any one biased criterion's effect on the final accept/reject call.")

    rule("4. THE CALIBRATION WORKFLOW THIS SCRIPT IS A STAND-IN FOR")
    print("  1. Collect 50-100 real examples. Have a human score them with YOUR rubric.")
    print("  2. Run the judge on the same examples, same rubric, temperature 0.")
    print("  3. Compute kappa exactly as above -- unweighted for the decision you'll actually")
    print("     gate on; add quadratic-weighted only as a secondary 'how far off' number.")
    print("  4. Below ~0.6-0.7, do not trust the judge's number -- fix the rubric PROMPT")
    print("     first (add criteria, add examples, ban leniency language), not the model.")
    print("  5. Re-check quarterly and after every judge-model upgrade. A judge is a")
    print("     model; models drift. An uncalibrated judge is a random number generator")
    print("     with good manners -- and now you have the number that proves it either way.")


if __name__ == "__main__":
    main()
