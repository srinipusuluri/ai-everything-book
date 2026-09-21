"""
Async Python for LLM workloads -- concurrency, rate limiting, and retries.

Why this file exists
--------------------
An LLM call is 99.9% waiting. A 2-second completion spends about 2 milliseconds
of CPU on your side and the rest blocked on a socket. If you write

    for prompt in prompts:
        results.append(client.complete(prompt))

you have built a machine whose throughput is 1/latency, forever, no matter how
many cores you own. Fixing that does not require threads, processes, or a faster
machine. It requires `await`.

This script contains NO network calls. It fakes an LLM provider with realistic
latency, a token-bucket-ish concurrency cap, transient 503s and 429s, so you can
watch the mechanics without an API key and without spending money.

What it demonstrates
    1. sequential vs asyncio.gather -- the headline number
    2. asyncio.Semaphore as a concurrency limiter (the thing that keeps you
       under a provider's rate limit)
    3. retry with exponential backoff + FULL JITTER, and why jitter is not optional
    4. per-request timeouts, and gather(return_exceptions=True) so one bad
       request does not destroy a batch
    5. as_completed / TaskGroup for streaming results as they land
    6. the CPU-bound trap: what happens when you block the event loop

    python code/async_llm_client.py

Requires: stdlib only. Runs offline. ~15 seconds.
"""
from __future__ import annotations

import asyncio
import random
import sys
import time
from dataclasses import dataclass, field

# Seeded so the failure pattern is reproducible across runs. Every retry demo
# you will ever write needs this, or your "flaky test" is just your RNG.
RNG = random.Random(11)


# =========================================================================== #
# 0. The fake provider                                                        #
# =========================================================================== #
class RateLimitError(RuntimeError):
    """Provider said 429. Retryable, and you should back off hard."""


class ServerError(RuntimeError):
    """Provider said 5xx. Retryable."""


class BadRequestError(RuntimeError):
    """Provider said 400. NOT retryable -- retrying a malformed request just
    burns your budget more slowly. The single most common retry bug is treating
    every exception as transient."""


@dataclass
class Usage:
    calls: int = 0
    retries: int = 0
    failures: int = 0
    latencies: list[float] = field(default_factory=list)


class FakeLLMClient:
    """Simulates a provider. Latency is lognormal-ish (LLM latency has a long
    right tail -- the p99 is what wakes you up, not the mean). Failures are
    injected at a fixed rate."""

    def __init__(self, base_latency: float = 0.25, fail_rate: float = 0.25) -> None:
        self.base_latency = base_latency
        self.fail_rate = fail_rate
        self.usage = Usage()
        self._in_flight = 0
        self.max_in_flight = 0

    async def complete(self, prompt: str) -> str:
        self.usage.calls += 1
        self._in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self._in_flight)
        try:
            # Long-tail latency: most calls near base, a few much slower.
            latency = self.base_latency * RNG.lognormvariate(0.0, 0.45)
            # `await asyncio.sleep` is the whole point: it yields control back to
            # the event loop, which is free to run 200 other coroutines meanwhile.
            # `time.sleep` would block the loop and every one of them. Never mix.
            await asyncio.sleep(latency)
            self.usage.latencies.append(latency)

            roll = RNG.random()
            if roll < self.fail_rate * 0.6:
                raise ServerError("503 upstream connect error")
            if roll < self.fail_rate:
                raise RateLimitError("429 rate_limit_error: too many tokens per minute")
            if "\x00" in prompt:
                raise BadRequestError("400 invalid_request_error: bad payload")

            return f"[answer to {prompt!r} in {latency * 1000:.0f}ms]"
        finally:
            self._in_flight -= 1


# =========================================================================== #
# 1. Retry with exponential backoff and full jitter                           #
# =========================================================================== #
RETRYABLE = (ServerError, RateLimitError, asyncio.TimeoutError)


