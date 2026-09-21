# 📄 Primary Sources — TypeScript for AI Applications

There is no arXiv literature for "how to parse an SSE frame". The primary sources
for this track are **specifications and official documentation**, and reading the
spec is a genuinely different experience from reading a blog post about the spec.

Read them in this order.

## Read these three first

| # | Source | Why it matters | Link |
|---|--------|----------------|------|
| 1 | **WHATWG — Server-Sent Events** (HTML spec, §9.2) | The actual framing rules: `\n` vs `\r\n` vs `\r`, comment lines, multi-line `data:`, `id:`/`retry:`, and the last-event-id reconnect protocol. Every streaming bug in note 02 is a deviation from this document. | https://html.spec.whatwg.org/multipage/server-sent-events.html |
| 2 | **WHATWG — Encoding Standard** (§ TextDecoder, streaming flag) | Why `decode(chunk, { stream: true })` exists and precisely what the decoder holds back between calls. Ten minutes here permanently fixes the split-UTF-8 bug in your head. | https://encoding.spec.whatwg.org/ |
| 3 | **WHATWG — Streams Standard** | `ReadableStream`, the `pull`/`cancel` contract, and the definition of backpressure. The source of truth for every edge runtime's streaming behaviour. | https://streams.spec.whatwg.org/ |

## Type system

| Source | Takeaway | Link |
|---|---|---|
| TypeScript Handbook — Narrowing | Discriminated unions, type guards, and the `never` exhaustiveness trick, straight from the source | https://www.typescriptlang.org/docs/handbook/2/narrowing.html |
| TypeScript Handbook — Template Literal Types | What they can and cannot do; read before you build a type-level parser | https://www.typescriptlang.org/docs/handbook/2/template-literal-types.html |
| TypeScript 4.9 release notes — `satisfies` | The original motivation and the exact difference from `as` and from an annotation | https://www.typescriptlang.org/docs/handbook/release-notes/typescript-4-9.html |
| TSConfig Reference | Every compiler flag with an example of what it catches. The reference for note 02 §7 | https://www.typescriptlang.org/tsconfig/ |
| TypeScript performance wiki | Why your editor got slow, and which type constructs cost the most | https://github.com/microsoft/TypeScript/wiki/Performance |

## Validation & schemas

| Source | Takeaway | Link |
|---|---|---|
| Zod documentation | `safeParse`, `z.infer`, coercion, refinements, discriminated unions | https://zod.dev/ |
| Zod — JSON Schema conversion | `z.toJSONSchema()`, the `io: "input" \| "output"` distinction, and what is unrepresentable | https://zod.dev/json-schema |
| JSON Schema specification | What the model's tool schema actually means; `required`, `enum`, `additionalProperties` | https://json-schema.org/ |
| `zod-to-json-schema` | The Zod v3-era converter. Read the README to understand why it is legacy on v4 | https://github.com/StefanTerdell/zod-to-json-schema |

## The SDK layer

| Source | Takeaway | Link |
|---|---|---|
| Anthropic — Streaming Messages | The full event list (`message_start` → `message_stop`), delta types, and the raw SSE payloads | https://platform.claude.com/docs/en/build-with-claude/streaming |
| Anthropic — Tool use overview | `input_schema`, `tool_choice`, `tool_result`, `is_error`, parallel tool calls | https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview |
| Anthropic — Structured outputs | `output_config.format` and `strict: true` — schema enforcement at the API level | https://platform.claude.com/docs/en/build-with-claude/structured-outputs |
| `@anthropic-ai/sdk` source | Read `src/lib/MessageStream.ts` for a production-grade version of `code/streaming-parser.ts` | https://github.com/anthropics/anthropic-sdk-typescript |
| Claude Agent SDK docs | The agent harness: built-in tools, subagents, hooks, permissions, MCP | https://code.claude.com/docs/en/agent-sdk |
| Vercel AI SDK docs | `generateText` / `streamText` / `generateObject`, the `tool()` helper, UI message streams | https://ai-sdk.dev/docs |

## Runtimes

| Source | Takeaway | Link |
|---|---|---|
| Cloudflare Workers — Node.js compatibility | Exactly which Node built-ins exist behind `nodejs_compat`, and which never will | https://developers.cloudflare.com/workers/runtime-apis/nodejs/ |
| Cloudflare Workers — Limits | CPU time, memory, subrequests, and what "wall time is not CPU time" means for streaming | https://developers.cloudflare.com/workers/platform/limits/ |
| Vercel — Functions | Node vs Edge runtime, streaming responses, duration limits by plan | https://vercel.com/docs/functions |
| Node.js — ECMAScript modules | The ESM/CJS interop rules, `import.meta.url`, and why extensions are required | https://nodejs.org/api/esm.html |

## Engineering essays worth the time

| Source | Takeaway | Link |
|---|---|---|
| Anthropic — Building Effective Agents | Workflow patterns vs. agents, and why most "agents" should be a chain. Language-agnostic but the tool-design advice is the spec for your Zod schemas | https://www.anthropic.com/engineering/building-effective-agents |
| MDN — Using Server-Sent Events | The readable companion to the WHATWG spec, with `EventSource` caveats (no custom headers, GET only — which is why everyone uses `fetch` instead) | https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events |

## How to read a spec (20 minutes, 3 passes)

1. **Pass 1 (3 min):** find the section that names your bug. Specs have excellent
   tables of contents and terrible introductions. Skip the introduction.
2. **Pass 2 (12 min):** read the algorithm steps literally, in order. Specs are
   written as imperative pseudocode. Your parser should be a transcription.
3. **Pass 3 (5 min):** hunt the edge cases — "if the field is absent", "ignore
   the line". That is where your bug is.

Keep one line of notes per spec section you consulted. The next time the same bug
appears, you will find your note before you find the section.
