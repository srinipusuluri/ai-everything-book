#!/usr/bin/env python3
"""
minimal_tracer.py — LangSmith's core data model, reimplemented locally in ~200 lines.

WHY THIS EXISTS
    LangSmith is a hosted service. You cannot run it offline, and you should not
    have to create an account to understand it. So we rebuild the part that
    actually carries the teaching: the *run tree*.

    Everything below mirrors a real LangSmith concept:

        Run                -> a single unit of work (one LLM call, one retrieval)
        Trace              -> the tree of runs for one top-level operation
        run_type           -> llm | chain | tool | retriever | prompt | parser
        parent/child       -> nesting, tracked through a contextvar
        inputs/outputs     -> what went in, what came out
        error              -> the exception, captured, run still recorded
        tags / metadata    -> filterable strings / key-value pairs
        thread_id          -> groups traces into one multi-turn conversation
        @traceable         -> the decorator that does all of this for you
        process_inputs     -> the PII redaction hook (real @traceable kwarg)
        sampling rate      -> LANGSMITH_TRACING_SAMPLING_RATE, but local

    What we do NOT rebuild: the backend, the UI, the search index, the evaluators.
    That is what you pay LangSmith (or Langfuse, or Phoenix) for.

RUN IT
    python minimal_tracer.py

    No network. No API key. No dependencies beyond the standard library (3.10+).
"""
from __future__ import annotations

import contextvars
import functools
import random
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

# ---------------------------------------------------------------------------
# 1. Cost attribution
# ---------------------------------------------------------------------------
# ILLUSTRATIVE rates in USD per 1M tokens, as (input, output). These are made-up
# tier placeholders on purpose — real prices move monthly and a hardcoded number
# in a teaching repo is a lie with a timestamp. Point this at your provider's
# live pricing page. The *mechanism* is what matters: cost is a derived field,
# computed from (model, prompt_tokens, completion_tokens) at write time.
PRICES_PER_MTOK: dict[str, tuple[float, float]] = {
    "frontier": (15.00, 75.00),
    "mid": (3.00, 15.00),
    "small": (0.25, 1.25),
}


def cost_usd(tier: str | None, prompt_tokens: int, completion_tokens: int) -> float:
    p_in, p_out = PRICES_PER_MTOK.get(tier or "", (0.0, 0.0))
    return prompt_tokens / 1e6 * p_in + completion_tokens / 1e6 * p_out


# ---------------------------------------------------------------------------
# 2. The Run — LangSmith's atom
# ---------------------------------------------------------------------------
@dataclass
class Run:
    name: str
    run_type: str = "chain"          # llm | chain | tool | retriever | prompt | parser
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    parent_id: str | None = None
    trace_id: str | None = None      # id of the root run; the whole tree shares it
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: Any = None
    error: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    start_ns: int = 0
    end_ns: int = 0
    prompt_tokens: int = 0           # set from inside via current_run()
    completion_tokens: int = 0
    model_tier: str | None = None
    children: list["Run"] = field(default_factory=list)

    # --- derived fields: never stored, always computed -----------------------
    @property
    def latency_ms(self) -> float:
        return (self.end_ns - self.start_ns) / 1e6

    @property
    def own_cost(self) -> float:
        return cost_usd(self.model_tier, self.prompt_tokens, self.completion_tokens)

    def rollup(self) -> tuple[int, float]:
        """(total tokens, total cost) for this run and every descendant.

        This is the single most useful number in an LLM trace: a chain has no
        cost of its own, but the subtree underneath it does. 'Which endpoint is
        burning my budget' is a rollup query, not a per-call query.
        """
        tok = self.prompt_tokens + self.completion_tokens
        usd = self.own_cost
        for c in self.children:
            ct, cu = c.rollup()
            tok += ct
            usd += cu
        return tok, usd


# ---------------------------------------------------------------------------
# 3. The tracer: a contextvar stack + a list of completed traces
# ---------------------------------------------------------------------------
_CURRENT: contextvars.ContextVar[Run | None] = contextvars.ContextVar("current_run", default=None)
TRACES: list[Run] = []
SAMPLING_RATE = 1.0   # the local twin of LANGSMITH_TRACING_SAMPLING_RATE
TRACING_ENABLED = True  # the local twin of LANGSMITH_TRACING


_AMBIENT: contextvars.ContextVar[dict] = contextvars.ContextVar("ambient_meta", default={})


class tracing_context:
    """Attach metadata/tags to every run started inside the block.

    The real SDK spells this `langsmith.tracing_context(metadata=..., tags=...)`,
    and it is how `thread_id`, `user_id` and a release SHA get onto spans without
    threading them through fifteen function signatures.
    """

    def __init__(self, **metadata: Any) -> None:
        self.metadata = metadata
        self._token: Any = None

    def __enter__(self) -> "tracing_context":
        self._token = _AMBIENT.set({**_AMBIENT.get(), **self.metadata})
        return self

    def __exit__(self, *exc: Any) -> None:
        _AMBIENT.reset(self._token)


