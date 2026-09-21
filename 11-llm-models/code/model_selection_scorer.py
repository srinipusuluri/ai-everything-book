"""
Model selection scorer -- decision support, not a leaderboard.

The whole point of this script is section 1 of notes/02: define the task's constraints
FIRST, then score candidates against YOUR numbers (ideally measured on YOUR eval set,
see Module 15), never against a public leaderboard alone.

This is a transparent, editable weighted-criteria scorer:
  1. You define a TaskProfile: accuracy bar, latency budget, cost budget, context need,
     and hard compliance constraints.
  2. You define CandidateModels: EXAMPLE specs below, clearly labeled as illustrative.
     Replace every number with something you actually measured or verified.
  3. The scorer disqualifies anything that fails a hard constraint, then scores the
     survivors on a 0-100 scale per criterion, weighted by what THIS task cares about,
     and prints the full reasoning -- not just a final number. If you can't see why a
     model won, the score is not trustworthy.

    python code/model_selection_scorer.py

Requires: nothing but the standard library.

PRICES, LATENCIES AND ACCURACY NUMBERS BELOW ARE ILLUSTRATIVE EXAMPLES, NOT CURRENT
VENDOR DATA. Verify current specs (see notes/02 section 5 and resources/RESOURCES.md)
and, more importantly, replace `eval_accuracy` with a number from YOUR eval set before
trusting this for a real decision.
"""
from __future__ import annotations

from dataclasses import dataclass, field


def rule(t: str) -> None:
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


# --------------------------------------------------------------------------- #
# 1. Define the task profile. EDIT THIS for your real use case.               #
# --------------------------------------------------------------------------- #
@dataclass
class TaskProfile:
    name: str
    accuracy_bar: float          # minimum acceptable score on YOUR eval set, 0-1
    latency_budget_ms: int       # p95 acceptable response time
    cost_budget_per_req: float   # USD ceiling per request at your expected volume
    context_needed_tokens: int   # the ACTUAL tokens this task needs, not "as much as possible"
    requires_open_weights: bool = False     # e.g. must self-host for data residency
    requires_region: str | None = None      # e.g. "eu" -- must be servable in-region
    # Weights must sum to 1.0. Change these to reflect what THIS task cares about.
    weight_accuracy: float = 0.45
    weight_latency: float = 0.20
    weight_cost: float = 0.25
    weight_context_fit: float = 0.10


# --------------------------------------------------------------------------- #
# 2. Define candidate models. EXAMPLE SPECS -- replace with verified numbers. #
#    eval_accuracy should come from running your own eval set (Module 15),   #
#    not from a public leaderboard.                                          #
# --------------------------------------------------------------------------- #
@dataclass
class CandidateModel:
    name: str
    tier: str                    # "frontier" | "mid" | "small"
    is_open_weights: bool
    servable_regions: list[str]  # e.g. ["us", "eu"] -- regions you can actually deploy in
    eval_accuracy: float         # YOUR eval set score, 0-1 -- NOT a public benchmark score
    p95_latency_ms: int
    cost_per_req: float          # USD, at your expected input/output token mix
    max_context_tokens: int


CANDIDATES: list[CandidateModel] = [
    CandidateModel("frontier-flagship", "frontier", is_open_weights=False,
                   servable_regions=["us", "eu"], eval_accuracy=0.93,
                   p95_latency_ms=3800, cost_per_req=0.048, max_context_tokens=200_000),
    CandidateModel("mid-tier-balanced", "mid", is_open_weights=False,
                   servable_regions=["us", "eu"], eval_accuracy=0.88,
                   p95_latency_ms=1200, cost_per_req=0.009, max_context_tokens=200_000),
    CandidateModel("small-fast", "small", is_open_weights=False,
                   servable_regions=["us", "eu"], eval_accuracy=0.76,
                   p95_latency_ms=350, cost_per_req=0.0012, max_context_tokens=128_000),
    CandidateModel("open-weights-self-hosted", "mid", is_open_weights=True,
                   servable_regions=["us", "eu", "on-prem"], eval_accuracy=0.85,
                   p95_latency_ms=900, cost_per_req=0.006, max_context_tokens=128_000),
]


# --------------------------------------------------------------------------- #
# 3. Scoring -- transparent, per-criterion, with reasoning printed.           #
# --------------------------------------------------------------------------- #
@dataclass
class ScoreResult:
    candidate: CandidateModel
    disqualified: bool
    disqualify_reasons: list[str] = field(default_factory=list)
    accuracy_score: float = 0.0
    latency_score: float = 0.0
    cost_score: float = 0.0
    context_score: float = 0.0
    total: float = 0.0


