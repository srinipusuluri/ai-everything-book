"""
AI risk register — a working scoring tool for tiering AI use cases.

This is a GOVERNANCE TOOL, not an ML script: it implements the risk-tiering mechanic
described in notes/01-governance-fundamentals-and-frameworks.md #5 -- score four
attributes that predict harm (data sensitivity, decision autonomy, affected-population
size, reversibility of harm), combine them with transparent, adjustable weights, and
sort a portfolio of AI use cases into proportional-control tiers.

Design intent: you delete DEMO_USE_CASES and replace it with your own organization's
real use cases (or point --input at a JSON file shaped the same way). The scoring logic,
weights, and tier thresholds are the parts worth arguing about in your own governance
committee -- they are deliberately kept in one place, in plain sight, instead of buried.

Usage:
    python code/ai_risk_register_template.py --demo
    python code/ai_risk_register_template.py --demo --legend
    python code/ai_risk_register_template.py --input my_use_cases.json
    python code/ai_risk_register_template.py --demo --json > register.json

Requires: nothing but the Python 3.9+ standard library.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

# ----------------------------------------------------------------------------
# 1. THE FOUR RISK ATTRIBUTES
# ----------------------------------------------------------------------------
# Every attribute is scored 1 (lowest risk contribution) to 5 (highest).
# The scale definitions below are the part a real governance committee should
# argue about and adapt -- these are a reasonable, defensible starting point,
# not a standard.

SCALES: dict[str, dict[int, str]] = {
    "data_sensitivity": {
        1: "Public information / no personal data",
        2: "Internal business data, non-personal",
        3: "Personal data, non-sensitive (name, email, order history)",
        4: "Sensitive personal data (financial, employment, precise location)",
        5: "Special-category data (health, biometric, protected-class, children's data)",
    },
    "decision_autonomy": {
        1: "Advisory only -- a human makes every decision unaided",
        2: "Human reviews and approves every individual output before action (HITL)",
        3: "Human spot-checks a sample of outputs; most proceed unreviewed (HOTL)",
        4: "System acts automatically; human override is available after the fact",
        5: "System acts automatically with no practical human override",
    },
    "population_scale": {
        1: "A handful of internal users (< 50)",
        2: "One internal department or team",
        3: "A broad internal population, or a moderate external user base (thousands)",
        4: "A large customer base (hundreds of thousands)",
        5: "General public / systemic reach (millions, or safety-critical to any one person)",
    },
    "reversibility": {
        1: "Trivially reversible -- edit and resend, no lasting effect",
        2: "Reversible with minor effort (a correction, a refund)",
        3: "Reversible but costly or slow (a manual appeals process)",
        4: "Difficult to reverse (a hiring rejection, a credit denial that already damaged trust)",
        5: "Irreversible or severe (denied medical care, wrongful account termination, safety harm)",
    },
}

# Weights must sum to 1.0. Autonomy and reversibility are weighted heaviest on
# purpose: a system that can act on its own AND cause harm that can't be undone
# is the combination that actually produces catastrophic outcomes, more than
# either raw sensitivity or raw population size alone.
WEIGHTS: dict[str, float] = {
    "data_sensitivity": 0.20,
    "decision_autonomy": 0.30,
    "population_scale": 0.20,
    "reversibility": 0.30,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "WEIGHTS must sum to 1.0"

# Tier thresholds against the 0-100 scaled score. Tune these against your own
# committee's risk appetite -- they are policy, not physics.
TIERS: list[tuple[float, str, str, list[str]]] = [
    # (score_ceiling, tier_name, one_line_meaning, required_controls)
    (30.0, "Minimal", "Low harm potential on every axis.", [
        "Self-attestation by the owning team",
        "Logged in the AI use-case inventory",
        "Standard engineering practice: version control + basic evals suffices",
    ]),
    (50.0, "Limited", "Meaningful but bounded and/or reversible exposure.", [
        "Business-owner sign-off + AI inventory entry",
        "Lightweight model card",
        "Periodic spot-check monitoring",
    ]),
    (75.0, "High", "Individually consequential decisions at real scale or sensitivity.", [
        "AI governance committee review",
        "Model risk management (independent) validation",
        "Full model/system card with evaluation results",
        "Mandatory human-in-the-loop or human-on-the-loop oversight",
        "Quarterly re-assessment",
    ]),
    (float("inf"), "Critical", "High-autonomy and/or irreversible harm at meaningful scale.", [
        "Executive/board-level sign-off",
        "Independent or external validation",
        "Human-in-command design with a real, fast override authority",
        "Continuous monitoring with alerting",
        "Named accountable executive on record",
        "Incident response plan defined before launch",
    ]),
]


@dataclass
class AIUseCase:
    """One entry in the register. Attributes are 1-5 per the SCALES above."""
    name: str
    description: str
    owner: str
    data_sensitivity: int
    decision_autonomy: int
    population_scale: int
    reversibility: int
    notes: str = ""

    def __post_init__(self) -> None:
        for attr in WEIGHTS:
            v = getattr(self, attr)
            if not isinstance(v, int) or not (1 <= v <= 5):
                raise ValueError(
                    f"{self.name!r}: {attr}={v!r} must be an int in 1..5. "
                    f"See SCALES[{attr!r}] for the rubric."
                )


@dataclass
class ScoredUseCase:
    use_case: AIUseCase
    breakdown: dict[str, float]   # attribute -> weighted contribution (0-5 scale)
    raw_score: float              # sum of weighted contributions, 0-5
    score: float                  # raw_score scaled to 0-100
    tier: str
    tier_meaning: str
    required_controls: list[str]


# ----------------------------------------------------------------------------
# 2. SCORING
# ----------------------------------------------------------------------------
def score_use_case(uc: AIUseCase) -> ScoredUseCase:
    breakdown = {attr: getattr(uc, attr) * w for attr, w in WEIGHTS.items()}
    raw = sum(breakdown.values())          # max possible = 5.0
    scaled = round(raw * 20, 1)            # scale 0-5 -> 0-100
    for ceiling, tier, meaning, controls in TIERS:
        if scaled <= ceiling:
            return ScoredUseCase(uc, breakdown, raw, scaled, tier, meaning, controls)
    raise AssertionError("unreachable: TIERS ends with an infinite ceiling")


def build_register(use_cases: list[AIUseCase]) -> list[ScoredUseCase]:
    """Score every use case and return them sorted highest-risk first."""
    scored = [score_use_case(uc) for uc in use_cases]
    return sorted(scored, key=lambda s: s.score, reverse=True)


# ----------------------------------------------------------------------------
# 3. DEMO PORTFOLIO -- six realistic use cases, deliberately spanning all four
#    tiers so the differentiation is visible, not asserted.
# ----------------------------------------------------------------------------
DEMO_USE_CASES: list[AIUseCase] = [
    AIUseCase(
        name="Internal code assistant",
        description="LLM-based autocomplete/chat for engineers inside the corporate IDE.",
        owner="Developer Platform team",
        data_sensitivity=2,    # sees internal source, occasionally internal secrets in context
        decision_autonomy=1,   # suggestions only; a human reviews and commits every change
        population_scale=1,    # internal engineering org only
        reversibility=1,       # caught in code review / CI before it ships
        notes="Guardrail: secrets-scanning on prompts before they leave the org network.",
    ),
    AIUseCase(
        name="Marketing copy generator",
        description="Drafts ad copy and social captions for the marketing team to edit and post.",
        owner="Brand Marketing",
        data_sensitivity=1,    # no personal data involved
        decision_autonomy=1,   # a human always reviews and publishes
        population_scale=4,    # published copy reaches a large public audience
        reversibility=1,       # a bad draft is caught pre-publish; a rare bad post is correctable
        notes="Risk lives almost entirely in reach, not in autonomy or data -- the register should show that.",
    ),
    AIUseCase(
        name="Customer FAQ chatbot",
        description="Answers billing/product questions on the public website; escalates ambiguous cases to a human agent.",
        owner="Customer Support",
        data_sensitivity=1,    # public product info, no account data in this scope
        decision_autonomy=2,   # answers go straight to the customer without per-answer review
        population_scale=4,    # broad, public-facing customer base
        reversibility=1,       # a wrong FAQ answer is annoying, not damaging, and is easily corrected
        notes="Escalation path for account-specific requests keeps this out of the High tier.",
    ),
    AIUseCase(
        name="Fraud-detection transaction flagging",
        description="Scores transactions in real time; high-score transactions are held for manual review.",
        owner="Risk & Fraud Engineering",
        data_sensitivity=4,    # financial transaction data
        decision_autonomy=3,   # holds transactions automatically; a human reviews flagged ones, most legit ones flow through unreviewed
        population_scale=4,    # all customers' transactions pass through it
        reversibility=3,       # a false hold is recoverable but costs the customer time and trust
        notes="A false positive that blocks a real purchase during a family emergency is the case the committee should stress-test.",
    ),
    AIUseCase(
        name="Resume-screening tool",
        description="Ranks and auto-filters job applicants before a recruiter sees the pool.",
        owner="Talent Acquisition",
        data_sensitivity=4,    # employment data, proxies for protected characteristics
        decision_autonomy=4,   # auto-filters candidates out of the pool; recruiter never sees the rejected ones
        population_scale=3,    # applicant pool for the org's open roles
        reversibility=4,       # a wrongly filtered candidate has effectively lost the opportunity; very hard to undo
        notes="This is a canonical EU AI Act Annex III 'employment' high-risk use case -- see Module 14.",
    ),
    AIUseCase(
        name="Medical symptom triage assistant",
        description="Patient-facing tool that suggests urgency level (self-care / urgent care / ER) from reported symptoms.",
        owner="Digital Health Product",
        data_sensitivity=5,    # health data, special category
        decision_autonomy=4,   # gives an actionable urgency recommendation the patient may act on directly
        population_scale=3,    # patient population using the app
        reversibility=5,       # under-triaging a serious symptom can cause irreversible harm
        notes="Highest-scoring use case in this demo on purpose -- health + high autonomy + irreversibility is the worst-case combination.",
    ),
]


# ----------------------------------------------------------------------------
# 4. OUTPUT
# ----------------------------------------------------------------------------
def print_legend() -> None:
    print("=" * 78)
    print("RISK ATTRIBUTE SCALES (1 = lowest risk contribution, 5 = highest)")
    print("=" * 78)
    for attr, levels in SCALES.items():
        print(f"\n{attr}  (weight={WEIGHTS[attr]:.0%})")
        for level, desc in levels.items():
            print(f"  {level}  {desc}")
    print("\n" + "=" * 78)
    print("TIERS (score is 0-100, weighted sum of the four attributes)")
    print("=" * 78)
    lo = 0.0
    for ceiling, tier, meaning, controls in TIERS:
        hi = "100" if ceiling == float("inf") else f"{ceiling:.0f}"
        print(f"\n[{lo:>3.0f}-{hi}]  {tier} -- {meaning}")
        for c in controls:
            print(f"    - {c}")
        lo = ceiling + 0.1 if ceiling != float("inf") else lo


def print_register(register: list[ScoredUseCase]) -> None:
    print("=" * 96)
    print(f"{'RISK REGISTER (highest risk first)':^96}")
    print("=" * 96)
    header = f"{'Use case':<32} {'Owner':<24} {'Score':>6} {'Tier':<10}"
    print(header)
    print("-" * 96)
    for s in register:
        print(f"{s.use_case.name:<32} {s.use_case.owner:<24} {s.score:>6.1f} {s.tier:<10}")
    print("-" * 96)

    for s in register:
        print(f"\n{'#' * 78}")
        print(f"# {s.use_case.name}  --  score {s.score:.1f}/100  --  TIER: {s.tier.upper()}")
        print(f"{'#' * 78}")
        print(f"  Owner:       {s.use_case.owner}")
        print(f"  Description: {s.use_case.description}")
        print(f"  Meaning:     {s.tier_meaning}")
        print("\n  Score breakdown (attribute score x weight = contribution, out of 5.0 raw):")
        for attr, contribution in s.breakdown.items():
            raw_val = getattr(s.use_case, attr)
            print(f"    {attr:<18} {raw_val} x {WEIGHTS[attr]:.2f} = {contribution:.2f}"
                  f"   ({SCALES[attr][raw_val]})")
        print(f"    {'TOTAL':<18} {'':<9} = {s.raw_score:.2f}  ->  scaled {s.score:.1f}/100")
        print(f"\n  Required controls at this tier:")
        for c in s.required_controls:
            print(f"    - {c}")
        if s.use_case.notes:
            print(f"\n  Notes: {s.use_case.notes}")

    tiers_seen = {s.tier for s in register}
    print(f"\n{'=' * 96}")
    print(f"Tiers represented in this register: {', '.join(sorted(tiers_seen, key=lambda t: [c[1] for c in TIERS].index(t)))}")
    print("If every use case lands in the same tier, your weights or your inputs aren't discriminating --")
    print("that is a bug to fix, not a result to report to the committee.")


def register_to_json(register: list[ScoredUseCase]) -> str:
    payload = []
    for s in register:
        d = asdict(s.use_case)
        d.update({
            "score": s.score,
            "tier": s.tier,
            "tier_meaning": s.tier_meaning,
            "required_controls": s.required_controls,
            "breakdown": s.breakdown,
        })
        payload.append(d)
    return json.dumps(payload, indent=2)


def load_use_cases(path: Path) -> list[AIUseCase]:
    data = json.loads(path.read_text())
    return [AIUseCase(**entry) for entry in data]


# ----------------------------------------------------------------------------
# 5. CLI
# ----------------------------------------------------------------------------
def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Score and tier a portfolio of AI use cases into a prioritized risk register.")
    parser.add_argument("--demo", action="store_true",
                         help="Run against the 6 built-in example use cases.")
    parser.add_argument("--input", type=Path,
                         help="Path to a JSON file: a list of objects matching AIUseCase's fields.")
    parser.add_argument("--legend", action="store_true",
                         help="Print the scoring scales and tier definitions before the register.")
    parser.add_argument("--json", action="store_true",
                         help="Print the register as JSON instead of a formatted report.")
    args = parser.parse_args(argv)

    if not args.demo and not args.input:
        parser.print_help()
        print("\nNo use cases given. Pass --demo to see the tool work on 6 example use cases,")
        print("or --input path/to/use_cases.json with your own real ones.")
        return 1

    use_cases = list(DEMO_USE_CASES) if args.demo else []
    if args.input:
        use_cases += load_use_cases(args.input)

    if args.legend and not args.json:
        print_legend()
        print()

    register = build_register(use_cases)

    if args.json:
        print(register_to_json(register))
    else:
        print_register(register)

    return 0


if __name__ == "__main__":
    sys.exit(main())
