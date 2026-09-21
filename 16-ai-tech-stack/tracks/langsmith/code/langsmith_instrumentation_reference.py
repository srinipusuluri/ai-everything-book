#!/usr/bin/env python3
"""
langsmith_instrumentation_reference.py — the real LangSmith SDK, annotated.

This file DOES NOT CALL LANGSMITH BY DEFAULT and it will not crash if you run it.
With no LANGSMITH_API_KEY set it prints an annotated walkthrough and exits 0.
With a key set it still refuses to send anything unless you also pass --live,
because a teaching script should never quietly create billable runs in someone's
workspace.

    python langsmith_instrumentation_reference.py          # explain, exit 0
    python langsmith_instrumentation_reference.py --live    # actually trace + eval

The offline twins of everything here are minimal_tracer.py and eval_harness.py.
Read those first; this file is the translation table.

Verified against the docs listed in ../papers/PAPERS.md (September 2026):
  https://docs.langchain.com/langsmith/observability-quickstart
  https://docs.langchain.com/langsmith/observability-concepts
  https://docs.langchain.com/langsmith/evaluate-llm-application
  https://docs.langchain.com/langsmith/evaluate-pairwise
  https://docs.langchain.com/langsmith/mask-inputs-outputs
  https://docs.langchain.com/langsmith/sample-traces
"""
from __future__ import annotations

import os
import sys
import textwrap

# =============================================================================
# SECTION 0 — Install and configure
# =============================================================================
SETUP = r"""
pip install -U langsmith                      # the SDK is standalone (v0.12 era)

export LANGSMITH_TRACING=true                 # the master switch. Without it,
                                              # @traceable is a no-op passthrough
                                              # and your traces silently vanish.
export LANGSMITH_API_KEY="lsv2_pt_..."
export LANGSMITH_PROJECT="support-agent-prod" # default project for these runs
# export LANGSMITH_ENDPOINT="https://eu.api.smith.langchain.com"   # EU data region
# export LANGSMITH_TRACING_SAMPLING_RATE=0.1  # 0.0-1.0; sample at the ROOT
# export LANGSMITH_HIDE_INPUTS=true           # blunt PII kill-switch
# export LANGSMITH_HIDE_OUTPUTS=true

The single most common setup bug: LANGSMITH_API_KEY set, LANGSMITH_TRACING unset.
Nothing errors. Nothing appears. You lose an afternoon.
"""

# =============================================================================
# SECTION 1 — Tracing: @traceable, wrappers, and why it is framework-agnostic
# =============================================================================
TRACING = r'''
from langsmith import traceable
from langsmith.wrappers import wrap_openai   # also: wrap_anthropic
import openai

# (a) Wrap the provider client. Every call it makes becomes a child `llm` run
#     with model, messages, token usage and cost already populated. This is the
#     highest value-per-keystroke line in the whole SDK.
client = wrap_openai(openai.OpenAI())

# (b) Decorate your own functions. run_type drives how the UI renders the span:
#     llm | chain | tool | retriever | prompt | parser
@traceable(run_type="retriever")
def retrieve(question: str) -> list[str]:
    return vector_store.similarity_search(question, k=4)

@traceable(run_type="tool")
def lookup_order(order_id: str) -> dict:
    return orders_api.get(order_id)

@traceable(                       # the parent span; children nest automatically
    name="support_agent",
    metadata={"release": os.environ.get("GIT_SHA", "dev")},
    tags=["prod", "support"],
)
def support_agent(question: str, order_id: str | None = None) -> str:
    docs = retrieve(question)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "\n".join(docs)},
                  {"role": "user", "content": question}],
    )
    return resp.choices[0].message.content

# (c) Attach data from inside a run -- feedback ids, custom metadata, usage.
from langsmith import get_current_run_tree

@traceable
def rerank(docs):
    rt = get_current_run_tree()
    rt.metadata["reranker"] = "bge-reranker-v2"
    rt.tags.append("experimental")
    return sorted(docs, key=score, reverse=True)

# (d) Ambient context instead of threading kwargs through ten call frames.
from langsmith import tracing_context

with tracing_context(metadata={"thread_id": session_id, "user_id": user.id},
                     project_name="support-agent-canary"):
    support_agent(q)
# thread_id is what turns N sibling traces into one readable conversation in
# the Threads view. Set it or you will debug multi-turn bugs one turn at a time.

# (e) Manual run trees, when a decorator cannot reach (streaming, callbacks,
#     a worker pool that loses the contextvar across a process boundary).
from langsmith.run_helpers import trace

with trace(name="batch_scoring", run_type="chain", inputs={"n": len(batch)}) as rt:
    out = score_all(batch)
    rt.end(outputs={"mean": out.mean})

# (f) FRAMEWORK-AGNOSTIC, which is the part people get wrong:
#     - LangChain / LangGraph: tracing is automatic once LANGSMITH_TRACING=true.
#       You import nothing.
#     - Everything else (raw SDK calls, FastAPI, DSPy, your own agent loop):
#       @traceable and the wrappers work fine. LangSmith does not require
#       LangChain. It is a tracing backend that happens to be made by them.
#     - OpenTelemetry: LangSmith accepts OTLP traces and can also export to an
#       OTel collector, so it can sit inside an existing observability stack
#       rather than beside it.
'''

