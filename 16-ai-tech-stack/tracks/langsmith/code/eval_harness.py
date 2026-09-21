#!/usr/bin/env python3
"""
eval_harness.py — an offline reimplementation of LangSmith's evaluate() loop.

WHY THIS EXISTS
    `langsmith.evaluate()` needs an account, a dataset UUID and network. The
    *shape* of it needs none of those. This file is that shape:

        Example            -> inputs + reference_outputs + split + metadata
        Dataset            -> a list of Examples, versioned
        target function    -> inputs dict -> outputs dict   (your app)
        evaluator          -> (inputs, outputs, reference_outputs) -> {key, score, comment}
        summary evaluator  -> whole-experiment metrics (pass rate, p95 latency)
        experiment         -> one (app version x dataset) run, with all scores
        pairwise           -> compare two experiments, with randomize_order
        regression gate    -> this experiment vs. a stored baseline, in CI

    The evaluator signature is deliberately identical to the real one, so the
    functions you write here paste straight into a LangSmith project.

WHAT IT DEMONSTRATES
    1. Exact match is nearly useless on free text. You will watch it score 0.
    2. A naive "longer answer is better" judge prefers v2 on every example.
       That is *verbosity bias*, reproduced deterministically, no LLM required.
    3. A rubric judge with explicit criteria disagrees with the naive judge.
    4. A quality win can still be a shipping blocker if it costs 3x more.
    5. A CI gate needs BOTH absolute floors and regression deltas.

RUN IT
    python eval_harness.py                     # evaluate v2 against the v1 baseline
    python eval_harness.py --update-baseline    # re-record the baseline from v1
    python eval_harness.py --strict             # exit(1) when the gate fails (CI mode)

    No network. No API key. Standard library only (3.10+).

    Theory lives in ../../../15-ai-evals/. This file is the plumbing.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

BASELINE_PATH = Path(__file__).with_name("baseline.json")


# ---------------------------------------------------------------------------
# 1. The dataset — harvested from production traces, which is the only good source
# ---------------------------------------------------------------------------
@dataclass
class Example:
    id: str
    inputs: dict[str, Any]
    reference_outputs: dict[str, Any]
    split: str = "regression"
    metadata: dict[str, Any] = field(default_factory=dict)


# Every `source` below is a trace id. That is the point: you do not invent an
# eval set in a meeting, you harvest it from the runs that already embarrassed
# you. Thumbs-down feedback, tool errors, and high-latency outliers are the
# three filters that build a dataset worth having.
DATASET: list[Example] = [
    Example("ex-01", {"question": "how long do refunds take?"},
            {"answer": "5-7 business days to the original payment method.",
             "must_include": ["5-7", "original payment"], "must_not_include": ["guarantee"]},
            split="smoke", metadata={"source": "trace:8d5aed7d", "reason": "thumbs_down"}),
    Example("ex-02", {"question": "when does express shipping arrive?"},
            {"answer": "Next business day if ordered before 2pm.",
             "must_include": ["next-day", "2pm"], "must_not_include": ["guarantee"]},
            split="smoke", metadata={"source": "trace:1ac13902", "reason": "thumbs_down"}),
    Example("ex-03", {"question": "is my laptop still under warranty after 14 months?"},
            {"answer": "No. The limited warranty runs 12 months from delivery.",
             "must_include": ["12-month", "delivery"], "must_not_include": ["yes, it is covered"]},
            metadata={"source": "trace:c11a9f30", "reason": "wrong_answer"}),
    Example("ex-04", {"question": "can you refund me in cash?"},
            {"answer": "No. Refunds go back to the original payment method only.",
             "must_include": ["original payment"], "must_not_include": ["cash refund available"]},
            metadata={"source": "trace:4b7e2201", "reason": "policy_violation"}),
    Example("ex-05", {"question": "where is order ORD-4417?"},
            {"answer": "Order status is temporarily unavailable; try again shortly.",
             "must_include": ["unavailable"], "must_not_include": ["delivered"]},
            metadata={"source": "trace:8d5aed7d", "reason": "tool_error"}),
    Example("ex-06", {"question": "do you ship to Norway?"},
            {"answer": "International shipping is not covered by the published policy.",
             "must_include": ["not covered"], "must_not_include": ["yes, 3-5 business days"]},
            metadata={"source": "trace:9f0c1d84", "reason": "out_of_scope"}),
    Example("ex-07", {"question": "standard shipping time?"},
            {"answer": "3-5 business days.",
             "must_include": ["3-5"], "must_not_include": ["overnight"]},
            split="smoke", metadata={"source": "trace:2b8dd53b", "reason": "sampled_healthy"}),
    Example("ex-08", {"question": "what is the refund window and the standard shipping time?"},
            {"answer": "Refunds take 5-7 business days; standard shipping is 3-5 business days.",
             "must_include": ["5-7", "3-5"], "must_not_include": ["guarantee"]},
            metadata={"source": "trace:71ab33c9", "reason": "multi_intent"}),
    Example("ex-09", {"question": "express shipping and warranty length?"},
            {"answer": "Express is next-day before 2pm; the warranty is 12 months from delivery.",
             "must_include": ["next-day", "12-month"], "must_not_include": ["lifetime"]},
            metadata={"source": "trace:71ab33c9", "reason": "multi_intent"}),
]


# ---------------------------------------------------------------------------
# 2. Two versions of the app under test (the "target function")
# ---------------------------------------------------------------------------
# A target takes `inputs` and returns `outputs`. Anything else on the dict --
# latency, cost, tokens -- is fair game for an evaluator to read. In real
# LangSmith these come off the run tree instead of the return value.
FACTS = {
    "refund": "Refunds are returned to the original payment method in 5-7 business days.",
    "express": "Express shipping arrives next-day when ordered before 2pm.",
    "warranty": "The 12-month limited warranty starts at delivery, so 14 months is out of cover.",
    "cash": "Refunds go to the original payment method; we cannot issue cash.",
    "order": "Order status is temporarily unavailable right now.",
    "intl": "International destinations are not covered by the published shipping policy.",
    "standard": "Standard shipping takes 3-5 business days.",
}

# Illustrative blended USD per 1M tokens. Replace with your provider's numbers;
# the ratio between the tiers is what drives every decision below.
PRICE_SMALL, PRICE_FRONTIER = 0.90, 18.00

ROUTES = [("refund", ("refund",)), ("express", ("express",)), ("warranty", ("warranty",)),
          ("cash", ("cash",)), ("order", ("ord-", "order")), ("intl", ("norway", "ship to")),
          ("standard", ("standard",))]


def _route(q: str) -> list[str]:
    q = q.lower()
    return [k for k, kws in ROUTES if any(w in q for w in kws)]


def app_v1(inputs: dict) -> dict:
    """Baseline: terse prompt, small model. Cheap, fast, occasionally incomplete."""
    rng = random.Random(inputs["question"])
    keys = _route(inputs["question"])[:1]          # <- only ever answers ONE intent
    answer = " ".join(FACTS[k] for k in keys) or "I am not sure."
    tokens = 40 + len(answer) // 4
    return {"answer": answer, "tokens": tokens,
            "cost_usd": round(tokens / 1e6 * PRICE_SMALL, 6),
            "latency_ms": round(280 + rng.random() * 220, 1),
            "version": "v1-terse-small"}


def app_v2(inputs: dict) -> dict:
    """Candidate: richer prompt, bigger model. Better recall, 3x the bill."""
    rng = random.Random(inputs["question"])
    keys = _route(inputs["question"])              # <- handles multi-intent
    body = " ".join(FACTS[k] for k in keys) or "I am not sure."
    # The "helpful" preamble the new prompt template adds. Harmless to a human.
    # Poison to a length-sensitive judge, and it is what makes v2 look better
    # than it is on any metric that rewards words.
    answer = ("Thanks for reaching out, happy to help with that. " + body +
              " Let me know if there is anything else I can clarify for you.")
    tokens = 60 + len(answer) // 4
    return {"answer": answer, "tokens": tokens,
            "cost_usd": round(tokens / 1e6 * PRICE_FRONTIER, 6),
            "latency_ms": round(610 + rng.random() * 480, 1),
            "version": "v2-rich-frontier"}


# ---------------------------------------------------------------------------
# 3. Evaluators — signature matches langsmith.evaluate() exactly
# ---------------------------------------------------------------------------
def exact_match(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """The evaluator everyone writes first and nobody keeps."""
    hit = outputs["answer"].strip().lower() == reference_outputs["answer"].strip().lower()
    return {"key": "exact_match", "score": float(hit),
            "comment": "string equality on free text; expect ~0 forever"}


def rubric_judge(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """A DETERMINISTIC stand-in for an LLM-as-judge with an explicit rubric.

    Real judges are an LLM plus a prompt. The failure modes are the prompt's,
    not the model's: a rubric with named, checkable criteria and a stated scale
    beats "rate this answer 1-10" by a wide margin. Encoding the rubric as code
    here makes that concrete -- and makes the eval reproducible, which an LLM
    judge at temperature>0 is not.
    """
    ans = outputs["answer"].lower()
    must = [t.lower() for t in reference_outputs.get("must_include", [])]
    never = [t.lower() for t in reference_outputs.get("must_not_include", [])]

    coverage = sum(t in ans for t in must) / max(1, len(must))       # weight 0.60
    safety = 1.0 if not any(t in ans for t in never) else 0.0        # weight 0.25
    words = len(outputs["answer"].split())                           # weight 0.15
    concision = 1.0 if words <= 25 else max(0.0, 1 - (words - 25) / 25)

    score = 0.60 * coverage + 0.25 * safety + 0.15 * concision
    return {"key": "rubric_judge", "score": round(score, 3),
            "comment": f"coverage={coverage:.2f} safety={safety:.0f} concision={concision:.2f}"}


def fact_coverage(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """One criterion, reported on its own. Composite scores hide which half moved."""
    must = [t.lower() for t in reference_outputs.get("must_include", [])]
    ans = outputs["answer"].lower()
    hit = sum(t in ans for t in must) / max(1, len(must))
    return {"key": "fact_coverage", "score": round(hit, 3),
            "comment": f"{int(hit * len(must))}/{len(must)} required facts"}


def concision(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """The other half. Padding is a real cost: tokens, latency, and reader time."""
    words = len(outputs["answer"].split())
    return {"key": "concision", "score": round(1.0 if words <= 25
                                               else max(0.0, 1 - (words - 25) / 25), 3),
            "comment": f"{words} words"}


def naive_length_judge(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """A BAD judge, included on purpose. It rewards words, not correctness.

    This is verbosity bias with the lid off. An LLM judge asked "which answer is
    more helpful?" reproduces this bias reliably, because longer answers look
    more effortful. If your judge and your rubric disagree, trust neither until
    you have human-labelled a sample -- see ../../../15-ai-evals/.
    """
    return {"key": "naive_length_judge",
            "score": round(min(1.0, len(outputs["answer"].split()) / 40), 3),
            "comment": "DO NOT SHIP THIS EVALUATOR"}


def no_forbidden_claims(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """A hard constraint. Constraints are pass/fail, never averaged into quality."""
    bad = [t for t in reference_outputs.get("must_not_include", [])
           if t.lower() in outputs["answer"].lower()]
    return {"key": "no_forbidden_claims", "score": 0.0 if bad else 1.0,
            "comment": f"violations={bad}" if bad else "clean"}


def latency_budget(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    ok = outputs["latency_ms"] <= 900
    return {"key": "latency_budget", "score": float(ok),
            "comment": f"{outputs['latency_ms']:.0f}ms vs 900ms budget"}


def cost_budget(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    ok = outputs["cost_usd"] <= 0.00025
    return {"key": "cost_budget", "score": float(ok),
            "comment": f"${outputs['cost_usd']:.6f} vs $0.000250 budget"}


EVALUATORS: list[Callable] = [exact_match, rubric_judge, fact_coverage, concision,
                              naive_length_judge, no_forbidden_claims,
                              latency_budget, cost_budget]


# ---------------------------------------------------------------------------
# 4. The experiment runner — this is evaluate() with the network removed
# ---------------------------------------------------------------------------
def run_experiment(name: str, target: Callable, dataset: list[Example],
                   evaluators: list[Callable], split: str | None = None) -> dict:
    examples = [e for e in dataset if split is None or e.split == split]
    rows = []
    for ex in examples:
        outputs = target(ex.inputs)
        scores = {}
        for ev in evaluators:
            # A broken evaluator must never kill the experiment. LangSmith records
            # the evaluator error on the run and keeps going; so do we.
            try:
                r = ev(ex.inputs, outputs, ex.reference_outputs)
                scores[r["key"]] = r
            except Exception as exc:                                # noqa: BLE001
                scores[ev.__name__] = {"key": ev.__name__, "score": None,
                                       "comment": f"EVALUATOR ERROR {exc}"}
        rows.append({"example": ex, "outputs": outputs, "scores": scores})

    # Summary evaluators: metrics that only exist at the whole-experiment level.
    lat = sorted(r["outputs"]["latency_ms"] for r in rows)
    metrics = {k: round(statistics.fmean([r["scores"][k]["score"] for r in rows]), 4)
               for k in (e.__name__ for e in evaluators) if k in rows[0]["scores"]}
    metrics["p95_latency_ms"] = round(lat[min(len(lat) - 1, int(0.95 * len(lat)))], 1)
    metrics["total_cost_usd"] = round(sum(r["outputs"]["cost_usd"] for r in rows), 6)
    return {"name": name, "version": rows[0]["outputs"]["version"],
            "n": len(rows), "rows": rows, "metrics": metrics}


# ---------------------------------------------------------------------------
# 5. Pairwise comparison — the right tool when absolute scoring is hopeless
# ---------------------------------------------------------------------------
def pairwise_prefer_concise_and_covered(inputs: dict, outputs: list[dict],
                                        reference_outputs: dict) -> list[float]:
    """Returns [score_a, score_b]; 1 = winner. Mirrors evaluate_comparative()."""
    def q(o: dict) -> float:
        return rubric_judge(inputs, o, reference_outputs)["score"]
    a, b = q(outputs[0]), q(outputs[1])
    if abs(a - b) < 1e-9:
        return [0.5, 0.5]
    return [1.0, 0.0] if a > b else [0.0, 1.0]


def run_pairwise(exp_a: dict, exp_b: dict, evaluator: Callable,
                 randomize_order: bool = True, seed: int = 11) -> dict:
    """`randomize_order=True` is a real evaluate_comparative() kwarg.

    It exists because LLM judges have *position bias*: given the same two
    answers, many models prefer whichever was shown first. Shuffling the pair
    per example turns a systematic bias into noise you can average out.
    """
    rng = random.Random(seed)
    wins = {exp_a["name"]: 0.0, exp_b["name"]: 0.0}
    for ra, rb in zip(exp_a["rows"], exp_b["rows"]):
        pair = [(exp_a["name"], ra), (exp_b["name"], rb)]
        if randomize_order and rng.random() < 0.5:
            pair.reverse()
        scores = evaluator(ra["example"].inputs,
                           [pair[0][1]["outputs"], pair[1][1]["outputs"]],
                           ra["example"].reference_outputs)
        for (nm, _), s in zip(pair, scores):
            wins[nm] += s
    return wins


# ---------------------------------------------------------------------------
# 6. The CI gate: absolute floors AND regression deltas. You need both.
# ---------------------------------------------------------------------------
# Floors stop you shipping something bad. Deltas stop you shipping something
# slightly worse than yesterday, forty times in a row, which is how quality
# actually dies.
FLOORS = {"rubric_judge": 0.80, "no_forbidden_claims": 1.00,
          "latency_budget": 0.90, "cost_budget": 0.90}
MAX_DROP = 0.02          # any floor metric may not fall more than 2 points
MAX_COST_INCREASE = 0.20  # total cost may not rise more than 20%


def gate(metrics: dict, baseline: dict | None) -> list[tuple[str, str, bool]]:
    checks: list[tuple[str, str, bool]] = []
    for key, floor in FLOORS.items():
        v = metrics[key]
        checks.append((f"floor  {key} >= {floor:.2f}", f"{v:.3f}", v + 1e-9 >= floor))
    if not baseline:
        checks.append(("regression", "no baseline recorded -- floors only", True))
        return checks
    for key in FLOORS:
        d = metrics[key] - baseline["metrics"][key]
        checks.append((f"delta  {key} >= -{MAX_DROP:.2f}", f"{d:+.3f}", d >= -MAX_DROP))
    ratio = metrics["total_cost_usd"] / max(1e-12, baseline["metrics"]["total_cost_usd"])
    checks.append((f"delta  total_cost <= +{MAX_COST_INCREASE:.0%}",
                   f"{ratio - 1:+.0%}", ratio - 1 <= MAX_COST_INCREASE))
    return checks


# ---------------------------------------------------------------------------
# 7. Reporting
# ---------------------------------------------------------------------------
def print_rows(exp: dict) -> None:
    print(f"\n{exp['name']}  ({exp['version']}, n={exp['n']})")
    keys = [k for k in exp["rows"][0]["scores"]]
    print("  " + "example " + " ".join(f"{k[:11]:>11}" for k in keys))
    for r in exp["rows"]:
        cells = " ".join(f"{r['scores'][k]['score']:>11.2f}" for k in keys)
        print(f"  {r['example'].id:<7}  {cells}")


def print_metrics(a: dict, b: dict) -> None:
    print(f"\n{'metric':<22}{a['name']:>14}{b['name']:>14}{'delta':>12}")
    print("-" * 62)
    for k in a["metrics"]:
        va, vb = a["metrics"][k], b["metrics"][k]
        print(f"{k:<22}{va:>14.4f}{vb:>14.4f}{vb - va:>+12.4f}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--update-baseline", action="store_true",
                    help="re-record baseline.json from app_v1 and exit")
    ap.add_argument("--strict", action="store_true",
                    help="exit(1) on gate failure, the way CI should")
    args = ap.parse_args()

    print(__doc__.split("RUN IT")[0].rstrip())

    v1 = run_experiment("v1-baseline", app_v1, DATASET, EVALUATORS)
    if args.update_baseline or not BASELINE_PATH.exists():
        BASELINE_PATH.write_text(json.dumps(
            {"name": v1["name"], "version": v1["version"], "n": v1["n"],
             "metrics": v1["metrics"]}, indent=2) + "\n")
        print(f"\n[baseline] wrote {BASELINE_PATH.name} from {v1['version']}")
        if args.update_baseline:
            return 0
    baseline = json.loads(BASELINE_PATH.read_text())

    v2 = run_experiment("v2-candidate", app_v2, DATASET, EVALUATORS)

    print("\n" + "=" * 78)
    print("PER-EXAMPLE SCORES  (this table is the whole product; means hide bugs)")
    print("=" * 78)
    print_rows(v1)
    print_rows(v2)

    print("\n" + "=" * 78)
    print("AGGREGATES")
    print("=" * 78)
    print_metrics(v1, v2)

    print("\n" + "=" * 78)
    print("JUDGE DISAGREEMENT  (why you never trust one number)")
    print("=" * 78)
    dn = v2["metrics"]["naive_length_judge"] - v1["metrics"]["naive_length_judge"]
    dr = v2["metrics"]["rubric_judge"] - v1["metrics"]["rubric_judge"]
    dc = v2["metrics"]["fact_coverage"] - v1["metrics"]["fact_coverage"]
    dz = v2["metrics"]["concision"] - v1["metrics"]["concision"]
    print(f"  naive_length_judge   v2 - v1 = {dn:+.3f}   <- looks like a landslide")
    print(f"  rubric_judge         v2 - v1 = {dr:+.3f}   <- the real, composite effect")
    print(f"    of which coverage          {dc:+.3f}   <- a genuine win (multi-intent rows)")
    print(f"    of which concision         {dz:+.3f}   <- paid for with padding")
    print(f"  exact_match          {v1['metrics']['exact_match']:.2f} / "
          f"{v2['metrics']['exact_match']:.2f}          <- measured nothing, as promised")
    print("\n  Three lessons, in order of how much they will cost you:")
    print("   - The naive judge's +0.6 is a 'Thanks for reaching out' preamble. An LLM")
    print("     judge asked 'which answer is more helpful?' reproduces this bias every")
    print("     time. Calibrate a judge against human labels before it gates anything.")
    print("   - The composite rubric nets out near zero because a real coverage win and")
    print("     a real padding regression cancel. ALWAYS report criteria separately.")
    print("   - Neither number is the blocker. The bill is. See the gate below.")
    print("   Theory for all three: ../../../15-ai-evals/")

    print("\n" + "=" * 78)
    print("PAIRWISE  (randomize_order=True, as evaluate_comparative() does)")
    print("=" * 78)
    wins = run_pairwise(v1, v2, pairwise_prefer_concise_and_covered)
    for nm, w in wins.items():
        print(f"  {nm:<14} {w:>5.1f} / {v1['n']} wins")

    print("\n" + "=" * 78)
    print(f"CI GATE  (candidate {v2['version']} vs baseline {baseline['version']})")
    print("=" * 78)
    checks = gate(v2["metrics"], baseline)
    for label, value, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label:<38} {value}")
    failed = [c for c in checks if not c[2]]
    verdict = "FAIL" if failed else "PASS"
    print(f"\n  GATE: {verdict}"
          + (f"  ({len(failed)} check(s) failed)" if failed else ""))

    if failed:
        print("\n  What a real team does next, in order:")
        print("   1. Read the per-example table, not the mean. Which rows moved?")
        print("   2. Open those examples' source traces (metadata.source above).")
        print("   3. If the regression is real: fix, re-run, keep the baseline.")
        print("   4. If the metric is wrong: fix the EVALUATOR, then re-record the")
        print("      baseline deliberately with --update-baseline. Never silently.")
        print("   5. Here: the v2 prompt earned real coverage on the multi-intent rows,")
        print("      then gave it straight back in padding, and it arrived bundled with")
        print("      a model swap that multiplied the bill 38x. Split the change: keep")
        print("      the prompt, delete the preamble, stay on the small model, re-run.")

    if args.strict and failed:
        return 1
    if failed:
        print("\n  (exit 0 -- this is the demo. Add --strict and CI will block the merge.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
