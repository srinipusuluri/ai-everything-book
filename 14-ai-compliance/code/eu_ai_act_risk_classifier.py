"""
EU AI Act risk-tier classifier -- a structured decision-support SCAFFOLD.

============================================================================
THIS IS EDUCATIONAL SCAFFOLDING, NOT LEGAL ADVICE. It implements a
SIMPLIFIED version of the Regulation (EU) 2024/1689 risk-tier logic for
teaching purposes: enough structure to make the *shape* of the reasoning
visible (which facts about a use case drive which tier, which obligations
follow), not enough nuance to be relied on for an actual classification
decision. Real classification requires reading the current text of Articles
5, 6, 50 and Annexes I/III, tracking amendments (see notes/01), and -- for
anything genuinely consequential -- a lawyer. See notes/01-regulatory-
landscape.md and notes/03-building-a-compliance-program.md #3 for how this
tool fits into a real workflow: it is the "what I think, ask counsel to
confirm or correct" starting draft, never the final answer.
============================================================================

Usage:
    python code/eu_ai_act_risk_classifier.py --demo
    python code/eu_ai_act_risk_classifier.py --demo --json > classifications.json
    python code/eu_ai_act_risk_classifier.py --input my_use_cases.json

Requires: nothing but the Python 3.9+ standard library.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

DISCLAIMER = (
    "EDUCATIONAL SCAFFOLDING, NOT LEGAL ADVICE. Simplified rules of thumb "
    "over a real, amended, multi-hundred-page regulation. Confirm any real "
    "classification with counsel and the current text -- see notes/01."
)

# ----------------------------------------------------------------------------
# 1. THE VOCABULARY THE CLASSIFIER REASONS OVER
# ----------------------------------------------------------------------------

# Article 5 prohibited practices (Tier 1). Presence of ANY of these flags is
# an automatic UNACCEPTABLE classification, full stop -- there is no
# "mostly fine" version of a prohibited practice.
PROHIBITED_PRACTICE_FLAGS: dict[str, str] = {
    "social_scoring":
        "Social scoring by/on behalf of a public authority across unrelated "
        "contexts, leading to disproportionate detrimental treatment (Art. 5(1)(c))",
    "subliminal_manipulation":
        "Subliminal or purposefully manipulative techniques that materially "
        "distort behavior and cause harm (Art. 5(1)(a))",
    "exploits_vulnerability":
        "Exploiting age, disability, or socio-economic vulnerability to "
        "materially distort behavior and cause harm (Art. 5(1)(b))",
    "biometric_categorization_protected_attributes":
        "Biometric categorization inferring race, political opinion, union "
        "membership, religion, or sexual orientation (Art. 5(1)(g))",
    "untargeted_facial_scraping":
        "Untargeted scraping of facial images (internet/CCTV) to build a "
        "facial-recognition database (Art. 5(1)(e))",
    "emotion_inference_workplace_or_school":
        "Inferring emotions in the workplace or in education, outside the "
        "narrow safety/medical exceptions (Art. 5(1)(f))",
    "realtime_biometric_id_law_enforcement":
        "Real-time remote biometric identification in publicly accessible "
        "spaces for law enforcement, outside narrow judicial exceptions (Art. 5(1)(h))",
}

# Annex III high-risk domains (Tier 2, use-based route). Annex I
# (product-safety route) is modeled separately below via a boolean flag.
ANNEX_III_DOMAINS: dict[str, str] = {
    "biometrics": "Annex III(1) -- Biometrics (remote ID, categorization, emotion recognition)",
    "critical_infrastructure": "Annex III(2) -- Critical infrastructure (safety components)",
    "education": "Annex III(3) -- Education (admissions, exam scoring, proctoring)",
    "employment": "Annex III(4) -- Employment (hiring, promotion, termination, monitoring)",
    "essential_services": "Annex III(5) -- Essential services (credit, insurance, benefits eligibility)",
    "law_enforcement": "Annex III(6) -- Law enforcement",
    "migration_border": "Annex III(7) -- Migration, asylum, border control",
    "justice_democratic": "Annex III(8) -- Administration of justice and democratic processes",
}

# Article 50 transparency triggers (Tier 3). Any one of these means
# disclosure is owed to someone, even with zero pre-market assessment.
TRANSPARENCY_TRIGGERS: dict[str, str] = {
    "chatbot_or_conversational_ai":
        "Directly interacts with a natural person (Art. 50(1)) -- must "
        "disclose it is AI unless obvious from context",
    "emotion_recognition_or_biometric_categorization":
        "Emotion-recognition or biometric-categorization system, not "
        "itself a prohibited practice (Art. 50(3)) -- must inform exposed persons",
    "synthetic_content_generation":
        "Generates synthetic audio/image/video/text (Art. 50(2)) -- output "
        "must be marked machine-readable/detectable as AI-generated",
    "deepfake":
        "Produces deepfake image/audio/video content (Art. 50(4)) -- must "
        "clearly disclose the content is artificially generated/manipulated",
}

VALID_AUTONOMY = {
    "advisory",                 # a human makes every decision unaided by system output
    "human_reviews_each",       # system proposes, human reviews and approves every instance
    "automatic_with_override",  # system acts automatically; human override exists after the fact
    "automatic_no_override",    # system acts automatically with no practical override
}

VALID_POPULATION = {"internal_small", "internal_large", "public"}


class Tier:
    UNACCEPTABLE = "UNACCEPTABLE (prohibited)"
    HIGH = "HIGH-RISK"
    LIMITED = "LIMITED RISK (transparency)"
    MINIMAL = "MINIMAL RISK"


# ----------------------------------------------------------------------------
# 2. THE USE CASE AND THE RESULT
# ----------------------------------------------------------------------------
@dataclass
class UseCase:
    name: str
    description: str
    domain: Optional[str] = None                      # key into ANNEX_III_DOMAINS, or None
    is_product_safety_component: bool = False          # Annex I route
    prohibited_flags: list[str] = field(default_factory=list)
    transparency_flags: list[str] = field(default_factory=list)
    decision_autonomy: str = "advisory"
    affected_population: str = "internal_small"
    disclosure_provided: bool = False                  # has the Art. 50 disclosure actually been implemented?
    claims_narrow_task_exception: bool = False          # Article 6(3) claim
    narrow_task_justification: str = ""

    def __post_init__(self) -> None:
        for flag in self.prohibited_flags:
            if flag not in PROHIBITED_PRACTICE_FLAGS:
                raise ValueError(f"{self.name!r}: unknown prohibited_flags entry {flag!r}")
        for flag in self.transparency_flags:
            if flag not in TRANSPARENCY_TRIGGERS:
                raise ValueError(f"{self.name!r}: unknown transparency_flags entry {flag!r}")
        if self.domain is not None and self.domain not in ANNEX_III_DOMAINS:
            raise ValueError(f"{self.name!r}: unknown domain {self.domain!r}")
        if self.decision_autonomy not in VALID_AUTONOMY:
            raise ValueError(f"{self.name!r}: decision_autonomy must be one of {sorted(VALID_AUTONOMY)}")
        if self.affected_population not in VALID_POPULATION:
            raise ValueError(f"{self.name!r}: affected_population must be one of {sorted(VALID_POPULATION)}")
        if self.claims_narrow_task_exception and not self.narrow_task_justification:
            raise ValueError(
                f"{self.name!r}: claims_narrow_task_exception=True requires a "
                f"narrow_task_justification string -- an undocumented exception "
                f"claim is not a real exception claim."
            )


@dataclass
class ClassificationResult:
    use_case: UseCase
    tier: str
    reasoning: list[str]
    obligations: list[str]
    matched_basis: str


# ----------------------------------------------------------------------------
# 3. THE CLASSIFICATION LOGIC
# ----------------------------------------------------------------------------
def classify(uc: UseCase) -> ClassificationResult:
    reasoning: list[str] = []

    # --- Step 1: Article 5 prohibited practices, checked first and absolute ---
    reasoning.append("Step 1 -- check Article 5 prohibited practices.")
    if uc.prohibited_flags:
        matched = [PROHIBITED_PRACTICE_FLAGS[f] for f in uc.prohibited_flags]
        reasoning.append(f"  MATCH: {'; '.join(matched)}")
        reasoning.append("  A prohibited practice was flagged. No amount of accuracy, "
                          "safeguards, or documentation creates a compliance path for this.")
        return ClassificationResult(
            use_case=uc,
            tier=Tier.UNACCEPTABLE,
            reasoning=reasoning,
            obligations=[
                "There is no compliance path. The obligation is: do not build or "
                "deploy this practice in the EU (or affecting EU persons).",
                "If already deployed, this is an incident -- escalate to legal/"
                "compliance leadership immediately, not a backlog item.",
                "Penalties for Article 5 violations are the Act's highest tier "
                "(verify the current figure -- historically discussed as up to "
                "EUR 35M or 7% of global annual turnover, whichever is higher; "
                "amounts can be revised by amendment).",
            ],
            matched_basis="Article 5 -- " + "; ".join(uc.prohibited_flags),
        )
    reasoning.append("  No match. Continue.")

    # --- Step 2: Annex I / Annex III high-risk routes ---
    reasoning.append("Step 2 -- check high-risk routes (Annex I product-safety, Annex III use-based).")
    annex_hit = None
    if uc.is_product_safety_component:
        annex_hit = "Annex I -- safety component of / itself a product already " \
                    "regulated under EU product-safety law"
    elif uc.domain is not None:
        annex_hit = ANNEX_III_DOMAINS[uc.domain]

    if annex_hit:
        reasoning.append(f"  MATCH: {annex_hit}")
        if uc.claims_narrow_task_exception:
            reasoning.append(
                "  A narrow-task exception (Article 6(3)) is CLAIMED, with "
                f"justification: \"{uc.narrow_task_justification}\""
            )
            reasoning.append(
                "  This classifier does NOT auto-downgrade on a claimed exception "
                "-- Article 6(3) is a judgment call the provider must document and "
                "be ready to defend to a regulator, not a self-service opt-out. "
                "Tier below is HIGH-RISK pending that documented, defensible "
                "assessment; treat it as provisional if you are relying on the "
                "exception."
            )
        reasoning.append(
            "  High-risk obligations attach regardless of how well the system "
            "performs -- this tier is about the DOMAIN and USE, not accuracy."
        )
        obligations = [
            "Risk management system across the full lifecycle (Art. 9) -- a "
            "living process, not a one-time form.",
            "Data governance: training/validation/test data quality, relevance, "
            "representativeness checks (Art. 10).",
            "Technical documentation sufficient for an authority to assess "
            "compliance (Art. 11, Annex IV) -- see code/compliance_documentation_"
            "mapper.py for which artifacts you likely already have.",
            "Automatic logging enabling traceability over the system's lifetime (Art. 12).",
            "Transparency instructions to deployers sufficient for them to meet "
            "their own duties (Art. 13).",
            "Human oversight: measures letting a human understand, monitor, and "
            "override the system (Art. 14) -- see ../12-ai-governance/.",
            "Accuracy, robustness, and cybersecurity: stated levels, tested, "
            "resilient to errors/attacks (Art. 15) -- see ../15-ai-evals/.",
            "Conformity assessment (self- or third-party via a notified body), "
            "CE marking, and EU database registration (Art. 16-17, 43, 49).",
            "Deployer duties (Art. 26): use per instructions, real human "
            "oversight in practice, monitor for known/foreseeable risks, and a "
            "fundamental rights impact assessment for certain public-sector / "
            "high-impact private uses.",
        ]
        return ClassificationResult(
            use_case=uc, tier=Tier.HIGH, reasoning=reasoning,
            obligations=obligations, matched_basis=annex_hit,
        )
    reasoning.append("  No match. Continue.")

    # --- Step 3: Article 50 transparency triggers ---
    reasoning.append("Step 3 -- check Article 50 transparency triggers.")
    if uc.transparency_flags:
        matched = [(f, TRANSPARENCY_TRIGGERS[f]) for f in uc.transparency_flags]
        for f, desc in matched:
            reasoning.append(f"  MATCH: {desc}")
        obligations = [f"Disclosure obligation: {desc}" for _, desc in matched]
        if uc.disclosure_provided:
            reasoning.append("  disclosure_provided=True -- the use case reports the "
                              "disclosure is already implemented.")
            obligations.append("STATUS: disclosure reported as implemented. Verify the "
                                "actual UX/label text against Art. 50's 'clear and "
                                "distinguishable' standard -- 'implemented' and "
                                "'compliant' are not automatically the same thing.")
        else:
            reasoning.append("  disclosure_provided=False -- GAP: the obligation exists "
                              "but has not been implemented yet.")
            obligations.append("GAP: no disclosure/marking has been implemented. This is "
                                "the single missing item standing between this system and "
                                "compliance at this tier -- prioritize it before launch.")
        reasoning.append("  No pre-market conformity assessment applies at this tier -- "
                          "disclosure IS the obligation, not a formality on top of one.")
        return ClassificationResult(
            use_case=uc, tier=Tier.LIMITED, reasoning=reasoning,
            obligations=obligations,
            matched_basis="Article 50 -- " + "; ".join(uc.transparency_flags),
        )
    reasoning.append("  No match. Continue.")

    # --- Step 4: fall through to minimal risk ---
    reasoning.append("Step 4 -- no prohibited practice, no high-risk domain, no "
                      "transparency trigger matched. Falls to minimal risk.")
    return ClassificationResult(
        use_case=uc, tier=Tier.MINIMAL, reasoning=reasoning,
        obligations=[
            "No obligations under the Act itself.",
            "The Act encourages (does not require) voluntary codes of conduct "
            "for this tier.",
            "Do not build compliance theater for a minimal-risk system -- spend "
            "that budget on anything that classified HIGH-RISK above.",
            "Re-classify if the use case's scope changes (e.g., an internal "
            "analytics tool later starts driving an automated employment "
            "decision -- that is a new classification, not a footnote).",
        ],
        matched_basis="none -- default tier",
    )


# ----------------------------------------------------------------------------
# 4. DEMO PORTFOLIO -- six use cases spanning all four tiers
# ----------------------------------------------------------------------------
DEMO_USE_CASES: list[UseCase] = [
    UseCase(
        name="Spam filter",
        description="Classifies inbound email as spam/not-spam for a consumer mailbox product.",
        domain=None,
        decision_autonomy="automatic_no_override",
        affected_population="public",
        transparency_flags=[],
    ),
    UseCase(
        name="Resume-screening tool",
        description="Ranks and auto-filters job applicants before a recruiter sees the shortlist.",
        domain="employment",
        decision_autonomy="automatic_with_override",
        affected_population="public",
    ),
    UseCase(
        name="Citizen social-scoring platform",
        description="A public-sector system that scores citizens' trustworthiness across unrelated "
                    "contexts (tax compliance, social media activity, traffic violations) and uses "
                    "the score to gate access to public services.",
        domain=None,
        prohibited_flags=["social_scoring"],
        decision_autonomy="automatic_no_override",
        affected_population="public",
    ),
    UseCase(
        name="Customer-service chatbot (with disclosure)",
        description="Public-facing support chatbot; opens every conversation with "
                    "'You're chatting with an AI assistant.'",
        domain=None,
        transparency_flags=["chatbot_or_conversational_ai"],
        disclosure_provided=True,
        decision_autonomy="automatic_with_override",
        affected_population="public",
    ),
    UseCase(
        name="Internal analytics dashboard",
        description="Summarizes internal sales/usage metrics for a product team using an LLM "
                    "over pre-aggregated, non-personal internal data.",
        domain=None,
        decision_autonomy="advisory",
        affected_population="internal_small",
    ),
    UseCase(
        name="Marketing deepfake video generator (no label yet)",
        description="Generates synthetic 'customer testimonial' videos of AI-voiced, AI-rendered "
                    "presenters for ad campaigns; ships today with no on-video disclosure.",
        domain=None,
        transparency_flags=["deepfake", "synthetic_content_generation"],
        disclosure_provided=False,
        decision_autonomy="automatic_no_override",
        affected_population="public",
    ),
]


# ----------------------------------------------------------------------------
# 5. OUTPUT
# ----------------------------------------------------------------------------
def rule(title: str) -> None:
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)


def print_result(r: ClassificationResult) -> None:
    print(f"\n{'#' * 90}")
    print(f"# {r.use_case.name}")
    print(f"{'#' * 90}")
    print(f"  Description: {r.use_case.description}")
    print(f"\n  Reasoning:")
    for line in r.reasoning:
        print(f"    {line}")
    print(f"\n  TIER: {r.tier}")
    print(f"  Matched basis: {r.matched_basis}")
    print(f"\n  Resulting obligations:")
    for o in r.obligations:
        print(f"    - {o}")


def print_summary(results: list[ClassificationResult]) -> None:
    rule("SUMMARY (this run)")
    header = f"{'Use case':<42} {'Tier':<28} {'Basis'}"
    print(header)
    print("-" * 110)
    for r in results:
        basis = r.matched_basis if len(r.matched_basis) < 36 else r.matched_basis[:33] + "..."
        print(f"{r.use_case.name:<42} {r.tier:<28} {basis}")
    tiers_seen = {r.tier for r in results}
    print(f"\nDistinct tiers produced: {len(tiers_seen)} of 4 possible.")
    if len(tiers_seen) < 2 and len(results) > 1:
        print("WARNING: every use case landed in the same tier -- that usually means "
              "your inputs (or the classifier) aren't discriminating. Check both.")


def results_to_json(results: list[ClassificationResult]) -> str:
    payload = []
    for r in results:
        d = asdict(r.use_case)
        d.update({"tier": r.tier, "reasoning": r.reasoning,
                  "obligations": r.obligations, "matched_basis": r.matched_basis})
        payload.append(d)
    return json.dumps(payload, indent=2)


def load_use_cases(path: Path) -> list[UseCase]:
    data = json.loads(path.read_text())
    return [UseCase(**entry) for entry in data]


# ----------------------------------------------------------------------------
# 6. CLI
# ----------------------------------------------------------------------------
def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Simplified, educational EU AI Act risk-tier classifier. NOT LEGAL ADVICE.")
    parser.add_argument("--demo", action="store_true",
                         help="Classify the 6 built-in example use cases.")
    parser.add_argument("--input", type=Path,
                         help="Path to a JSON file: a list of objects matching UseCase's fields.")
    parser.add_argument("--json", action="store_true",
                         help="Print machine-readable JSON instead of the narrated report.")
    args = parser.parse_args(argv)

    if not args.demo and not args.input:
        parser.print_help()
        print("\nNo use cases given. Pass --demo to see the tool work on 6 example "
              "use cases, or --input path/to/use_cases.json with your own.")
        return 1

    use_cases = list(DEMO_USE_CASES) if args.demo else []
    if args.input:
        use_cases += load_use_cases(args.input)

    results = [classify(uc) for uc in use_cases]

    if args.json:
        print(results_to_json(results))
        return 0

    print(DISCLAIMER)
    for r in results:
        print_result(r)
    print_summary(results)
    print(f"\n{DISCLAIMER}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