# =============================================================================
# SECTION 2 — PII: redact at the SDK boundary, never server-side
# =============================================================================
REDACTION = r'''
from langsmith import Client, traceable
from langsmith.anonymizer import create_anonymizer

# Rule-based, client-wide. Runs before anything leaves the process.
anonymizer = create_anonymizer([
    {"pattern": r"[\w.+-]+@[\w-]+\.[\w.]+", "replace": "<email>"},
    {"pattern": r"\b\d{3}-\d{2}-\d{4}\b",   "replace": "<ssn>"},
])
client = Client(anonymizer=anonymizer)

# Or callables, if you need structure-aware masking:
client = Client(
    hide_inputs=lambda x: {**x, "question": mask(x.get("question", ""))},
    hide_outputs=lambda x: x,
)

# Or per-function, which composes and takes precedence over the client hooks:
@traceable(process_inputs=lambda d: {**d, "ssn": "<redacted>"},
           process_outputs=lambda o: o)
def underwrite(applicant): ...

# The blunt instrument, for regulated workloads:
#   LANGSMITH_HIDE_INPUTS=true LANGSMITH_HIDE_OUTPUTS=true
# You keep latency, cost, error rate and tree shape; you lose the payloads,
# which is most of the debugging value. Decide deliberately, with the people in
# ../../../12-ai-governance/ and ../../../13-ai-security/ in the room.
'''

# =============================================================================
# SECTION 3 — Datasets, from the only source that matters: production traces
# =============================================================================
DATASETS = r'''
from langsmith import Client
client = Client()

ds = client.create_dataset("support-regression",
                           description="Harvested from thumbs-down + tool-error traces")

client.create_examples(
    dataset_id=ds.id,
    examples=[
        {"inputs": {"question": "how long do refunds take?"},
         "outputs": {"answer": "5-7 business days to the original payment method."},
         "metadata": {"source_run_id": "...", "reason": "thumbs_down"},
         "split": "smoke"},
    ],
)

# Versioning is automatic: every add/update/delete creates a new dataset version.
# Tag the one CI should pin to, so a teammate adding examples cannot move your
# baseline out from under you mid-sprint.
client.update_dataset_tag(dataset_name="support-regression",
                          as_of="2026-09-01T00:00:00Z", tag="ci-pinned")

# Read back a split, or a specific version:
examples = list(client.list_examples(dataset_name="support-regression",
                                     splits=["smoke"]))

# In the UI: filter a tracing project (feedback = thumbs down, error = true,
# latency > p99, metadata.customer_tier = enterprise), multi-select, Add to
# Dataset. This is the single highest-leverage habit in the whole track --
# your eval set should be a museum of your own outages, not a brainstorm.
'''