def current_run() -> Run | None:
    """Grab the run you are inside, to attach token counts, tags or metadata.

    The real SDK spells this `langsmith.get_current_run_tree()`.
    """
    return _CURRENT.get()


def traceable(
    func: Callable | None = None,
    *,
    run_type: str = "chain",
    name: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    process_inputs: Callable[[dict], dict] | None = None,
    process_outputs: Callable[[Any], Any] | None = None,
):
    """A stand-in for `langsmith.traceable`. Same shape, same kwargs, no network.

    Usable bare (`@traceable`) or called (`@traceable(run_type="llm")`).

    `process_inputs` / `process_outputs` are the redaction hooks. They are real
    @traceable kwargs and they are how you keep customer PII out of a SaaS
    observability backend. See ../../../13-ai-security/ and ../../../12-ai-governance/.
    """

    def decorate(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            parent = _CURRENT.get()
            # Sampling decision happens at the ROOT only. Sampling a child out of
            # an otherwise-sampled trace would give you a tree with holes in it.
            if not TRACING_ENABLED or (parent is None and random.random() > SAMPLING_RATE):
                return fn(*args, **kwargs)

            payload = {"args": [_short(a) for a in args],
                       **{k: _short(v) for k, v in kwargs.items()}}
            if process_inputs:
                payload = process_inputs(payload)

            run = Run(
                name=name or fn.__name__,
                run_type=run_type,
                parent_id=parent.id if parent else None,
                inputs=payload,
                tags=list(tags or []),
                metadata={**_AMBIENT.get(), **(metadata or {})},
                start_ns=time.perf_counter_ns(),
            )
            run.trace_id = parent.trace_id if parent else run.id
            if parent:
                parent.children.append(run)
                # Metadata inherits down the tree — that is how thread_id,
                # user_id and release version reach every span for free.
                run.metadata = {**parent.metadata, **run.metadata}

            token = _CURRENT.set(run)
            try:
                out = fn(*args, **kwargs)
                run.outputs = process_outputs(out) if process_outputs else _short(out)
                return out
            except Exception as exc:                      # noqa: BLE001
                # Errors are DATA, not a reason to lose the trace. This is the
                # whole point: the failed run is the one you most want to read.
                run.error = f"{type(exc).__name__}: {exc}"
                raise
            finally:
                run.end_ns = time.perf_counter_ns()
                _CURRENT.reset(token)
                if parent is None:
                    TRACES.append(run)

        return wrapper

    return decorate(func) if callable(func) else decorate


def _short(v: Any, limit: int = 60) -> Any:
    s = v if isinstance(v, str) else repr(v)
    return s if len(s) <= limit else s[: limit - 1] + "…"


# ---------------------------------------------------------------------------
# 4. Pretty-printing the tree — the artifact you actually debug from
# ---------------------------------------------------------------------------
def print_trace(root: Run, width: int = 46) -> None:
    tok, usd = root.rollup()
    thread = root.metadata.get("thread_id", "-")
    print(f"\ntrace {root.trace_id}  thread={thread}  "
          f"{root.latency_ms:.0f}ms  {tok:,} tok  ${usd:.6f}")
    print(f"  in : {root.inputs}")
    print(f"  out: {root.outputs}")
    print("-" * 96)
    _walk(root, "", True, width, root=True)


def _walk(run: Run, prefix: str, last: bool, width: int, root: bool = False) -> None:
    elbow = "" if root else ("`-- " if last else "|-- ")
    label = f"{prefix}{elbow}{run.name}"
    cost = f"${run.own_cost:.6f}" if run.own_cost else ""
    toks = f"{run.prompt_tokens + run.completion_tokens:>5} tok" if run.model_tier else " " * 9
    status = f"   ERR {run.error}" if run.error else ""
    print(f"{label:<{width}} [{run.run_type:<9}] {run.latency_ms:>7.1f}ms {toks} {cost:>10}{status}".rstrip())
    child_prefix = prefix + ("" if root else ("    " if last else "|   "))
    for i, c in enumerate(run.children):
        _walk(c, child_prefix, i == len(run.children) - 1, width)


# ---------------------------------------------------------------------------
# 5. A worked example: a small RAG-ish agent, one good turn and one broken turn
# ---------------------------------------------------------------------------
DOCS = {
    "refund": "Refunds are issued to the original payment method within 5-7 business days.",
    "shipping": "Standard shipping is 3-5 business days. Express is next-day before 2pm.",
    "warranty": "Hardware carries a 12-month limited warranty from date of delivery.",
}


EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def redact(payload: dict) -> dict:
    """process_inputs hook: never ship raw customer text to a vendor backend.

    The real SDK gives you the same seam three ways: `process_inputs` on
    @traceable (per function), `hide_inputs=` / `anonymizer=` on the Client
    (global), or LANGSMITH_HIDE_INPUTS=true (blunt, ships nothing).
    """

    def scrub(v: Any) -> Any:
        if isinstance(v, str):
            return EMAIL_RE.sub("<redacted:email>", v)
        if isinstance(v, list):
            return [scrub(x) for x in v]
        if isinstance(v, dict):
            return {k: scrub(x) for k, x in v.items()}
        return v

    return {k: scrub(v) for k, v in payload.items()}


@traceable(run_type="retriever", tags=["rag"])
def retrieve(query: str, k: int = 2) -> list[str]:
    time.sleep(0.012)
    hits = [t for t in DOCS if t in query.lower()]
    return [DOCS[t] for t in hits[:k]] or [DOCS["shipping"]]


@traceable(run_type="prompt")
def build_prompt(question: str, context: list[str]) -> str:
    return "Context:\n" + "\n".join(context) + f"\n\nQuestion: {question}"


@traceable(run_type="llm", name="chat_completion")
def call_llm(prompt: str, tier: str = "mid") -> str:
    """Stand-in for an actual provider call. Token counts land on the run."""
    time.sleep(0.03 if tier == "small" else 0.09)
    run = current_run()
    if run:                                    # this is the wrap_openai() job
        run.model_tier = tier
        run.prompt_tokens = max(1, len(prompt) // 4)
        run.completion_tokens = 120 if tier != "small" else 40
    return "Refunds land back on your original card in 5-7 business days."


@traceable(run_type="tool")
def check_policy_api(answer: str) -> dict:
    time.sleep(0.008)
    if "5-7" not in answer:
        raise ValueError("answer contradicts the published SLA")
    return {"ok": True}


@traceable(run_type="tool")
def lookup_order(order_id: str) -> dict:
    time.sleep(0.005)
    raise TimeoutError(f"orders-api did not respond for {order_id}")


@traceable(name="support_agent", metadata={"release": "2026.09.1"},
           process_inputs=redact)
def support_agent(question: str, order_id: str | None = None) -> str:
    ctx = retrieve(question)
    prompt = build_prompt(question, ctx)
    answer = call_llm(prompt)
    check_policy_api(answer)
    if order_id:
        # Deliberately fails, so you can see an error inside an otherwise
        # healthy trace — the single most common real-world shape.
        try:
            lookup_order(order_id)
        except TimeoutError:
            answer += " (Order status is temporarily unavailable.)"
    return answer


@traceable(name="classify", metadata={"release": "2026.09.1"})
def classify(question: str) -> str:
    return call_llm(question, tier="small")


def main() -> None:
    random.seed(7)
    print(__doc__.split("RUN IT")[0].rstrip())

    # --- one thread, two turns: each turn is its own trace ------------------
    # A thread is not a bigger trace. It is a *label shared by sibling traces*.
    # Turn 1 and turn 2 stay separately debuggable; the UI groups them for you.
    thread = "thread-" + uuid.uuid4().hex[:6]
    with tracing_context(thread_id=thread, user_id="u_8812"):
        support_agent("what is the refund policy? mail me at ana@example.com")
        support_agent("and where is my order?", "ORD-4417")

    # A trace outside any thread, for contrast.
    classify("is this billing or shipping?")

    for t in TRACES:
        print_trace(t)

    # --- the aggregate views a dashboard would show -------------------------
    print("\n" + "=" * 96)
    print("PROJECT ROLLUP (what the monitoring tab computes for you)")
    print("=" * 96)
    total_cost = sum(t.rollup()[1] for t in TRACES)
    errs = sum(_count_errors(t) for t in TRACES)
    runs = sum(_count_runs(t) for t in TRACES)
    lats = sorted(t.latency_ms for t in TRACES)
    print(f"  traces            {len(TRACES)}")
    print(f"  runs (spans)      {runs}")
    print(f"  error runs        {errs}  ({errs / runs:.0%} of spans)")
    print(f"  p50 / max latency {lats[len(lats) // 2]:.0f}ms / {lats[-1]:.0f}ms")
    print(f"  total cost        ${total_cost:.6f}   "
          f"(projected at 1M traces: ${total_cost / len(TRACES) * 1e6:,.0f})")
    print("\n  Note the redacted input on the first trace: process_inputs ran before\n"
          "  anything was recorded. Redaction at the SDK boundary is the only kind\n"
          "  that counts -- scrubbing server-side means the PII already left.\n")
    print("  Next: code/eval_harness.py turns the failing runs above into a dataset.")


def _count_errors(r: Run) -> int:
    return (1 if r.error else 0) + sum(_count_errors(c) for c in r.children)


def _count_runs(r: Run) -> int:
    return 1 + sum(_count_runs(c) for c in r.children)


if __name__ == "__main__":
    main()