async def complete_with_retry(
    client: FakeLLMClient,
    prompt: str,
    *,
    max_attempts: int = 5,
    base: float = 0.1,
    cap: float = 4.0,
    per_call_timeout: float = 2.0,
    trace: list[str] | None = None,
) -> str:
    """One LLM call, made durable.

    Backoff schedule -- "full jitter", the variant AWS recommended after
    measuring the alternatives:

        sleep = random.uniform(0, min(cap, base * 2**attempt))

    Why the randomness matters: if 500 workers all get 429'd by the same
    overloaded provider at the same instant and all sleep exactly 1.0s, they
    all wake at the same instant and hit it again. That is a thundering herd,
    and it is how a brief blip becomes a sustained outage. Jitter smears the
    retries across the window so the provider sees a ramp, not a wall.

    Note what is NOT retried: BadRequestError. A 400 will be a 400 forever.
    """
    last: Exception | None = None
    for attempt in range(max_attempts):
        try:
            # asyncio.timeout (3.11+) is the modern per-operation deadline. It
            # cancels the inner coroutine and raises TimeoutError here.
            async with asyncio.timeout(per_call_timeout):
                return await client.complete(prompt)
        except BadRequestError:
            client.usage.failures += 1
            raise                                     # fail fast, do not retry
        except RETRYABLE as e:
            last = e
            client.usage.retries += 1
            if attempt == max_attempts - 1:
                break
            delay = RNG.uniform(0.0, min(cap, base * (2 ** attempt)))
            if trace is not None:
                trace.append(
                    f"    attempt {attempt + 1} of {prompt}: {type(e).__name__} "
                    f"-> sleeping {delay * 1000:.0f}ms"
                )
            await asyncio.sleep(delay)
    client.usage.failures += 1
    raise RuntimeError(f"gave up on {prompt!r} after {max_attempts} attempts") from last


# =========================================================================== #
# 2. Sequential vs concurrent                                                 #
# =========================================================================== #
async def run_sequential(client: FakeLLMClient, prompts: list[str]) -> list[str]:
    """Correct, simple, and throughput-bound by a single request's latency."""
    return [await complete_with_retry(client, p) for p in prompts]


async def run_gathered(client: FakeLLMClient, prompts: list[str]) -> list[str]:
    """asyncio.gather schedules every coroutine on the loop at once and waits
    for all of them. Results come back in ARGUMENT order, not completion order,
    which is why gather is the right tool for batch work: prompts[i] lines up
    with results[i] and you never need to carry an index around.

    return_exceptions=True turns a failure into a value in the list rather than
    a raised exception that discards all the other successful results. For a
    batch job this is almost always what you want -- you paid for those tokens.
    """
    coros = [complete_with_retry(client, p) for p in prompts]
    return await asyncio.gather(*coros, return_exceptions=True)


# =========================================================================== #
# 3. Bounded concurrency: the semaphore                                       #
# =========================================================================== #
class RateLimitedClient:
    """gather() with 5,000 prompts opens 5,000 sockets, and the provider answers
    with 429s for all of them. A semaphore is the fix and it is four lines.

    Pick the limit from the provider's documented concurrency, or derive it:
        max_concurrency ~= target_RPS * average_latency_seconds  (Little's Law)
    30 requests/sec at 2s average latency needs ~60 in flight. Not 5,000.
    """

    def __init__(self, client: FakeLLMClient, max_concurrency: int = 8) -> None:
        self.client = client
        self.sem = asyncio.Semaphore(max_concurrency)

    async def complete(self, prompt: str, trace: list[str] | None = None) -> str:
        # `async with` on a Semaphore acquires a slot, suspends if none is free,
        # and ALWAYS releases -- including on exception or cancellation. Hand-
        # rolling acquire()/release() around a try/finally is a leak waiting to
        # happen; a leaked slot permanently shrinks your concurrency.
        async with self.sem:
            return await complete_with_retry(self.client, prompt, trace=trace)

    async def complete_many(self, prompts: list[str]) -> list[str | BaseException]:
        return await asyncio.gather(
            *(self.complete(p) for p in prompts), return_exceptions=True
        )


# =========================================================================== #
# Demos                                                                       #
# =========================================================================== #
def banner(n: int, title: str) -> None:
    print()
    print("=" * 76)
    print(f"{n}. {title}")
    print("=" * 76)


async def demo_backoff() -> None:
    banner(1, "Retry with exponential backoff + full jitter")
    client = FakeLLMClient(base_latency=0.05, fail_rate=0.55)   # deliberately flaky
    trace: list[str] = []
    print("  Calling a provider that fails 55% of the time. The backoff CEILING")
    print("  doubles each attempt (80ms, 160ms, 320ms...) but the sleep actually")
    print("  taken is a uniform draw below it. That randomness is the jitter.")
    print()
    for i in range(4):
        outcome: str
        try:
            out = await complete_with_retry(client, f"p{i}", base=0.08, trace=trace)
            outcome = f"  p{i}: OK   {out}"
        except RuntimeError as e:
            outcome = f"  p{i}: DEAD {e}"
        for line in trace:          # the retries happened first, so print them first
            print(line)
        print(outcome)
        trace.clear()
    print()
    print(f"  {client.usage.calls} HTTP calls for 4 logical requests "
          f"({client.usage.retries} retries).")
    print("  That multiplier is your real cost. Budget for it, and alert on it:")
    print("  a rising retry rate is the earliest signal that a provider is sick.")


