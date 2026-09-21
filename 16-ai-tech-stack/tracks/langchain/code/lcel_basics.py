"""
lcel_basics.py -- the Runnable interface and LCEL composition, end to end, offline.

RUNS WITH NO NETWORK AND NO API KEY. Every model call is served by the hand-rolled
fakes in `fakes.py`, so output is byte-for-byte reproducible.

    /Users/srinip/ai-all/.venv/bin/python lcel_basics.py

What this file argues: LCEL is not a DSL you have to learn, it is one interface
(`Runnable`) plus operator overloading. `__or__` builds a `RunnableSequence`; a dict
literal in a chain position is coerced into a `RunnableParallel`; a bare function is
coerced into a `RunnableLambda`. Once something is a Runnable you inherit
invoke/stream/batch + their async twins + retries + fallbacks + config + tracing.

Targets langchain-core 1.6.3. Note the v1 framing: `create_agent` (langchain.agents,
built on LangGraph) is now the recommended way to build *agents*. LCEL remains the
right tool for fixed, deterministic pipelines -- prompt -> model -> parse -- and it
is still the plumbing under every LangChain component. See notes/01-core-concepts.md.
"""

from __future__ import annotations

import asyncio
import time

from fakes import FakeChatModel, FlakyChatModel, rule
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import (
    ConfigurableField,
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)

# A single model instance reused everywhere. Rules are matched in order.
MODEL = FakeChatModel(
    rules=[
        ("kubernetes", "Kubernetes schedules containers across a cluster of machines."),
        ("embedding", "An embedding maps text to a vector so similar text lands nearby."),
        ("latency", "Latency is dominated by output tokens, not input tokens."),
        # Order matters: "critique" is checked before "summar" so the critique
        # branch in demo 3 does not get hijacked by the word "summarisation".
        ("critique", "Weakness: the answer gives no numbers and cites nothing."),
        ("summar", "Short version: it orchestrates model calls."),
    ],
    default="No rule matched, so this is the fallback reply.",
)


# ---------------------------------------------------------------------------
def demo_1_the_smallest_chain() -> None:
    rule("1. prompt | model | parser -- the whole of LCEL in one line")

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are terse. Answer in one sentence."),
            ("human", "{question}"),
        ]
    )
    chain = prompt | MODEL | StrOutputParser()

    print("type of chain      :", type(chain).__name__)
    print("steps              :", [type(s).__name__ for s in chain.steps])
    print("input schema keys  :", sorted(chain.input_schema.model_json_schema()["properties"]))
    print()
    print("invoke ->", chain.invoke({"question": "What is an embedding?"}))

    # Without the parser you get an AIMessage, not a str. The parser is the only
    # reason `chain.invoke(...)` returns something you can concatenate.
    raw = (prompt | MODEL).invoke({"question": "What is an embedding?"})
    print("no parser ->", type(raw).__name__, "| .content =", repr(raw.content[:40] + "..."))


# ---------------------------------------------------------------------------
def demo_2_the_four_verbs() -> None:
    rule("2. invoke / batch / stream / astream -- you implement none of these")

    chain = ChatPromptTemplate.from_template("Q: {question}") | MODEL | StrOutputParser()

    print("invoke:", chain.invoke({"question": "kubernetes?"}))

    questions = [{"question": q} for q in ("kubernetes?", "latency?", "who is Ada?")]
    t0 = time.perf_counter()
    for i, out in enumerate(chain.batch(questions, config={"max_concurrency": 3})):
        print(f"batch[{i}]:", out)
    print(f"(batch ran 3 inputs in {time.perf_counter() - t0:.4f}s using a thread pool)")

    print("stream:", end=" ", flush=True)
    for token in chain.stream({"question": "latency?"}):
        print(token, end="", flush=True)
    print()

    async def astream_demo() -> None:
        chunks = [c async for c in chain.astream({"question": "embedding?"})]
        print(f"astream: {len(chunks)} chunks, joined =", "".join(chunks).strip())

    asyncio.run(astream_demo())

    # THE GOTCHA: streaming only works if every step in the chain can stream.
    # StrOutputParser can (it passes chunks through). A parser that needs the whole
    # document -- JsonOutputParser, or any RunnableLambda over a complete string --
    # buffers, and your "streaming" app silently becomes a blocking one.
    blocking = chain | RunnableLambda(lambda s: s.upper())
    n = len(list(blocking.stream({"question": "latency?"})))
    print(f"chain | RunnableLambda(...) streamed {n} chunk(s) -- the lambda buffered everything")


# ---------------------------------------------------------------------------
def demo_3_parallel_and_passthrough() -> None:
    rule("3. RunnableParallel and RunnablePassthrough -- fan-out and plumbing")

    summarise = ChatPromptTemplate.from_template("Summarise: {text}") | MODEL | StrOutputParser()
    critique = ChatPromptTemplate.from_template("Critique: {text}") | MODEL | StrOutputParser()

    # A plain dict in a chain position is coerced to RunnableParallel. Both branches
    # run concurrently in a thread pool; the output is a dict with the same keys.
    fan_out = RunnableParallel(summary=summarise, critique=critique)
    result = fan_out.invoke({"text": "a long document about summarisation"})
    for key, value in result.items():
        print(f"  {key:9s}: {value}")

    # RunnablePassthrough.assign adds keys to a dict WITHOUT dropping the originals.
    # This is the single most useful plumbing primitive in LCEL: it is how a RAG
    # chain carries the question forward alongside the retrieved context.
    enriched = RunnablePassthrough.assign(
        word_count=RunnableLambda(lambda d: len(d["text"].split())),
        upper=RunnableLambda(lambda d: d["text"].upper()[:20]),
    )
    print("\n  assign ->", enriched.invoke({"text": "two branches, one dict"}))

    # .pick trims a dict down; useful right before you hand results to a caller.
    print("  pick   ->", (enriched | RunnablePassthrough().pick(["word_count"])).invoke(
        {"text": "two branches, one dict"}
    ))


