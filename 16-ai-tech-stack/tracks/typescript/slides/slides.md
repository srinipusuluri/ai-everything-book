---
marp: true
theme: default
paginate: true
style: |
  section h1 { color: #3178C6; }
  section { font-size: 24px; }
---

# TypeScript for AI Applications

### Python trains the model. TypeScript ships the product.

**Module 16.2** · AI End-to-End Learning Track

---

## Why this track exists

- Once the model is an HTTP call, the product language is what matters
- The application layer is streaming, tools, cancellation, and the edge
- One lesson underneath everything: types do not exist at runtime
- Target: ship a streaming chat route that survives a hostile model

<!-- speaker note: Set the frame early. This is not a TypeScript tutorial; it is the engineering of the layer between a model endpoint and a user. -->

---

## The division of labour

- Python: data prep, training, eval, a model behind an HTTP API
- TypeScript: routes, tool execution, streaming, auth, quotas, the UI
- The contract between them is JSON over HTTPS -- that is all
- Do NOT rewrite your eval harness or data pipeline in TypeScript

<!-- speaker note: The last bullet is the honest counter-argument. The Python ecosystem gap for training and evals is not closing. -->

---

## Why TypeScript won this layer

| Reason | What it buys you |
|---|---|
| One language, client to server | one Message type, no codegen, no drift |
| Streaming is native | ReadableStream and async iterators are platform APIs |
| Edge runtimes run JS | Workers, Vercel Edge, Deno Deploy, Bun |
| Type-safe tool schemas | one Zod schema = validator + type + JSON Schema |
| SDKs are TypeScript-first | not ports; the types encode the real API shape |


<!-- speaker note: Row 4 is the one people underrate. Three artifacts from one declaration is the whole pitch for Zod. -->

---

## Discriminated unions carry everything

- Almost every LLM API object is a tagged union on a 'type' field
- Content blocks: text | thinking | tool_use | tool_result
- Stream events: message_start | content_block_delta | error | ...
- Narrowing on the discriminant gives you the right member for free
- Stop writing your own ChatMessage -- import the SDK's types

<!-- speaker note: A hand-rolled { role: string; content: unknown } is strictly worse than Anthropic.MessageParam. It loses the literal union and the block discrimination. -->

---

## Exhaustiveness checking: five lines that pay rent

- function assertNever(x: never): never { throw new Error(...) }
- Put it in the default case of every switch over a union
- Providers ADD stream event types -- your build should fail, not your UI
- Without it, a 'default: break' silently drops a whole feature
- Pair with noFallthroughCasesInSwitch

<!-- speaker note: This is the highest-leverage five lines in an AI codebase. Demo it live: add a union member, watch tsc name the case you forgot. -->

---

## The central fact

> **A TypeScript type does not exist at runtime. The model has never seen your tsconfig.**

- tsc cannot check a network response
- Structured outputs reduce the odds; they do not remove them
- In the lab demo, 3 of 5 tool calls from a 'good' model were malformed
- Compile-time types describe intent. Only a validator enforces it

<!-- speaker note: Run code/typed-tool-calling.ts on screen here. The score card slide at the end of that script sells the point better than any argument. -->

---

## Zod: one declaration, three artifacts

- z.infer<typeof S>            -> the static type
- S.safeParse(modelOutput)     -> the runtime check
- z.toJSONSchema(S, {io:'input'}) -> what you send the model
- The alternative is three files that silently drift apart
- Nothing links a hand-written schema to a hand-written interface

<!-- speaker note: Emphasise that the JSON Schema is DERIVED. The number one cause of bad tool calls is a schema that no longer matches the validator. -->

---

## Zod rules for model-facing schemas

| Rule | Why |
|---|---|
| safeParse, never parse | a throw is a dead turn in an agent loop |
| .describe() every field | becomes the JSON Schema description; cheapest accuracy win |
| .nullable() over .optional() | models emit explicit null better than they omit keys |
| io: 'input' for tool schemas | defaults change which fields are required |
| z.prettifyError back to the model | models usually self-repair on the next turn |


<!-- speaker note: Row 4 is subtle: a field with .default() is optional on input and always present on output. Get it backwards and you lie to the model. -->

---

## Gotcha: zod-to-json-schema on Zod v4

- Zod v4 ships z.toJSONSchema() natively -- use it
- Point the old package at a v4 schema and it does NOT throw
- It reads v3 internals, finds nothing, and returns {}
- An empty schema = zero constraints = the model invents fields
- Silent in dev, loud in prod. Keep the package only if pinned to v3

<!-- speaker note: Section 2 of typed-tool-calling.ts prints the empty definitions object. Show it. This class of silent-degradation bug is the worst kind. -->

---

## Streaming is a product requirement

- Time-to-first-token is what users feel; total latency is what dashboards show
- 600 tokens is 8-20 seconds of spinner without it
- Streaming is also your only cancellation point
- A non-streaming request bills you even after the user leaves
- Three layers: SSE framing, event semantics, your own UI transport

<!-- speaker note: Transition into streaming here. You should almost never write layer 1 -- the SDK does it. Write it only when proxying and re-framing, or debugging someone else's parser. Ask who has written an SSE parser, then ask if they tested it at one-byte chunks. -->

---

## The five streaming bugs, in order

| Bug | Symptom | Fix |
|---|---|---|
| New TextDecoder per chunk | accented chars and emoji become U+FFFD | one decoder, {stream:true} |
| Split on blank line, drop rest | random missing sentences under load | buffer across chunks |
| No final flush | last token silently truncated | decode() with no args, drain buffer |
| Ignoring the error event | half a sentence, HTTP 200, no log | handle it in the switch |
| Proxy buffers the body | streaming code, non-streaming UX | no-transform, X-Accel-Buffering: no |


<!-- speaker note: Bugs 1 to 3 are one bug in three hats: chunk boundaries are not message boundaries. TCP knows nothing about SSE frames or code points. -->

---

## Why these bugs ship

> **On localhost the whole response arrives in one 4KB read, so every test passes.**

- A CDN, a proxy, or a slow mobile link slices it anywhere
- The naive parser is correct at 4096 bytes and empty at 7 bytes
- Test your parser at chunkBytes = 1. If it passes there, it passes anywhere
- Record one real SSE response and replay it at five chunk sizes

<!-- speaker note: The recorded-fixture replay test is the highest-value test in an AI codebase and almost nobody writes it. -->

---

## Cancellation, end to end

- Stop button -> client AbortController -> connection closes
- -> server Request.signal -> provider request aborted -> billing stops
- Every link must be connected or you have a decorative Stop button
- Treat AbortError as normal control flow, not a 500
- Breaking a 'for await' loop calls return() and cleans up for you

<!-- speaker note: Backpressure comes free from await in a for-await loop, and from pull() in a ReadableStream. Pushing everything in start() reinvents an unbounded buffer. -->

---

## Three SDKs, three jobs

| Library | What it is | Reach for it when |
|---|---|---|
| ai (Vercel AI SDK) | provider-agnostic facade + UI hooks | building a chat product, want portability |
| @anthropic-ai/sdk | official client, full API surface | caching, thinking, server tools, batches |
| @anthropic-ai/claude-agent-sdk | Claude Code as a library | coding or filesystem agent, tools included |


<!-- speaker note: Do not confuse the Agent SDK with the API SDK's beta tool runner. The tool runner loops over tools YOU define and has no built-in tools. -->

---

## AI SDK: the line that earns its keep

- streamText({ model, messages, tools }) with Zod inputSchema per tool
- return result.toUIMessageStreamResponse()
- useChat() on the client already speaks that protocol
- generateObject / streamObject give you validated typed output
- v5 renamed a lot -- check ai-sdk.dev before trusting any snippet

<!-- speaker note: maxTokens became maxOutputTokens, CoreMessage became ModelMessage, toDataStreamResponse became toUIMessageStreamResponse, hooks moved to @ai-sdk/react. -->

---

## Runtimes

| Runtime | Strength | What bites you |
|---|---|---|
| Node 20/22/24 | everything works; the default | cold starts, ESM/CJS interop |
| Bun | fast installs and startup, TS native | occasional Node-API gaps |
| Deno | secure by default, web standards | npm compat good, not invisible |
| Cloudflare Workers | global, near-zero cold start | V8 isolate, no fs, CPU caps |
| Vercel Edge | same isolate, Next.js integrated | duration limits vary by plan |


<!-- speaker note: Opinion: run the streaming chat route at the edge where TTFT matters, keep the agent loop and anything touching a filesystem on Node. -->

---

## What actually breaks on the edge

- No filesystem: no fs, no __dirname, no path-based asset loading
- Node built-ins are opt-in (nodejs_compat); net and child_process never work
- CPU time is capped; waiting on a stream is I/O, so that part is fine
- Response duration limits: a 10-minute agent run is not a request handler
- Background work must use waitUntil() or it is killed with the response

<!-- speaker note: The floating-promise-for-logging pattern is the most common edge bug. It works in dev and silently drops your analytics in production. -->

---

## The tsconfig flags that actually matter

| Flag | What it catches |
|---|---|
| strict | table stakes, not a finish line |
| noUncheckedIndexedAccess | arr[0] is T|undefined -- the empty-content case |
| exactOptionalPropertyTypes | missing vs null; providers treat them differently |
| verbatimModuleSyntax | forces import type; kills ESM/CJS surprises |
| module: bundler (not node) | understands package exports maps |


<!-- speaker note: Turn them on one at a time on an existing codebase and count how many new errors were real bugs. That is exercise 6 in the lab. -->

---

## Toolchain, and the mistake everyone makes

- pnpm for installs, vitest for tests, biome for lint and format
- Go ESM-only: 'type': 'module', no dual build, no three-day tax
- tsx and esbuild DO NOT typecheck -- they strip types and run
- If tsc --noEmit is not in CI, you do not have types, you have comments
- Test parsers and schemas offline; run live evals on a schedule, not in CI

<!-- speaker note: The tsx bullet is the one to dwell on. People ship type errors for months because the app runs fine locally. -->

---

## Your exit check

- A POST /api/chat that streams SSE and validates input with Zod
- One Zod tool; bad arguments return tool_result is_error, never a throw
- Client disconnect aborts the provider call and logs 'cancelled'
- Clean under strict + noUncheckedIndexedAccess + exactOptionalPropertyTypes
- A test replaying a recorded SSE fixture at 1-byte and 4096-byte chunks

<!-- speaker note: If the last bullet passes, they have beaten the bug that ships in most AI products. Point them at lab/EXERCISES.md and the python sibling track. -->

---

## Now go build

`code/` run it · `lab/EXERCISES.md` break it · `papers/` go deeper