async def demo_sequential_vs_gather() -> None:
    banner(2, "Sequential vs asyncio.gather -- the headline number")
    prompts = [f"summarise doc {i}" for i in range(24)]

    seq_client = FakeLLMClient(base_latency=0.25, fail_rate=0.10)
    t0 = time.perf_counter()
    await run_sequential(seq_client, prompts)
    seq_time = time.perf_counter() - t0

    par_client = FakeLLMClient(base_latency=0.25, fail_rate=0.10)
    t0 = time.perf_counter()
    results = await run_gathered(par_client, prompts)
    par_time = time.perf_counter() - t0

    errs = sum(isinstance(r, BaseException) for r in results)
    print(f"  prompts                  : {len(prompts)}")
    print(f"  simulated latency        : ~250 ms each, 10% transient failure rate")
    print()
    print(f"  sequential (for + await) : {seq_time:6.2f} s")
    print(f"  asyncio.gather           : {par_time:6.2f} s")
    print(f"  speedup                  : {seq_time / par_time:6.1f}x")
    print(f"  peak concurrent requests : {par_client.max_in_flight}")
    print(f"  failed after retries     : {errs}")
    print()
    print("  Sequential time ~= n * latency. Gathered time ~= the SLOWEST call,")
    print("  plus whatever retries added. You did not make anything faster; you")
    print("  stopped making the CPU wait in a queue it had no business being in.")
    print()
    print("  The `for p in prompts: await ...` line is the most expensive line of")
    print("  Python in the LLM ecosystem. It is also the most common.")


async def demo_semaphore() -> None:
    banner(3, "Bounded concurrency with asyncio.Semaphore")
    prompts = [f"classify ticket {i}" for i in range(60)]

    for limit in (60, 8):
        client = FakeLLMClient(base_latency=0.15, fail_rate=0.10)
        limited = RateLimitedClient(client, max_concurrency=limit)
        t0 = time.perf_counter()
        await limited.complete_many(prompts)
        dt = time.perf_counter() - t0
        label = "unbounded (limit = n)" if limit == 60 else f"semaphore(limit={limit})"
        print(f"  {label:<24} {dt:5.2f} s   peak in flight = {client.max_in_flight:>2}"
              f"   http calls = {client.usage.calls}")

    print()
    print("  Unbounded is faster here because the fake provider has no real")
    print("  capacity limit. A real one does. Unbounded against a real provider")
    print("  means 429s, which mean retries, which mean MORE load -- the classic")
    print("  congestion collapse. The semaphore trades a little latency for a")
    print("  system that degrades smoothly instead of falling over.")
    print()
    print("  Sizing: max_concurrency ~= target_RPS * avg_latency (Little's Law).")
    print("  Then set it 20% below the provider's documented cap and alert on 429s.")


async def demo_as_completed() -> None:
    banner(4, "Streaming results: as_completed and TaskGroup")
    client = FakeLLMClient(base_latency=0.2, fail_rate=0.0)
    prompts = [f"q{i}" for i in range(6)]

    print("  gather() gives you everything at the end, in argument order.")
    print("  as_completed() gives you each result the instant it lands -- use it")
    print("  when a human is watching a progress bar, or when you want to start")
    print("  downstream work (embedding, writing to a DB) before the batch ends.")
    print()
    t0 = time.perf_counter()
    coros = [client.complete(p) for p in prompts]
    done = 0
    for fut in asyncio.as_completed(coros):
        result = await fut
        done += 1
        print(f"    +{time.perf_counter() - t0:5.2f}s  [{done}/{len(prompts)}] {result}")

    print()
    print("  The order is not q0..q5. as_completed loses the mapping back to")
    print("  the input unless you carry it yourself -- wrap each call so it returns")
    print("  (index, result), or use a dict of task -> input.")
    print()
    print("  asyncio.TaskGroup (3.11+) is the third option and the best default for")
    print("  structured work: if any child task raises, the rest are cancelled and")
    print("  you get an ExceptionGroup. No orphaned tasks, no silent leaks.")

    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(client.complete(f"tg{i}")) for i in range(3)]
    print(f"    TaskGroup finished {len(tasks)} tasks, all awaited on block exit.")