# =============================================================================
# SECTION 4 — Evaluation: evaluate(), judges, pairwise, summary metrics
# =============================================================================
EVALUATION = r'''
from langsmith import Client, evaluate, aevaluate

# An evaluator takes any subset of these kwargs, by name. Return {key, score}
# plus an optional comment. Identical signature to eval_harness.py.
def correct(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    return {"key": "correct",
            "score": outputs["answer"].strip() == reference_outputs["answer"].strip()}

# LLM-as-judge: an LLM plus a rubric. The rubric is the product.
from openevals.llm import create_llm_as_judge   # pip install openevals
groundedness = create_llm_as_judge(
    prompt="Does the ANSWER follow only from the CONTEXT? Reply true or false.\n"
           "CONTEXT:\n{context}\nANSWER:\n{outputs}",
    model="openai:o4-mini",
    feedback_key="groundedness",
)

def target(inputs: dict) -> dict:
    return {"answer": support_agent(inputs["question"])}

results = evaluate(
    target,
    data="support-regression",           # name, UUID, or an example iterator
    evaluators=[correct, groundedness],
    experiment_prefix="prompt-v7",
    max_concurrency=8,
    num_repetitions=3,                   # run each example N times; nondeterminism
                                         # means one pass is an anecdote
    metadata={"git_sha": os.environ["GIT_SHA"]},
)
# aevaluate() is the async twin with an identical interface -- use it for
# anything above a few dozen examples.

# Summary evaluators score the EXPERIMENT, not a row: pass rate, p95 latency,
# a fleet-level calibration number.
def pass_rate(outputs: list[dict], reference_outputs: list[dict]) -> dict:
    hits = sum(o["answer"] == r["answer"] for o, r in zip(outputs, reference_outputs))
    return {"key": "pass_rate", "score": hits / len(outputs)}

# Pairwise: when absolute scoring is hopeless but "which is better" is easy.
from langsmith import evaluate_comparative

def prefer(inputs: dict, outputs: list[dict]) -> list[float]:
    return [1, 0] if better(outputs[0], outputs[1]) else [0, 1]

evaluate_comparative(
    ["prompt-v6-a1b2c3", "prompt-v7-d4e5f6"],   # two EXISTING experiments
    evaluators=[prefer],
    randomize_order=True,   # <- mitigates POSITION BIAS. Not optional. Many
                            #    judges prefer whichever answer came first, by
                            #    10-20 points, on identical content.
)

# THE THREE BIASES THAT WILL BURN YOU (theory: ../../../15-ai-evals/)
#   position bias      -> randomize_order=True, or score both orders and average
#   verbosity bias     -> longer reads as better; add an explicit length criterion
#   self-preference    -> models rate their own family higher; judge with a
#                         different family than the one you are scoring
'''

# =============================================================================
# SECTION 5 — Feedback, annotation queues, online evals, monitoring
# =============================================================================
OPERATIONS = r'''
from langsmith import Client
client = Client()

# (a) Thumbs up/down from your UI. Return the run id to the browser, POST it back.
from langsmith.run_helpers import get_current_run_tree

@traceable
def answer(q):
    run_id = str(get_current_run_tree().id)     # ship this to the client
    ...

client.create_feedback(run_id=run_id, key="user_score", score=1.0,
                       comment="solved it")     # continuous or categorical

# (b) Annotation queues: human review with a rubric, in the UI. Configure the
#     queue with reviewer instructions and categorical criteria; route runs in
#     by hand, in batches of up to 100, or automatically via a rule. Reviewers
#     score, leave notes, and "Add to Dataset" in one click -- which closes the
#     loop from "a human said this was wrong" to "CI now blocks it".

# (c) Online evaluation: in a Tracing Project, the Evaluators tab attaches an
#     LLM-as-judge to LIVE traffic. You set a filter (feedback = thumbs down,
#     tool = search, metadata.tier = enterprise) and a sampling rate, because
#     judging 100% of production doubles your inference bill. Rules can also
#     auto-add matching runs to a dataset, push them to an annotation queue, or
#     fire a webhook.

# (d) Monitoring: dashboards over traces -- volume, error rate, p50/p95/p99
#     latency, tokens, cost, feedback scores -- grouped by tag or metadata.
#     Alert on cost-per-trace and p95 latency, not just errors. The classic LLM
#     incident is not a 500; it is a prompt change that tripled context length
#     and nobody noticed for nine days.

# (e) LangSmith Engine (2026): scans a project's traces for RECURRING failure
#     patterns -- silent tool errors, hallucinations -- and proposes fixes plus
#     a dataset to verify them. Useful; still an assistant. Read its diagnosis,
#     do not merge its patch unseen.
'''

