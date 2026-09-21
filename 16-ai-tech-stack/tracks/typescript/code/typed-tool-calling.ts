/**
 * typed-tool-calling.ts -- schema-first tool definitions for an LLM, in TypeScript.
 *
 * Why this file exists
 * --------------------
 * A `type ToolArgs = { city: string }` is erased at runtime. The model has never
 * seen your tsconfig and does not care about it. The ONLY thing standing between
 * a hallucinated tool call and a 500 in production is a runtime validator.
 *
 * This script shows the full loop, offline (no network, no API key):
 *   1. Define tools once with Zod                -> one source of truth
 *   2. Derive static types with z.infer          -> compile-time safety
 *   3. Derive JSON Schema with z.toJSONSchema    -> what you actually send the model
 *   4. Validate every tool call the model makes  -> runtime safety
 *   5. Dispatch through a discriminated union    -> exhaustiveness checked by tsc
 *   6. Turn failures into tool_result(is_error)  -> let the model repair itself
 *
 * Run:  npx tsx typed-tool-calling.ts
 * Deps: zod (installed). zod-to-json-schema is optional -- section 3b degrades
 *       to an explanation if it is missing.
 */

import { z } from "zod";

const line = (s = "") => console.log(s);
const rule = (t: string) => line(`\n${"=".repeat(74)}\n${t}\n${"=".repeat(74)}`);

// --------------------------------------------------------------------------- //
// 1. One schema, three jobs: validation, static type, wire schema              //
// --------------------------------------------------------------------------- //

const WeatherInput = z.object({
  city: z.string().min(1).describe("City name, e.g. 'Lisbon'"),
  units: z.enum(["celsius", "fahrenheit"]).default("celsius")
    .describe("Temperature units to return"),
});

const SearchInput = z.object({
  query: z.string().min(1).describe("Free-text search over the internal docs"),
  top_k: z.number().int().min(1).max(20).default(5).describe("How many hits to return"),
});

const TicketInput = z.object({
  title: z.string().min(3).describe("One-line summary"),
  severity: z.enum(["low", "medium", "high"]).describe("Operational severity"),
  // .nullable() not .optional(): models are far better at emitting an explicit
  // null than at omitting a key they were told about.
  assignee: z.string().nullable().describe("Username, or null to leave unassigned"),
});

/**
 * defineTool exists purely for *inference*. Written inline, `input` would widen
 * to ZodType and `args` in run() would collapse to `unknown`. The generic
 * parameters pin the schema type so `args` is exactly z.infer<S>.
 */
type ToolDef<Name extends string, S extends z.ZodType> = {
  readonly name: Name;
  readonly description: string;
  readonly input: S;
  readonly run: (args: z.infer<S>) => Promise<string>;
};

function defineTool<Name extends string, S extends z.ZodType>(
  def: ToolDef<Name, S>,
): ToolDef<Name, S> {
  return def;
}

const weatherTool = defineTool({
  name: "get_weather",
  description: "Current conditions for a city. Use for 'what's the weather' questions.",
  input: WeatherInput,
  // `args` is typed { city: string; units: "celsius" | "fahrenheit" } -- hover it.
  run: async (args) => `18 degrees ${args.units} and overcast in ${args.city}`,
});

const searchTool = defineTool({
  name: "search_docs",
  description: "Keyword search over internal engineering documentation.",
  input: SearchInput,
  run: async (args) => `${args.top_k} hits for "${args.query}" (top: runbooks/oncall.md)`,
});

const ticketTool = defineTool({
  name: "create_ticket",
  description: "File an incident ticket. Only call this when the user explicitly asks.",
  input: TicketInput,
  run: async (args) =>
    `OPS-4417 created: "${args.title}" [${args.severity}] assignee=${args.assignee ?? "unassigned"}`,
});

// `as const` keeps the tuple's literal member types, which is what makes
// ToolName a union of string literals instead of plain `string`.
const TOOLS = [weatherTool, searchTool, ticketTool] as const;
type ToolName = (typeof TOOLS)[number]["name"]; // "get_weather" | "search_docs" | "create_ticket"

// --------------------------------------------------------------------------- //
// 2. Schema -> JSON Schema: the shape you put on the wire                      //
// --------------------------------------------------------------------------- //

/** The Anthropic Messages API tool shape (`tools: [...]` on messages.create). */
type WireTool = {
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
};