def check_hard_constraints(task: TaskProfile, c: CandidateModel) -> list[str]:
    """Hard fails, not scored -- disqualification, because no weighting fixes these."""
    reasons = []
    if task.requires_open_weights and not c.is_open_weights:
        reasons.append("task requires open-weights (self-hosting/data-control); candidate is proprietary")
    if task.requires_region and task.requires_region not in c.servable_regions:
        reasons.append(f"candidate cannot be served in required region '{task.requires_region}'")
    if c.max_context_tokens < task.context_needed_tokens:
        reasons.append(f"context too small: needs {task.context_needed_tokens:,}, has {c.max_context_tokens:,}")
    if c.eval_accuracy < task.accuracy_bar:
        reasons.append(f"eval accuracy {c.eval_accuracy:.2f} below required bar {task.accuracy_bar:.2f}")
    return reasons


def score_candidate(task: TaskProfile, c: CandidateModel) -> ScoreResult:
    reasons = check_hard_constraints(task, c)
    if reasons:
        return ScoreResult(c, disqualified=True, disqualify_reasons=reasons)

    # Accuracy: linear reward for clearing the bar, capped at 100.
    # A model that just clears the bar scores lower than one with headroom to spare.
    headroom = max(0.0, c.eval_accuracy - task.accuracy_bar)
    accuracy_score = min(100.0, 60.0 + headroom * 400)  # clearing the bar = 60, generous headroom -> 100

    # Latency: 100 if well under budget, degrading linearly, 0 at 2x budget.
    ratio = c.p95_latency_ms / task.latency_budget_ms
    latency_score = max(0.0, 100.0 * (1.0 - max(0.0, ratio - 1.0)))

    # Cost: 100 at or under budget, degrading linearly, 0 at 3x budget (cost overruns
    # compound at volume, so we punish overruns harder than latency overruns).
    cratio = c.cost_per_req / task.cost_budget_per_req
    cost_score = max(0.0, 100.0 * (1.0 - max(0.0, cratio - 1.0) / 2.0))

    # Context fit: reward having enough context WITHOUT rewarding pointless excess --
    # a model with 100x the context you need is not "more correct," see notes/01 section 4.
    fit = task.context_needed_tokens / c.max_context_tokens
    context_score = 100.0 if fit >= 0.5 else 100.0 * (0.6 + 0.8 * fit)  # sweet spot, not "biggest wins"

    total = (accuracy_score * task.weight_accuracy
             + latency_score * task.weight_latency
             + cost_score * task.weight_cost
             + context_score * task.weight_context_fit)

    return ScoreResult(c, disqualified=False, accuracy_score=accuracy_score,
                       latency_score=latency_score, cost_score=cost_score,
                       context_score=context_score, total=total)


def rank(task: TaskProfile, candidates: list[CandidateModel]) -> list[ScoreResult]:
    results = [score_candidate(task, c) for c in candidates]
    results.sort(key=lambda r: (r.disqualified, -r.total))
    return results