# =============================================================================
# SECTION 6 — Prompts
# =============================================================================
PROMPTS = r'''
# Prompts live in LangSmith with git-like semantics: every save is a COMMIT with
# a hash, and you can put human-readable TAGS on commits, including the reserved
# environment tags `staging` and `production`.
prompt = client.pull_prompt("my-org/support-system:production")
prompt = client.pull_prompt("my-org/support-system:a1b2c3d")   # pin a commit

# Worth it when non-engineers edit prompts and you still want a rollback path
# and an audit trail (../../../14-ai-compliance/ will ask for one).
# Not worth it when prompts are code owned by engineers: git already does this,
# and a prompt that can change without a deploy is a prompt that can break
# production without a deploy.
'''


def explain() -> None:
    blocks = [("0. SETUP", SETUP), ("1. TRACING", TRACING), ("2. PII REDACTION", REDACTION),
              ("3. DATASETS", DATASETS), ("4. EVALUATION", EVALUATION),
              ("5. FEEDBACK & OPERATIONS", OPERATIONS), ("6. PROMPTS", PROMPTS)]
    for title, body in blocks:
        print("\n" + "=" * 78)
        print(title)
        print("=" * 78)
        print(textwrap.dedent(body).strip("\n"))


def live() -> int:
    """Only reached with --live AND a key. Kept deliberately small."""
    try:
        from langsmith import Client, traceable
    except ImportError:
        print("langsmith is not installed.  pip install -U langsmith")
        return 1

    @traceable(run_type="chain", name="hello_langsmith")
    def hello(name: str) -> str:
        return f"hello, {name}"

    print(hello("langsmith"))
    project = os.environ.get("LANGSMITH_PROJECT", "default")
    print(f"\nSent one trace to project '{project}'.")
    print("Open https://smith.langchain.com and look at the run tree.")
    try:
        Client().list_runs(project_name=project, limit=1)
        print("Client connectivity: OK")
    except Exception as exc:                                     # noqa: BLE001
        print(f"Client connectivity: FAILED -- {type(exc).__name__}: {exc}")
        return 1
    return 0


def main() -> int:
    wants_live = "--live" in sys.argv
    has_key = bool(os.environ.get("LANGSMITH_API_KEY"))
    tracing_on = os.environ.get("LANGSMITH_TRACING", "").lower() in {"1", "true", "yes"}

    print(__doc__.strip())
    print("\n" + "-" * 78)
    print(f"LANGSMITH_API_KEY  {'set' if has_key else 'NOT SET'}")
    print(f"LANGSMITH_TRACING  {'true' if tracing_on else 'not enabled'}")
    print(f"--live flag        {'yes' if wants_live else 'no'}")
    print("-" * 78)

    if wants_live and has_key:
        explain()
        print("\n" + "=" * 78)
        print("LIVE MODE")
        print("=" * 78)
        if not tracing_on:
            print("LANGSMITH_TRACING is not true, so @traceable will no-op and you will\n"
                  "see nothing in the UI. Export LANGSMITH_TRACING=true and re-run.")
        return live()

    if wants_live and not has_key:
        print("\n--live requested but LANGSMITH_API_KEY is unset. Nothing was sent.\n"
              "Printing the reference instead.")
    elif has_key:
        print("\nA key is present but --live was not passed, so NOTHING was sent to your\n"
              "workspace. Re-run with --live if you actually want one test trace.")
    else:
        print("\nNo key, no network, no account needed. Here is the whole API surface,\n"
              "annotated. The offline twins are minimal_tracer.py and eval_harness.py.")

    explain()
    print("\n" + "=" * 78)
    print("Now go run the offline versions:")
    print("  python minimal_tracer.py      -- the run tree, rebuilt from scratch")
    print("  python eval_harness.py        -- evaluate(), judges, and a CI gate")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