function toWireTool(t: ToolDef<string, z.ZodType>): WireTool {
  // io: "input" matters. A schema with .default() has a different INPUT type
  // (field optional) than OUTPUT type (field always present). The model is
  // producing input, so it must see the input view or you will tell it that an
  // optional field is required.
  const schema = z.toJSONSchema(t.input, { io: "input" }) as Record<string, unknown>;
  delete schema["$schema"]; // providers reject or ignore the meta key; drop it
  return { name: t.name, description: t.description, input_schema: schema };
}

// --------------------------------------------------------------------------- //
// 3. Result type -- errors as values, not exceptions                           //
// --------------------------------------------------------------------------- //

type Result<T, E> = { ok: true; value: T } | { ok: false; error: E };
const Ok = <T>(value: T): Result<T, never> => ({ ok: true, value });
const Err = <E>(error: E): Result<never, E> => ({ ok: false, error });

/** Every way a model-authored tool call can be wrong, as a closed union. */
type ToolError =
  | { kind: "unknown_tool"; name: string; known: readonly string[] }
  | { kind: "invalid_arguments"; name: ToolName; detail: string }
  | { kind: "tool_threw"; name: ToolName; detail: string };

/** A validated call. The union is what makes dispatch exhaustive. */
type ToolCall =
  | { tool: "get_weather"; args: z.infer<typeof WeatherInput> }
  | { tool: "search_docs"; args: z.infer<typeof SearchInput> }
  | { tool: "create_ticket"; args: z.infer<typeof TicketInput> };

/** What the SDK hands you inside a streamed/complete assistant message. */
type RawToolUse = { type: "tool_use"; id: string; name: string; input: unknown };

// --------------------------------------------------------------------------- //
// 4. The boundary: unknown -> ToolCall                                         //
// --------------------------------------------------------------------------- //

function parseToolCall(raw: RawToolUse): Result<ToolCall, ToolError> {
  // Note `input: unknown`, not `any`. `any` would let the next line compile
  // as `raw.input.city` and blow up at runtime. `unknown` forces the parse.
  const tool = TOOLS.find((t) => t.name === raw.name);
  if (!tool) {
    return Err({ kind: "unknown_tool", name: raw.name, known: TOOLS.map((t) => t.name) });
  }
  const parsed = tool.input.safeParse(raw.input);
  if (!parsed.success) {
    return Err({
      kind: "invalid_arguments",
      name: tool.name as ToolName,
      detail: z.prettifyError(parsed.error),
    });
  }
  // The cast is the one unavoidable seam: TS cannot prove that the name found
  // at runtime lines up with the schema in the same array element. Keep the
  // cast here, in one audited function, and nowhere else.
  return Ok({ tool: tool.name, args: parsed.data } as ToolCall);
}

// --------------------------------------------------------------------------- //
// 5. Exhaustive dispatch                                                       //
// --------------------------------------------------------------------------- //

/**
 * Add a fourth member to ToolCall without adding a case below and tsc fails
 * here with "Argument of type '{...}' is not assignable to parameter of type
 * 'never'". That compile error is the entire point of this function.
 */
function assertNever(x: never): never {
  throw new Error(`Unhandled variant: ${JSON.stringify(x)}`);
}

async function dispatch(call: ToolCall): Promise<Result<string, ToolError>> {
  try {
    switch (call.tool) {
      case "get_weather":
        return Ok(await weatherTool.run(call.args));
      case "search_docs":
        return Ok(await searchTool.run(call.args));
      case "create_ticket":
        return Ok(await ticketTool.run(call.args));
      default:
        return assertNever(call);
    }
  } catch (e) {
    // Never let a tool exception kill the agent loop. The model can often
    // recover from an error string; it cannot recover from a crashed process.
    return Err({
      kind: "tool_threw",
      name: call.tool,
      detail: e instanceof Error ? e.message : String(e),
    });
  }
}

/** The block you push back into `messages` for each call the model made. */
type ToolResultBlock = {
  type: "tool_result";
  tool_use_id: string;
  content: string;
  is_error?: true;
};

/** Errors go back to the model as tool_result blocks, not as thrown exceptions. */
function errorToToolResult(id: string, err: ToolError): ToolResultBlock {
  let content: string;
  switch (err.kind) {
    case "unknown_tool":
      content = `No tool named "${err.name}". Available tools: ${err.known.join(", ")}.`;
      break;
    case "invalid_arguments":
      content = `Arguments for "${err.name}" failed validation:\n${err.detail}\nFix them and call again.`;
      break;
    case "tool_threw":
      content = `Tool "${err.name}" failed: ${err.detail}`;
      break;
    default:
      return assertNever(err);
  }
  return { type: "tool_result", tool_use_id: id, content, is_error: true };
}

