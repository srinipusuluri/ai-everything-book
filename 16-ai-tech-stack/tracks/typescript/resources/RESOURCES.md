# 🔗 Resources — TypeScript for AI Applications

## Learn the type system properly

| Resource | Who it is for | Link |
|---|---|---|
| **TypeScript Handbook** | The official tour. Skip to "Narrowing" and "Type Manipulation" if you already write TS daily | https://www.typescriptlang.org/docs/handbook/intro.html |
| **Total TypeScript** (Matt Pocock) | Free core-volume tutorials plus the best short-form TS content anywhere. The "Type Transformations" workshop is the fastest route to fluency with generics | https://www.totaltypescript.com/ |
| **type-challenges** | 150+ type-level puzzles, graded. Do the easy and medium tiers; skip "extreme" unless you enjoy suffering | https://github.com/type-challenges/type-challenges |
| **TypeScript Deep Dive** (Basarat) | Free book; still the clearest explanation of structural typing and declaration files | https://basarat.gitbook.io/typescript/ |
| **ts-reset** | A "CSS reset" for TypeScript's less defensible built-in types (`JSON.parse` returning `any`, `.filter(Boolean)`) | https://github.com/mattpocock/ts-reset |

## The AI SDK layer

| Repo / doc | What is inside | Link |
|---|---|---|
| **Vercel AI SDK** | `ai` + `@ai-sdk/*` providers. Read `examples/` in the repo before the docs — they are more current | https://github.com/vercel/ai |
| AI SDK documentation | `streamText`, `generateObject`, tool calling, agent loops, UI hooks | https://ai-sdk.dev/docs |
| **Anthropic TypeScript SDK** | Official client. `src/lib/MessageStream.ts` is worth reading line by line | https://github.com/anthropics/anthropic-sdk-typescript |
| Claude Agent SDK docs | Agent harness with built-in tools, subagents, hooks, permissions | https://code.claude.com/docs/en/agent-sdk |
| **MCP TypeScript SDK** | Server and client for Model Context Protocol; takes Zod schemas for tool definitions directly | https://github.com/modelcontextprotocol/typescript-sdk |
| **ai-chatbot** (Vercel) | A complete, production-shaped Next.js chat app: streaming, tools, auth, persistence | https://github.com/vercel/ai-chatbot |

## Validation & error handling

| Resource | Why | Link |
|---|---|---|
| **Zod** | The default. Read the docs on `safeParse`, `discriminatedUnion`, and JSON Schema | https://zod.dev/ |
| **Valibot** | Zod's API with a much smaller bundle, via modular imports. Worth it when bundle size is a real constraint (edge, browser) | https://valibot.dev/ |
| **ArkType** | Parses TypeScript-syntax type strings at runtime; the fastest of the three. Younger ecosystem | https://arktype.io/ |
| **Standard Schema** | The shared interface Zod/Valibot/ArkType all implement, so libraries can accept any of them | https://github.com/standard-schema/standard-schema |
| **neverthrow** | Minimal `Result<T, E>` with combinators, if the 1-line type alias stops being enough | https://github.com/supermacro/neverthrow |
| **Effect** | A full effect system: typed errors, dependency injection, structured concurrency, retries. Powerful and a large commitment — adopt deliberately, not incidentally | https://effect.website/ |

## Runtimes & deployment

| Resource | Why | Link |
|---|---|---|
| Cloudflare Workers docs | The reference edge runtime. Read the Node.js-compat and Limits pages before you port anything | https://developers.cloudflare.com/workers/ |
| Vercel Functions docs | Node vs Edge runtime, streaming, duration limits | https://vercel.com/docs/functions |
| Bun docs | Runtime, bundler, test runner, package manager in one binary | https://bun.sh/docs |
| Deno docs | Permissions model, web-standard APIs, npm compatibility | https://docs.deno.com/ |
| **Hono** | Tiny web framework that runs unmodified on Node, Bun, Deno, Workers and Vercel Edge. The pragmatic choice for an AI backend that must be portable | https://hono.dev/ |
| **Nitro / h3** | The other portable-server answer; powers Nuxt | https://nitro.build/ |

## Toolchain

| Tool | Link |
|---|---|
| pnpm — strict, fast, content-addressed package manager | https://pnpm.io/ |
| Vitest — the test runner to use with TypeScript in 2026 | https://vitest.dev/ |
| Biome — eslint + prettier replacement, one Rust binary | https://biomejs.dev/ |
| typescript-eslint — if you need rules Biome does not have | https://typescript-eslint.io/ |
| tsx — run a `.ts` file directly. Remember: it does **not** typecheck | https://github.com/privatenumber/tsx |
| tsup — bundle a TS library without a webpack config | https://tsup.egoist.dev/ |
| Changesets — versioning and changelogs for monorepos | https://github.com/changesets/changesets |

## Observability for AI apps

| Tool | Why | Link |
|---|---|---|
| **OpenTelemetry JS** | Vendor-neutral tracing. The AI SDK emits OTel spans for model calls | https://opentelemetry.io/docs/languages/js/ |
| **Langfuse** | Open-source LLM tracing with a solid TS SDK; self-hostable | https://langfuse.com/ |
| **LangSmith** | See the sibling track [../langsmith/](../../langsmith/) | https://docs.smith.langchain.com/ |

## Communities & keeping current

- TypeScript release notes — the only reliable way to hear about new flags:
  https://devblogs.microsoft.com/typescript/
- Matt Pocock's newsletter/videos — short, high signal: https://www.totaltypescript.com/
- r/typescript — https://www.reddit.com/r/typescript/
- Anthropic engineering blog — https://www.anthropic.com/engineering
- AI SDK changelog — the API moved a lot in v5; read it before upgrading:
  https://github.com/vercel/ai/releases

## Sibling tracks

- [../python/](../../python/) — the other half of the wire
- [../claude-code/](../../claude-code/) — the Claude Agent SDK in anger
- [../langchain/](../../langchain/) and [../langgraph/](../../langgraph/) — both have
  TypeScript ports; note 02 §5 is the context for deciding whether you want one
