# Running the examples

Both scripts are **offline**. There is no network call, no API key, and no model
provider. The model is simulated — deliberately badly, so you see the failure
modes you would otherwise only meet in production.

```bash
cd 16-ai-tech-stack/tracks/typescript/code
npm install          # zod, zod-to-json-schema, tsx, typescript, @types/node
npx tsx typed-tool-calling.ts
npx tsx streaming-parser.ts
```

Or via the scripts:

```bash
npm run typecheck    # tsc --noEmit under the strict-plus tsconfig
npm run tools        # typed-tool-calling.ts
npm run stream       # streaming-parser.ts
npm run all          # all three, in order
```

Verified on Node 24 with `zod@4`, `typescript@7`, `tsx@4`.
Node 20+ is enough — the only runtime globals used are `TextDecoder`,
`TextEncoder`, `ReadableStream` and `AbortController`, all of which have been
stable since Node 18.

## What each file is for

| File | Teaches |
|---|---|
| `typed-tool-calling.ts` | Zod as the single source of truth for a tool: static type, runtime validator, and JSON Schema all derived from one declaration. Then: rejecting a malformed tool call, an invented tool name, and a `"5"`-instead-of-`5` argument, all without throwing. Exhaustiveness checking via `assertNever`. |
| `streaming-parser.ts` | SSE framing over hostile chunk boundaries. Reproduces the split-UTF-8 bug and the dropped-frame bug, then fixes both. Incremental JSON accumulation for streamed tool arguments, mid-stream `error` events, `AbortController`, and converting an async iterator into a `ReadableStream` for a route handler. |

## `tsconfig.json`

The config is the lesson. `strict: true` is table stakes; the three flags that
change how you write code are `noUncheckedIndexedAccess`,
`exactOptionalPropertyTypes` and `verbatimModuleSyntax`. See
[`../notes/02-streaming-runtimes-and-hygiene.md`](../notes/02-streaming-runtimes-and-hygiene.md) §6.

## If `npm install` is blocked

`streaming-parser.ts` has **zero dependencies** — it will run under `npx tsx`
(or `node --experimental-strip-types streaming-parser.ts` on Node 22.6+) with
nothing installed. `typed-tool-calling.ts` needs `zod`; the
`zod-to-json-schema` section is wrapped in a dynamic `import()` and degrades to
a printed explanation if that package is absent.