# --------------------------------------------------------------------------- #
# Reporting -- show the reasoning, not just the number.                       #
# --------------------------------------------------------------------------- #
def report(task: TaskProfile, results: list[ScoreResult]) -> None:
    rule(f"TASK PROFILE: {task.name}")
    print(f"  accuracy bar >= {task.accuracy_bar:.2f}   latency budget <= {task.latency_budget_ms}ms p95")
    print(f"  cost budget <= ${task.cost_budget_per_req:.4f}/req   context needed >= {task.context_needed_tokens:,} tok")
    if task.requires_open_weights:
        print("  HARD CONSTRAINT: must be open-weights (self-hosted / data control)")
    if task.requires_region:
        print(f"  HARD CONSTRAINT: must be servable in region '{task.requires_region}'")
    print(f"  weights: accuracy={task.weight_accuracy} latency={task.weight_latency} "
          f"cost={task.weight_cost} context_fit={task.weight_context_fit}")

    rule("DISQUALIFIED CANDIDATES (hard constraints, not weighted -- no score can save these)")
    dq = [r for r in results if r.disqualified]
    if not dq:
        print("  none")
    for r in dq:
        print(f"  {r.candidate.name}:")
        for reason in r.disqualify_reasons:
            print(f"    - {reason}")

    rule("RANKED CANDIDATES (survivors only, highest total first)")
    survivors = [r for r in results if not r.disqualified]
    if not survivors:
        print("  No candidate survives the hard constraints. Widen the shortlist or")
        print("  relax a constraint deliberately -- do not silently ignore a disqualification.")
        return

    print(f"  {'rank':<5}{'model':<26}{'accuracy':>10}{'latency':>10}{'cost':>8}{'ctx-fit':>9}{'TOTAL':>8}")
    for i, r in enumerate(survivors, start=1):
        print(f"  {i:<5}{r.candidate.name:<26}{r.accuracy_score:>10.1f}{r.latency_score:>10.1f}"
              f"{r.cost_score:>8.1f}{r.context_score:>9.1f}{r.total:>8.1f}")

    best = survivors[0]
    rule(f"RECOMMENDATION: {best.candidate.name}")
    print(f"  Total score {best.total:.1f}/100, built from:")
    print(f"    accuracy  {best.accuracy_score:>6.1f} x weight {task.weight_accuracy} = "
          f"{best.accuracy_score * task.weight_accuracy:6.1f}  (eval accuracy {best.candidate.eval_accuracy:.2f} "
          f"vs bar {task.accuracy_bar:.2f})")
    print(f"    latency   {best.latency_score:>6.1f} x weight {task.weight_latency} = "
          f"{best.latency_score * task.weight_latency:6.1f}  ({best.candidate.p95_latency_ms}ms "
          f"vs budget {task.latency_budget_ms}ms)")
    print(f"    cost      {best.cost_score:>6.1f} x weight {task.weight_cost} = "
          f"{best.cost_score * task.weight_cost:6.1f}  (${best.candidate.cost_per_req:.4f} "
          f"vs budget ${task.cost_budget_per_req:.4f})")
    print(f"    ctx-fit   {best.context_score:>6.1f} x weight {task.weight_context_fit} = "
          f"{best.context_score * task.weight_context_fit:6.1f}  ({best.candidate.max_context_tokens:,} tok "
          f"available vs {task.context_needed_tokens:,} needed)")
    if len(survivors) > 1:
        gap = best.total - survivors[1].total
        print(f"\n  Margin over runner-up ({survivors[1].candidate.name}): {gap:.1f} points.")
        if gap < 5:
            print("  That margin is thin. A thin margin means: pilot BOTH on live-adjacent")
            print("  traffic (notes/02 section 1, step 4) before committing -- don't let a")
            print("  5-point weighted score alone decide a production dependency.")


# --------------------------------------------------------------------------- #
# Two worked examples showing HOW THE SAME CANDIDATES RANK DIFFERENTLY        #
# depending on what the task actually needs. This is the point of the tool:  #
# there is no context-free "best model."                                     #
# --------------------------------------------------------------------------- #
def scenario_latency_sensitive() -> None:
    task = TaskProfile(
        name="Real-time chat widget (user is watching a spinner)",
        accuracy_bar=0.80, latency_budget_ms=500, cost_budget_per_req=0.003,
        context_needed_tokens=4_000,
        weight_accuracy=0.35, weight_latency=0.35, weight_cost=0.25, weight_context_fit=0.05,
    )
    report(task, rank(task, CANDIDATES))


def scenario_compliance_constrained() -> None:
    task = TaskProfile(
        name="Regulated-industry document analysis (must self-host, EU data)",
        accuracy_bar=0.82, latency_budget_ms=5_000, cost_budget_per_req=0.05,
        context_needed_tokens=60_000,
        requires_open_weights=True, requires_region="eu",
        weight_accuracy=0.50, weight_latency=0.10, weight_cost=0.20, weight_context_fit=0.20,
    )
    report(task, rank(task, CANDIDATES))


def scenario_accuracy_critical() -> None:
    task = TaskProfile(
        name="High-stakes summarization reviewed downstream by a human",
        accuracy_bar=0.90, latency_budget_ms=8_000, cost_budget_per_req=0.10,
        context_needed_tokens=150_000,
        weight_accuracy=0.60, weight_latency=0.05, weight_cost=0.15, weight_context_fit=0.20,
    )
    report(task, rank(task, CANDIDATES))


if __name__ == "__main__":
    scenario_latency_sensitive()
    scenario_compliance_constrained()
    scenario_accuracy_critical()
    rule("NOW DO THIS WITH YOUR OWN NUMBERS")
    print("  1. Edit TaskProfile with your real accuracy bar, latency budget, cost budget,")
    print("     context need, and any hard compliance constraints.")
    print("  2. Edit CANDIDATES with models you've actually shortlisted, and replace")
    print("     eval_accuracy with a score from YOUR eval set (Module 15) -- not a")
    print("     public leaderboard number (see notes/01 section 3 on why).")
    print("  3. Re-run. If the winner changes when you nudge a weight by 0.05, the")
    print("     decision is close -- pilot before you commit, per notes/02 section 1.\n")