async def demo_blocking_the_loop() -> None:
    banner(5, "The trap: blocking the event loop")
    print("  asyncio is ONE thread running a scheduler. A coroutine that does not")
    print("  await keeps that thread until it returns. Everything else is frozen.")
    print()

    async def cooperative(i: int) -> float:
        await asyncio.sleep(0.15)
        return time.perf_counter()

    async def selfish(i: int) -> float:
        # A synchronous 0.15s of work -- a tight numeric loop, json.loads on a
        # 50 MB file, a `requests.get`, or time.sleep. All the same sin.
        t_end = time.perf_counter() + 0.15
        while time.perf_counter() < t_end:
            pass
        return time.perf_counter()

    t0 = time.perf_counter()
    await asyncio.gather(*(cooperative(i) for i in range(8)))
    good = time.perf_counter() - t0

    t0 = time.perf_counter()
    await asyncio.gather(*(selfish(i) for i in range(8)))
    bad = time.perf_counter() - t0

    print(f"  8 x 0.15s awaiting        : {good:5.2f} s  <- overlapped, as intended")
    print(f"  8 x 0.15s CPU-spinning    : {bad:5.2f} s  <- serialised, loop held hostage")
    print()
    print("  The fix for genuinely blocking work inside async code:")
    print("    await asyncio.to_thread(blocking_fn, *args)        # IO or C that releases the GIL")
    print("    await loop.run_in_executor(ProcessPoolExecutor(), fn, *args)   # real CPU work")
    print()
    print("  Use `python -X dev` and asyncio debug mode (PYTHONASYNCIODEBUG=1) --")
    print("  it logs a warning whenever a callback holds the loop over 100 ms.")


def gil_note() -> None:
    banner(6, "Concurrency vs parallelism, and the GIL in 2026")
    print(f"""
  Three different problems, three different tools:

    asyncio          concurrency, one thread. For IO-bound work: HTTP, DB,
                     disk, queues. LLM calls are IO-bound. This is your default.
    threads          concurrency, many threads, one GIL. Useful for blocking
                     libraries you cannot make async. NumPy/torch release the
                     GIL during compute, so threads DO help there.
    processes        true parallelism. For CPU-bound Python: preprocessing,
                     tokenizing, chunking a corpus. Pays a pickling tax.

  GIL status, honestly:
    * CPython has had a Global Interpreter Lock forever -- only one thread runs
      Python bytecode at a time. It is why threads do not speed up pure-Python
      compute, and it is why multiprocessing exists.
    * PEP 703 made a free-threaded (no-GIL) build official. It shipped as an
      EXPERIMENTAL build in 3.13, and in 3.14 the free-threaded build became a
      supported, non-experimental option -- still not the default interpreter,
      and still requiring C extensions to be built for it.
    * Practically, in 2026: assume the GIL. Check with sys._is_gil_enabled()
      if you need to branch. The free-threaded build is worth benchmarking for
      CPU-heavy data prep; it is not yet where you deploy a service by default.
    * None of this matters for LLM calls. Your bottleneck is a provider 80 ms
      away, not your interpreter. Reach for asyncio, not for a no-GIL build.

  This interpreter: Python {sys.version.split()[0]}, GIL enabled = {getattr(sys, "_is_gil_enabled", lambda: True)()}
""".rstrip())


def httpx_note() -> None:
    banner(7, "What this looks like against a real provider")
    print("""
  Everything above is provider-agnostic. In real code:

    import httpx

    # ONE client for the process lifetime. Creating a client per request throws
    # away connection pooling and TLS session reuse -- typically 30-80 ms of
    # handshake per call, which at 1000 calls is a minute of pure waste.
    limits = httpx.Limits(max_connections=64, max_keepalive_connections=32)
    timeout = httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0)

    async with httpx.AsyncClient(limits=limits, timeout=timeout) as http:
        ...

  Four rules that cover most production incidents:

    1. Set a READ timeout that fits your longest generation, not the library
       default. A long completion is not a hung socket; httpx's 5s default will
       cancel perfectly healthy requests.
    2. Respect Retry-After on a 429. The provider is telling you the answer;
       your backoff formula is a guess. Use the header when it is present.
    3. The official SDKs (anthropic, openai) already retry with backoff and
       jitter internally. Check max_retries before adding your own layer --
       stacked retries multiply: 3 x 3 = 9 calls for one logical request.
    4. Idempotency: a retry after a timeout may duplicate work the provider
       already did. For anything with a side effect, send an idempotency key.

  Where this returns: Module 06/07 (agents issue many tool calls per turn),
  Module 08 (embed thousands of chunks -- pure gather + semaphore work),
  Module 15 (running an eval suite is this script with real prompts).
""".rstrip())


async def main() -> int:
    print()
    print(f"Async LLM patterns -- Python {sys.version.split()[0]}, no network required")
    await demo_backoff()
    await demo_sequential_vs_gather()
    await demo_semaphore()
    await demo_as_completed()
    await demo_blocking_the_loop()
    gil_note()
    httpx_note()
    print()
    print("Done. If you take one thing: `for x in xs: await f(x)` is a bug in")
    print("disguise, and `asyncio.gather` without a Semaphore is the next one.")
    print()
    return 0


if __name__ == "__main__":
    # asyncio.run() creates a loop, runs the coroutine, and tears the loop down
    # cleanly -- cancelling leftover tasks and closing async generators. Do not
    # hand-manage loops with get_event_loop(); that API has been a footgun for
    # a decade and is deprecated for this use.
    raise SystemExit(asyncio.run(main()))