// --------------------------------------------------------------------------- //
// 6. A fake model. Deliberately badly behaved.                                 //
// --------------------------------------------------------------------------- //

function fakeModelTurn(): RawToolUse[] {
  return [
    // (a) correct
    { type: "tool_use", id: "tu_01", name: "get_weather", input: { city: "Lisbon", units: "celsius" } },
    // (b) correct, relying on a schema default the model omitted
    { type: "tool_use", id: "tu_02", name: "search_docs", input: { query: "oncall rotation" } },
    // (c) wrong type + missing required field -- the classic
    { type: "tool_use", id: "tu_03", name: "create_ticket", input: { title: "Pager storm", severity: "critical" } },
    // (d) a tool that does not exist. Models invent these under pressure.
    { type: "tool_use", id: "tu_04", name: "delete_production", input: { confirm: true } },
    // (e) numeric string. JSON round-trips lose types more often than you think.
    { type: "tool_use", id: "tu_05", name: "search_docs", input: { query: "slo", top_k: "5" } },
  ];
}

// --------------------------------------------------------------------------- //
// main                                                                         //
// --------------------------------------------------------------------------- //

async function main() {
  rule("1. What the model sees: Zod -> JSON Schema");
  line(JSON.stringify(toWireTool(ticketTool), null, 2));
  line(JSON.stringify(toWireTool(weatherTool), null, 2));
  line();
  line("Read the two schemas side by side:");
  line("  - `severity` became an enum, so the model cannot invent 'critical'.");
  line("  - `assignee` became type: [string, null] -- nullable, but still required.");
  line("  - `units` has a default, so under io:'input' it is NOT in `required`.");
  line("Everything here is derived. Nothing is typed twice, so nothing can drift.");

  rule("2. Gotcha: zod-to-json-schema vs Zod v4");
  try {
    const mod = await import("zod-to-json-schema");
    const legacy = mod.zodToJsonSchema(TicketInput as never, "TicketInput");
    line("zod-to-json-schema output for the SAME schema:");
    line(JSON.stringify(legacy, null, 2));
    line();
    line("Look at `definitions.TicketInput`. On Zod v4 it is EMPTY -- the library");
    line("reads v3 internals that no longer exist, finds nothing, and returns {}");
    line("with no error. An empty schema means the model is handed zero constraints");
    line("and will cheerfully invent fields. This bug is silent in dev and loud in prod.");
    line("Rule: on Zod v4 use the built-in z.toJSONSchema(). Keep zod-to-json-schema");
    line("only for codebases still pinned to Zod v3.");
  } catch {
    line("zod-to-json-schema is not installed -- skipping the demo.");
    line("The lesson stands: that package targets Zod v3 internals. Point it at a");
    line("Zod v4 schema and it silently returns an empty object instead of throwing.");
    line("Use z.toJSONSchema() on Zod v4.");
  }

  rule("3. Validating and dispatching one model turn");
  const results: ToolResultBlock[] = [];
  for (const raw of fakeModelTurn()) {
    const parsed = parseToolCall(raw);
    if (!parsed.ok) {
      const block = errorToToolResult(raw.id, parsed.error);
      line(`[${raw.id}] REJECTED (${parsed.error.kind})`);
      line(`         ${block.content.replace(/\n/g, "\n         ")}`);
      results.push(block);
      continue;
    }
    const out = await dispatch(parsed.value);
    if (out.ok) {
      line(`[${raw.id}] ok  ${parsed.value.tool} -> ${out.value}`);
      results.push({ type: "tool_result", tool_use_id: raw.id, content: out.value });
    } else {
      line(`[${raw.id}] tool failed: ${out.error.kind}`);
      results.push(errorToToolResult(raw.id, out.error));
    }
  }

  rule("4. What goes back to the model");
  line("All five tool_result blocks travel in ONE user message. Splitting them");
  line("across several messages teaches the model to stop calling tools in parallel.");
  line(`blocks=${results.length}, errors=${results.filter((r) => r.is_error).length}`);

  rule("5. Score card");
  line("- 3 of 5 calls from a 'well-behaved' model were malformed.");
  line("- Zero of them reached a tool body.");
  line("- Zero of them threw.");
  line("- The model got a specific, actionable repair message for each.");
  line("");
  line("That is the whole job. Types describe your intent; Zod enforces it.");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
