"""
Compliance documentation mapper -- one artifact, many frameworks.

The single most expensive compliance mistake (see notes/03 #2) is building a
parallel paperwork trail *for compliance* on top of the documentation you
already produce *for engineering*. This tool makes the alternative visible:
it takes four artifacts a competent AI team already produces as normal
engineering discipline --

    1. Model card         (../12-ai-governance/)
    2. Eval report        (../15-ai-evals/)
    3. Trace / audit log  (../13-ai-security/, ../12-ai-governance/)
    4. Risk register entry(../12-ai-governance/)

-- and shows which requirements across THREE frameworks (EU AI Act Annex IV
technical documentation, ISO/IEC 42001 Annex A evidence, SOC 2 evidence for
an AI feature) each artifact already satisfies, fully or partially.

EDUCATIONAL SCAFFOLDING, NOT LEGAL/AUDIT ADVICE. Real Annex IV sign-off, ISO
42001 certification, and SOC 2 attestation are performed by qualified
assessors against the current standard text and your actual evidence -- this
tool teaches the MAPPING HABIT (one artifact, many audiences), not a
substitute for an audit.

Usage:
    python code/compliance_documentation_mapper.py
    python code/compliance_documentation_mapper.py --json > mapping.json

Requires: nothing but the Python 3.9+ standard library.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from typing import Optional

DISCLAIMER = (
    "EDUCATIONAL SCAFFOLDING, NOT LEGAL/AUDIT ADVICE. This is a teaching map of "
    "artifact-to-requirement overlap, not an Annex IV sign-off, an ISO 42001 "
    "certification decision, or a SOC 2 opinion. See notes/03."
)

ARTIFACTS: dict[str, str] = {
    "model_card": "Model card (Module 12 -- AI Governance)",
    "eval_report": "Eval report (Module 15 -- AI Evaluation)",
    "trace_log": "Trace / audit log (Module 13 -- AI Security, Module 12)",
    "risk_register": "Risk register entry (Module 12 -- AI Governance)",
}

FULL, PARTIAL, NONE_ = "full", "partial", "none"
SYMBOL = {FULL: "X", PARTIAL: "~", NONE_: "."}


@dataclass
class Requirement:
    framework: str
    ref: str            # article/clause/criterion reference
    requirement: str     # plain-language description
    covers: dict[str, str] = field(default_factory=dict)   # artifact_key -> full/partial/none
    note: str = ""


REQUIREMENTS: list[Requirement] = [
    # ---------------- EU AI Act -- Annex IV technical documentation ----------------
    Requirement(
        "EU AI Act (Annex IV)", "IV.1",
        "General description: intended purpose, versions, how it interacts with hardware/other software",
        {"model_card": FULL, "eval_report": NONE_, "trace_log": NONE_, "risk_register": PARTIAL},
        "A model card's 'intended use / out-of-scope use' section is written for exactly this question.",
    ),
    Requirement(
        "EU AI Act (Annex IV)", "IV.2",
        "Detailed design: architecture, algorithmic choices, key design decisions and their rationale",
        {"model_card": FULL, "eval_report": NONE_, "trace_log": NONE_, "risk_register": NONE_},
        "",
    ),
    Requirement(
        "EU AI Act (Annex IV)", "IV.3",
        "Data governance: training/validation/test data provenance, quality, representativeness",
        {"model_card": FULL, "eval_report": PARTIAL, "trace_log": NONE_, "risk_register": NONE_},
        "Eval reports add a partial contribution when they include bias-slice / subgroup breakdowns.",
    ),
    Requirement(
        "EU AI Act (Annex IV)", "IV.4",
        "Human oversight measures designed into the system",
        {"model_card": PARTIAL, "eval_report": NONE_, "trace_log": PARTIAL, "risk_register": FULL},
        "A risk register entry's control list is the authoritative source; logs prove oversight happened in practice.",
    ),
    Requirement(
        "EU AI Act (Annex IV)", "IV.5",
        "Accuracy, robustness, cybersecurity: appropriate levels, stated and tested",
        {"model_card": PARTIAL, "eval_report": FULL, "trace_log": NONE_, "risk_register": PARTIAL},
        "This is the eval report's entire reason for existing -- see ../15-ai-evals/.",
    ),
    Requirement(
        "EU AI Act (Annex IV)", "IV.6",
        "Risk management system: identified risks, mitigations, residual risk",
        {"model_card": PARTIAL, "eval_report": PARTIAL, "trace_log": NONE_, "risk_register": FULL},
        "",
    ),
    Requirement(
        "EU AI Act (Art. 12)", "Art.12",
        "Automatic logging enabling traceability over the system's lifetime",
        {"model_card": NONE_, "eval_report": NONE_, "trace_log": FULL, "risk_register": NONE_},
        "There is no substitute artifact for this one -- if you don't have logs, you don't have this requirement.",
    ),
    Requirement(
        "EU AI Act (Art. 13)", "Art.13",
        "Instructions for use sufficient for a deployer to meet their own duties",
        {"model_card": FULL, "eval_report": PARTIAL, "trace_log": NONE_, "risk_register": NONE_},
        "",
    ),

    # ---------------- ISO/IEC 42001 -- Annex A evidence ----------------
    Requirement(
        "ISO/IEC 42001 (Annex A)", "A.2/A.3",
        "AI policy and objectives, with roles/responsibilities assigned",
        {"model_card": NONE_, "eval_report": NONE_, "trace_log": NONE_, "risk_register": PARTIAL},
        "Policy artifacts live above the per-system level -- these four don't cover it; see ../12-ai-governance/.",
    ),
    Requirement(
        "ISO/IEC 42001 (Annex A)", "A.6",
        "AI system impact assessment performed before deployment",
        {"model_card": PARTIAL, "eval_report": PARTIAL, "trace_log": NONE_, "risk_register": FULL},
        "",
    ),
    Requirement(
        "ISO/IEC 42001 (Annex A)", "A.7",
        "Data for AI systems: quality, provenance, and management processes",
        {"model_card": FULL, "eval_report": PARTIAL, "trace_log": NONE_, "risk_register": NONE_},
        "",
    ),
    Requirement(
        "ISO/IEC 42001 (Annex A)", "A.9",
        "Third-party / supplier relationships involving AI (vendor models, data vendors)",
        {"model_card": PARTIAL, "eval_report": NONE_, "trace_log": NONE_, "risk_register": PARTIAL},
        "A model card that documents 'built on vendor model X, version Y' covers part of this; full coverage needs a vendor record these four don't include.",
    ),
    Requirement(
        "ISO/IEC 42001 (Clause 9)", "Cl.9",
        "Performance evaluation: monitoring, measurement, analysis of the AI system",
        {"model_card": NONE_, "eval_report": FULL, "trace_log": PARTIAL, "risk_register": PARTIAL},
        "",
    ),
    Requirement(
        "ISO/IEC 42001 (Clause 10)", "Cl.10",
        "Nonconformity and corrective action / continual improvement",
        {"model_card": NONE_, "eval_report": PARTIAL, "trace_log": PARTIAL, "risk_register": FULL},
        "An incident logged in the risk register with a remediation date is exactly this evidence.",
    ),

    # ---------------- SOC 2 -- evidence for an AI feature ----------------
    Requirement(
        "SOC 2 (Security)", "CC6",
        "Access control over model endpoints and training/eval data",
        {"model_card": NONE_, "eval_report": NONE_, "trace_log": PARTIAL, "risk_register": NONE_},
        "Access logs partially evidence control existence; the control design itself lives in infra config, outside these four.",
    ),
    Requirement(
        "SOC 2 (Security)", "CC8",
        "Change management for model/prompt updates, mirroring code-deployment controls",
        {"model_card": PARTIAL, "eval_report": PARTIAL, "trace_log": PARTIAL, "risk_register": NONE_},
        "A versioned model card plus a re-run eval report per release is strong change-management evidence together.",
    ),
    Requirement(
        "SOC 2 (Security)", "CC7",
        "Logging of AI-driven decisions sufficient to reconstruct what happened",
        {"model_card": NONE_, "eval_report": NONE_, "trace_log": FULL, "risk_register": NONE_},
        "",
    ),
    Requirement(
        "SOC 2 (Security)", "CC9",
        "Vendor-management record for any third-party model API",
        {"model_card": PARTIAL, "eval_report": NONE_, "trace_log": NONE_, "risk_register": PARTIAL},
        "",
    ),
    Requirement(
        "SOC 2 (Security)", "CC7.3",
        "Incident-response plan covering AI-specific failure modes (data leakage, prompt injection)",
        {"model_card": NONE_, "eval_report": PARTIAL, "trace_log": PARTIAL, "risk_register": FULL},
        "Adversarial/red-team eval results plus a risk register mitigation plan are the substance here.",
    ),
]


# ----------------------------------------------------------------------------
# Output
# ----------------------------------------------------------------------------
def rule(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def print_matrix(reqs: list[Requirement]) -> None:
    rule("COVERAGE MATRIX -- one row per requirement, one column per artifact")
    print("Legend: X = fully satisfies this requirement on its own   "
          "~ = partial evidence, needs another artifact too   . = no coverage\n")
    art_keys = list(ARTIFACTS.keys())
    col_w = max(len(k) for k in art_keys) + 2
    header = f"{'Framework':<26}{'Ref':<10}{'Requirement':<58}" + "".join(f"{k:>{col_w}}" for k in art_keys)
    print(header)
    print("-" * len(header))
    current_framework = None
    for r in reqs:
        fw_label = r.framework if r.framework != current_framework else ""
        current_framework = r.framework
        req_text = r.requirement if len(r.requirement) < 56 else r.requirement[:53] + "..."
        row = f"{fw_label:<26}{r.ref:<10}{req_text:<58}"
        row += "".join(f"{SYMBOL[r.covers.get(k, NONE_)]:>{col_w}}" for k in art_keys)
        print(row)
    print("-" * len(header))
    print("Columns: " + "  |  ".join(f"{k} = {v}" for k, v in ARTIFACTS.items()))


def print_leverage_summary(reqs: list[Requirement]) -> None:
    rule("CROSS-FRAMEWORK LEVERAGE -- what each artifact buys you, alone")
    for key, label in ARTIFACTS.items():
        full_hits = [(r.framework, r.ref, r.requirement) for r in reqs if r.covers.get(key) == FULL]
        partial_hits = [(r.framework, r.ref, r.requirement) for r in reqs if r.covers.get(key) == PARTIAL]
        frameworks_touched = {r.framework for r in reqs if r.covers.get(key) in (FULL, PARTIAL)}
        print(f"\n{label}")
        print(f"  Fully satisfies {len(full_hits)} requirement(s) across "
              f"{len({f for f, _, _ in full_hits})} framework(s), contributes "
              f"partially to {len(partial_hits)} more, touching "
              f"{len(frameworks_touched)} framework(s) total:")
        for fw, ref, text in full_hits:
            print(f"    [FULL]    {fw:<26} {ref:<8} {text}")
        for fw, ref, text in partial_hits:
            print(f"    [partial] {fw:<26} {ref:<8} {text}")

    rule("THE POINT")
    total = len(reqs)
    fully_covered = sum(1 for r in reqs if any(v == FULL for v in r.covers.values()))
    all_four = sum(1 for r in reqs
                   if sum(1 for v in r.covers.values() if v != NONE_) >= 3)
    thin = [r for r in reqs
            if not any(v == FULL for v in r.covers.values())
            and sum(1 for v in r.covers.values() if v == PARTIAL) <= 1]
    print(f"{fully_covered}/{total} requirements across all three frameworks are FULLY "
          f"satisfied by at least one of these four engineering artifacts, no new "
          f"paperwork required.")
    print(f"{all_four}/{total} requirements are touched (fully or partially) by THREE OR "
          f"MORE of these four artifacts simultaneously -- that overlap is exactly why "
          f"'build one artifact set, map it to every audience' beats parallel paperwork.")
    print(f"\n{len(thin)}/{total} requirements have only thin coverage (no full hit, at "
          f"most one partial) -- these are the real gaps, where the fix is a new/upgraded "
          f"artifact, not a creative re-reading of an existing one:")
    for r in thin:
        print(f"    {r.framework:<26} {r.ref:<8} {r.requirement}")


def matrix_to_json(reqs: list[Requirement]) -> str:
    return json.dumps([asdict(r) for r in reqs], indent=2)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Map governance/eval artifacts to EU AI Act / ISO 42001 / SOC 2 requirements.")
    parser.add_argument("--json", action="store_true", help="Print the raw mapping as JSON.")
    args = parser.parse_args(argv)

    if args.json:
        print(matrix_to_json(REQUIREMENTS))
        return 0

    print(DISCLAIMER)
    print_matrix(REQUIREMENTS)
    print_leverage_summary(REQUIREMENTS)
    print(f"\n{DISCLAIMER}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
