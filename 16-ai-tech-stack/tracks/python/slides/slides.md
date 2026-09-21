---
marp: true
theme: default
paginate: true
style: |
  section h1 { color: #3776AB; }
  section { font-size: 24px; }
---

# Python for AI Engineering

### The 20% of modern Python that every AI system is built on

**Module 16.1** · AI End-to-End Learning Track

---

## Why this track exists

- Every other track in Module 16 assumes you can write shippable Python
- Python won as glue over C, CUDA, Arrow and Rust kernels -- know the seams
- Not Python that runs -- Python that is typed, tested, packaged, async
- That gap is why most prototypes never become services
- This is not 'learn Python'. It is the 2026 toolchain, not the 2018 one

<!-- speaker note: Set the frame: the audience can already program. We teach the idioms and the toolchain, not the syntax. Python is not the best language; it is the one with the ecosystem. -->

---

## Part 1 -- The toolchain

*uv, pyproject.toml, ruff, mypy, pytest*


<!-- speaker note: About 25 minutes. This is the part people can adopt the same afternoon. -->

---

## uv: stop thinking about environments

- uv init my-service  -- pyproject.toml + src/ layout in one second
- uv add anthropic pydantic httpx  -- resolve, install, lock, record
- uv run pytest  -- you never 'source activate' again
- uv sync  -- make this machine match uv.lock exactly
- pyproject.toml holds deps, entry points AND all tool config. One file
- 10-100x faster than pip. Commit uv.lock; never commit .venv/

<!-- speaker note: The speed is not vanity: it changes how often people run CI and how willingly they rebuild environments. Demo it live - it is under ten seconds. Lower bounds go in pyproject, exact pins in uv.lock. -->

---

## The packaging landscape, decided

| Tool | Use it? | Verdict |
|---|---|---|
| uv | Yes -- default | One Rust binary, manages Python versions too |
| pip + venv | Only as fallback | Works, slow, does not lock |
| poetry | Legacy projects only | Fine but slower; do not start here |
| pipenv | No | Effectively dead |
| conda / pixi | Binary-heavy stacks | The only remaining good reason |


<!-- speaker note: Have an opinion. The worst outcome is a team where three people use three tools. -->

---

## ruff: lint and format in one, instantly

- Replaces flake8, isort, black, pyupgrade, pydocstyle, autoflake
- Sub-second on a large repo -- so you run it on save, not in CI only
- select = [E, F, I, B, UP, SIM, ASYNC, RUF]
- B (bugbear) catches the mutable-default-argument bug for free
- ASYNC flags blocking calls inside async functions -- real value for LLM code
- Do not argue about formatting. Hook it and reclaim the meeting

<!-- speaker note: The ASYNC ruleset is underrated. It catches requests.get() inside an async def, which is the number one asyncio bug in LLM codebases. -->

---

## Types: what they buy, what they do not

| Construct | Runtime cost | Validates? | Use for |
|---|---|---|---|
| type hint | none | no | the checker, the editor, the next human |
| TypedDict | none -- it IS a dict | no | API request/response payloads |
| dataclass | low | no | internal structs, state you created |
| Protocol | none | no | typing 'an LLM client' without a vendor base class |
| Pydantic BaseModel | moderate, Rust core | YES | anything crossing a trust boundary |


<!-- speaker note: Hints are NOT enforced at runtime. embed(42) runs fine. Say this out loud - it is the single most misunderstood thing about Python typing. -->

---

## The decision rule

> **Data you created -> dataclass. Data someone else created -> Pydantic.**

- LLM output is data someone else created
- And that someone is a stochastic text generator
- mypy in CI, pyright in the editor. Running both is normal
- On legacy code: ratchet strictness per module, never all at once

<!-- speaker note: This one line resolves 90% of 'should I use a dataclass or a model' arguments. -->

---

## Pydantic v2: one class, three jobs

- model_json_schema() -> the tool schema you SEND the provider
- model_validate() -> validation of what you GET BACK
- typed attributes -> your checker and IDE understand the result
- Schema and parser cannot drift, because they are the same class
- Field order = generation order: put evidence BEFORE the judgement
- Enums, not free strings. ge/le on every number. extra='forbid'

<!-- speaker note: The evidence-before-judgement trick smuggles chain-of-thought into a schema. It is worth real accuracy on extraction tasks and costs nothing. -->

---

## Part 2 -- Making it fast

*Vectorization, broadcasting, and the memory nobody measures*


<!-- speaker note: Switch gears. Run code/vectorization_benchmark.py live here if the room has a terminal. -->

---

## The benchmark that ends the argument

| Approach | Time | Speedup |
|---|---|---|
| Pure Python triple loop | 1.12 s | 1x |
| NumPy INSIDE a Python loop | 214 ms | 5x |
| Broadcasting | 15.6 ms | 72x |
| BLAS gemm identity | 0.34 ms | 3295x |


<!-- speaker note: Row 2 is the teaching moment. Importing numpy does not make code fast; removing the Python loop does. Row 2 is 120,000 dispatches into C, each paying fixed overhead. -->

---

## Broadcasting has a bill, payable in bytes

- (300,1,128) - (1,400,128) -> materialises (300,400,128)
- That is 122.9 MB of temporary for a 0.96 MB answer -- 128x
- Scale to 20k x 20k embeddings: 409 GB. Same line of code
- Rule: every added dimension, compute what it costs in bytes
- float64 is NumPy's default and nobody's actual precision -- cast to float32

<!-- speaker note: The OOM kill is the failure mode. Fix is chunking the outer loop, or an algebraic identity that avoids the intermediate entirely. -->

---

## The bug that ships

> **x = emb - emb.mean(axis=1)   # you meant axis=0**

- On a (5,3) array this raises ValueError -- a gift
- On a SQUARE batch the shapes align and it silently computes garbage
- No exception, no warning, plausible numbers, eval 4% worse
- Fix: keepdims=True on every reduction you will broadcast against
- Never smoke-test with a square batch. 32x32 hides every axis bug

<!-- speaker note: Ask the room who has shipped this. Hands will go up. This is the only bug on the whole list that produces no signal at all. -->

---

## Part 3 -- Async, because LLM calls are waiting

*gather, semaphores, backoff and jitter*


<!-- speaker note: Run code/async_llm_client.py here. The sequential-vs-gather number lands better as a live demo. -->

---

## The most expensive line in the LLM ecosystem

- for p in prompts: results.append(await client.complete(p))
- Throughput is 1/latency forever, regardless of your hardware
- await asyncio.gather(*(complete(p) for p in prompts))
- Measured: 24 prompts, 7.25 s sequential -> 0.76 s gathered
- An LLM call is 99.9% waiting. You did not go faster; you stopped queueing

<!-- speaker note: gather returns results in ARGUMENT order, not completion order. That is why it is the right tool for batch work - prompts[i] lines up with results[i]. -->

---

## Four rules on top of gather

| Rule | Why |
|---|---|
| Semaphore the concurrency | gather over 5000 prompts earns 5000 429s |
| Size it by Little's Law | max_conc ~= target_RPS * avg_latency_s |
| return_exceptions=True | one failure must not discard a paid-for batch |
| Backoff WITH full jitter | fixed sleeps make 500 workers wake together |
| Retry 429/5xx, never 400 | a 400 will be a 400 forever |
| Respect Retry-After | the header is the answer; your formula is a guess |


<!-- speaker note: Jitter is the part people drop and the part that matters. Without it a blip becomes a thundering herd and then an outage. -->

---

## Concurrency vs parallelism, and the GIL in 2026

- asyncio: IO-bound work, one thread, thousands of waits. Your default
- threads: help when the GIL is released -- NumPy, torch, IO all do
- processes: true parallelism for pure-Python CPU. Pays a pickling tax
- PEP 703 free-threaded build: experimental in 3.13, supported in 3.14
- Still not the default interpreter. Assume the GIL; benchmark before switching
- None of it matters for LLM calls -- you are blocked on a socket, not bytecode

<!-- speaker note: Correct the two common errors in both directions: threads do not speed up pure Python, but they DO help around numpy because the kernel releases the GIL. -->

---

## Never block the event loop

- time.sleep, requests.get, a tight loop, json.loads on 50 MB -- all freeze it
- Measured: 8 x 0.15s awaiting = 0.15s; 8 x 0.15s spinning = 1.20s
- Fix: await asyncio.to_thread(fn) or a ProcessPoolExecutor
- One httpx.AsyncClient per process, not per request (TLS reuse)
- Set a read timeout that fits your longest generation, not the default
- Check your SDK's built-in retries -- 3 x 3 = 9 calls per request

<!-- speaker note: PYTHONASYNCIODEBUG=1 warns whenever a callback holds the loop over 100ms. Turn it on in development and leave it on. -->

---

## Idioms that bite AI engineers

| Idiom | What it costs you |
|---|---|
| Mutable default arg | conversation history bleeds between users |
| Closure late binding | 100 deferred calls all use the last prompt |
| Float equality | similarity assertions that fail on another CPU |
| Silent broadcasting | no error, no warning, wrong numbers |
| pickle.load on untrusted data | arbitrary code execution from a model hub |
| Bare except: | your eval job becomes un-killable |


<!-- speaker note: Ruff catches rows 1 and 6 automatically. Row 5 is why safetensors exists and why torch.load takes weights_only=True. -->

---

## Testing code that calls a nondeterministic thing

- No network in the default run. Mark live tests and deselect them
- Mock at the CLIENT boundary via Protocol, not at the HTTP layer
- Test against BAD output: truncated, fenced, hallucinated enums
- Seed everything -- and know temperature=0 is still not determinism
- Assert tolerances and properties, not exact strings
- Snapshot the rendered PROMPT, not the completion. Keep it under 5 seconds

<!-- speaker note: Your production incidents make excellent test fixtures. The clean-response test passes on day one and never catches anything again. -->

---

## Your exit check

- A repo that installs with one uv sync, clean on ruff and mypy
- pytest under 5 seconds, LLM client mocked, zero network
- Pydantic-validated structured output with a bounded repair loop
- Model calls batched with gather under an explicit semaphore
- Run all three scripts in code/ -- they need no API key
- Then: the TypeScript track, or straight into LangChain

<!-- speaker note: The real check: a colleague clones it and gets a green run before their coffee cools. -->

---

## Now go build

`code/` run it · `lab/EXERCISES.md` break it · `papers/` go deeper