# ---------------------------------------------------------------------------
def demo_4_configurable_fields() -> None:
    rule("4. configurable_fields -- change behaviour at call time, not build time")

    # Build the chain once, at import time. Vary the model per request via config.
    # The alternative -- rebuilding the chain inside the request handler -- works but
    # costs you a fresh schema validation on every call and makes tracing noisier.
    configurable_model = MODEL.configurable_fields(
        default=ConfigurableField(id="default_reply", name="Fallback reply")
    )
    chain = ChatPromptTemplate.from_template("{q}") | configurable_model | StrOutputParser()

    print("as built :", chain.invoke({"q": "unmatched question"}))
    print("per-call :", chain.invoke(
        {"q": "unmatched question"},
        config={"configurable": {"default_reply": "Escalating to a human."}},
    ))

    # with_config is the same idea, frozen: it returns a new Runnable with the
    # config baked in. Use it to name runs -- these names become the span names in
    # a LangSmith trace, and unnamed spans are the reason traces are unreadable.
    named = chain.with_config(run_name="faq_answer", tags=["demo", "lcel"])
    print("named run:", named.invoke({"q": "kubernetes"}))


# ---------------------------------------------------------------------------
def demo_5_retry_and_fallbacks() -> None:
    rule("5. with_retry and with_fallbacks -- the two lines that save production")

    # with_retry: same runnable, again. Correct for transient failures (429, 503,
    # connection reset). WRONG for a bad prompt -- you will pay three times for the
    # same failure. Always constrain retry_if_exception_type.
    flaky = FlakyChatModel(fail_times=2, reply="succeeded on attempt 3")
    resilient = flaky.with_retry(
        retry_if_exception_type=(ConnectionError,),
        stop_after_attempt=4,
        wait_exponential_jitter=False,  # deterministic output for this demo
    )
    print("with_retry ->", resilient.invoke("hello").content, f"(attempts: {flaky.attempts})")

    # with_fallbacks: a DIFFERENT runnable when the first exhausts itself. The usual
    # shape is expensive-model -> cheap-model, or provider-A -> provider-B.
    always_down = FlakyChatModel(fail_times=99)
    backup = FakeChatModel(rules=[], default="served by the backup model")
    hardened = always_down.with_fallbacks([backup])
    print("with_fallbacks ->", hardened.invoke("hello").content)

    # Compose them: retry the primary a few times, THEN fall back. Order matters --
    # `.with_retry().with_fallbacks()` retries the primary first (usually right);
    # `.with_fallbacks().with_retry()` retries the whole fallback ladder (rarely).
    ladder = FlakyChatModel(fail_times=99).with_retry(
        retry_if_exception_type=(ConnectionError,),
        stop_after_attempt=2,
        wait_exponential_jitter=False,
    ).with_fallbacks([backup])
    print("retry-then-fallback ->", ladder.invoke("hello").content)


# ---------------------------------------------------------------------------
def demo_6_astream_events() -> None:
    rule("6. astream_events -- the API you debug with")

    chain = (
        ChatPromptTemplate.from_template("{q}")
        | MODEL
        | StrOutputParser()
    ).with_config(run_name="faq_chain")

    async def run() -> None:
        counts: dict[str, int] = {}
        first_token_at: float | None = None
        t0 = time.perf_counter()
        async for event in chain.astream_events({"q": "latency?"}):
            counts[event["event"]] = counts.get(event["event"], 0) + 1
            if event["event"] == "on_chat_model_stream" and first_token_at is None:
                first_token_at = time.perf_counter() - t0
        for name, count in counts.items():
            print(f"  {name:26s} x{count}")
        if first_token_at is not None:
            print(f"  time-to-first-token: {first_token_at * 1000:.2f} ms")

    asyncio.run(run())
    print("\n  Every nested runnable emits start/stream/end with a run_id and parent_ids.")
    print("  This is exactly what LangSmith ships over the wire -- see ../langsmith/.")


# ---------------------------------------------------------------------------
def demo_7_token_accounting() -> None:
    rule("7. Counting tokens without a vendor dashboard")

    chain = ChatPromptTemplate.from_template("{q}") | MODEL

    totals = {"input_tokens": 0, "output_tokens": 0}
    for q in ("kubernetes?", "embedding?", "latency?"):
        msg = chain.invoke({"q": q})
        usage = msg.usage_metadata or {}
        totals["input_tokens"] += usage.get("input_tokens", 0)
        totals["output_tokens"] += usage.get("output_tokens", 0)
        print(f"  {q:14s} in={usage.get('input_tokens')} out={usage.get('output_tokens')}")
    print("  totals:", totals)
    print("\n  Real providers populate `AIMessage.usage_metadata` the same way, with")
    print("  input_token_details.cache_read when prompt caching hits. For an aggregate")
    print("  across many calls, langchain_core.callbacks.get_usage_metadata_callback()")
    print("  is a context manager that sums usage by model name.")


if __name__ == "__main__":
    demo_1_the_smallest_chain()
    demo_2_the_four_verbs()
    demo_3_parallel_and_passthrough()
    demo_4_configurable_fields()
    demo_5_retry_and_fallbacks()
    demo_6_astream_events()
    demo_7_token_accounting()
    rule("Done")
    print("Next: tools_and_structured_output.py, then mini_rag_chain.py.")
