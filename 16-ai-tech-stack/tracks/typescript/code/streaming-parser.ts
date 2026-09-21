/**
 * streaming-parser.ts -- SSE framing, partial chunks, and cancellation, offline.
 *
 * Why this file exists
 * --------------------
 * Every AI product streams. Almost every hand-rolled stream reader has the same
 * two bugs, and both of them only show up under real network conditions:
 *
 *   BUG 1  You decode each byte chunk independently. A multi-byte UTF-8
 *          character split across a TCP segment becomes U+FFFD. Your users see
 *          a black diamond where an emoji or an accented letter should be.
 *   BUG 2  You split the chunk on "\n\n" and throw away the remainder. TCP has
 *          no idea what an SSE frame is; a frame boundary lands mid-chunk
 *          roughly always, and you silently drop tokens.
 *
 * Neither bug reproduces on localhost with short responses, which is why they
 * ship. This file reproduces both deterministically, then fixes them.
 *
 * Also covered: incremental JSON accumulation for streamed tool arguments,
 * AbortController cancellation, and mid-stream error events.
 *
 * Run:  npx tsx streaming-parser.ts
 * Deps: none (Node 18+ globals only). No network, no API key.
 */

const line = (s = "") => console.log(s);
const rule = (t: string) => line(`\n${"=".repeat(74)}\n${t}\n${"=".repeat(74)}`);
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

// --------------------------------------------------------------------------- //
// 1. The event union -- model this before you write the parser                 //
// --------------------------------------------------------------------------- //

/**
 * A trimmed version of the Anthropic Messages streaming protocol. The real one
 * has more members; the shape is identical. Note that this is a *discriminated*
 * union on `type`, which is what lets the renderer be exhaustiveness-checked.
 */
type StreamEvent =
  | { type: "message_start"; message: { id: string; model: string } }
  | { type: "content_block_start"; index: number; content_block: ContentBlockStart }
  | { type: "content_block_delta"; index: number; delta: Delta }
  | { type: "content_block_stop"; index: number }
  | { type: "message_delta"; delta: { stop_reason: string }; usage: { output_tokens: number } }
  | { type: "message_stop" }
  | { type: "error"; error: { type: string; message: string } };

type ContentBlockStart =
  | { type: "text"; text: string }
  | { type: "tool_use"; id: string; name: string; input: Record<string, never> };

type Delta =
  | { type: "text_delta"; text: string }
  | { type: "input_json_delta"; partial_json: string };

function assertNever(x: never): never {
  throw new Error(`Unhandled stream event: ${JSON.stringify(x)}`);
}

// --------------------------------------------------------------------------- //
// 2. A fake server: emits real SSE bytes at hostile chunk boundaries           //
// --------------------------------------------------------------------------- //

/** Serialize one event into the SSE wire format: `event:` + `data:` + blank line. */
function frame(e: StreamEvent): string {
  return `event: ${e.type}\ndata: ${JSON.stringify(e)}\n\n`;
}

function scriptedEvents(): StreamEvent[] {
  return [
    { type: "message_start", message: { id: "msg_01", model: "claude-opus-5" } },
    { type: "content_block_start", index: 0, content_block: { type: "text", text: "" } },
    { type: "content_block_delta", index: 0, delta: { type: "text_delta", text: "Deployment " } },
    { type: "content_block_delta", index: 0, delta: { type: "text_delta", text: "looks healthy" } },
    // A 4-byte astral character and a 2-byte accented character. These are the
    // ones that break naive decoding.
    { type: "content_block_delta", index: 0, delta: { type: "text_delta", text: " \u{1F680} in Sao Paulo (São)." } },
    { type: "content_block_stop", index: 0 },
    // A streamed tool call. Note the arguments arrive as JSON *fragments*:
    // JSON.parse on any prefix throws. You must buffer to the block stop.
    { type: "content_block_start", index: 1, content_block: { type: "tool_use", id: "tu_09", name: "create_ticket", input: {} } },
    { type: "content_block_delta", index: 1, delta: { type: "input_json_delta", partial_json: '{"title":"Latenc' } },
    { type: "content_block_delta", index: 1, delta: { type: "input_json_delta", partial_json: 'y spike","sever' } },
    { type: "content_block_delta", index: 1, delta: { type: "input_json_delta", partial_json: 'ity":"high","assignee":null}' } },
    { type: "content_block_stop", index: 1 },
    { type: "message_delta", delta: { stop_reason: "tool_use" }, usage: { output_tokens: 47 } },
    { type: "message_stop" },
  ];
}

/**
 * The transport. Produces Uint8Array chunks of a fixed byte size, so frames and
 * multi-byte characters get sliced apart exactly the way a real socket does it.
 * `chunkBytes = 7` is not a cheap trick -- it is a small-MTU simulator.
 */
async function* fakeSocket(
  events: StreamEvent[],
  opts: { chunkBytes?: number; delayMs?: number; signal?: AbortSignal } = {},
): AsyncGenerator<Uint8Array> {
  const { chunkBytes = 7, delayMs = 0, signal } = opts;
  const bytes = new TextEncoder().encode(events.map(frame).join(""));
  for (let i = 0; i < bytes.length; i += chunkBytes) {
    if (signal?.aborted) {
      // Real SDKs surface this as an AbortError from the fetch body. Model it.
      throw Object.assign(new Error("The operation was aborted."), { name: "AbortError" });
    }
    if (delayMs) await sleep(delayMs);
    yield bytes.slice(i, i + chunkBytes);
  }
}

// --------------------------------------------------------------------------- //
// 3. BUG 1 + BUG 2: the parser everyone writes first                           //
// --------------------------------------------------------------------------- //

async function* brokenParser(src: AsyncIterable<Uint8Array>): AsyncGenerator<StreamEvent> {
  for await (const chunk of src) {
    // Bug 1: a fresh decode per chunk, no streaming mode -> split code points
    //        are replaced with U+FFFD, permanently.
    const text = new TextDecoder().decode(chunk);
    // Bug 2: no buffer across chunks -> every frame that straddles a chunk
    //        boundary is discarded.
    for (const block of text.split("\n\n")) {
      const dataLine = block.split("\n").find((l) => l.startsWith("data: "));
      if (!dataLine) continue;
      try {
        yield JSON.parse(dataLine.slice(6)) as StreamEvent;
      } catch {
        // "Just swallow the parse error" is how this bug survives code review.
      }
    }
  }
}

// --------------------------------------------------------------------------- //
// 4. The correct parser                                                        //
// --------------------------------------------------------------------------- //

async function* sseParser(src: AsyncIterable<Uint8Array>): AsyncGenerator<StreamEvent> {
  // FIX 1: one decoder for the whole stream, in streaming mode. It holds
  // incomplete multi-byte sequences internally until the next chunk arrives.
  const decoder = new TextDecoder("utf-8");
  // FIX 2: a text buffer that survives across chunks.
  let buffer = "";

  for await (const chunk of src) {
    buffer += decoder.decode(chunk, { stream: true });

    // Emit only COMPLETE frames. Whatever is left is a prefix of the next one.
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const raw = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);

      // SSE allows multiple `data:` lines per event; they concatenate with \n.
      const data = raw
        .split("\n")
        .filter((l) => l.startsWith("data:"))
        .map((l) => l.slice(5).trimStart())
        .join("\n");
      if (!data || data === "[DONE]") continue; // [DONE] is an OpenAI-ism; harmless to ignore
      yield JSON.parse(data) as StreamEvent;
    }
  }

  // FIX 3: flush. decoder.decode() with no argument emits any trailing partial
  // sequence, and a server that closed without a final "\n\n" leaves one last
  // frame in the buffer. Forgetting this truncates the final token.
  buffer += decoder.decode();
  const tail = buffer.trim();
  if (tail) {
    const data = tail.split("\n").filter((l) => l.startsWith("data:")).map((l) => l.slice(5).trimStart()).join("\n");
    if (data) yield JSON.parse(data) as StreamEvent;
  }
}

// --------------------------------------------------------------------------- //
// 5. Consuming the events: accumulate text, accumulate tool JSON               //
// --------------------------------------------------------------------------- //

type Accumulated = {
  text: string;
  toolCalls: { id: string; name: string; input: unknown }[];
  stopReason: string | null;
  outputTokens: number;
};

async function consume(
  events: AsyncIterable<StreamEvent>,
  onToken?: (t: string) => void,
): Promise<Accumulated> {
  const acc: Accumulated = { text: "", toolCalls: [], stopReason: null, outputTokens: 0 };
  // Tool arguments stream as JSON fragments keyed by content-block index.
  const jsonBuffers = new Map<number, { id: string; name: string; json: string }>();

  for await (const ev of events) {
    switch (ev.type) {
      case "message_start":
        break;
      case "content_block_start":
        if (ev.content_block.type === "tool_use") {
          jsonBuffers.set(ev.index, { id: ev.content_block.id, name: ev.content_block.name, json: "" });
        }
        break;
      case "content_block_delta":
        switch (ev.delta.type) {
          case "text_delta":
            acc.text += ev.delta.text;
            onToken?.(ev.delta.text);
            break;
          case "input_json_delta": {
            const buf = jsonBuffers.get(ev.index);
            // NEVER JSON.parse here. '{"title":"Latenc' is not valid JSON.
            if (buf) buf.json += ev.delta.partial_json;
            break;
          }
          default:
            assertNever(ev.delta);
        }
        break;
      case "content_block_stop": {
        const buf = jsonBuffers.get(ev.index);
        if (buf) {
          // A model can stop mid-arguments (max_tokens, refusal, disconnect).
          // Parse defensively even though the happy path is valid JSON.
          try {
            acc.toolCalls.push({ id: buf.id, name: buf.name, input: JSON.parse(buf.json || "{}") });
          } catch {
            acc.toolCalls.push({ id: buf.id, name: buf.name, input: { __truncated: buf.json } });
          }
          jsonBuffers.delete(ev.index);
        }
        break;
      }
      case "message_delta":
        acc.stopReason = ev.delta.stop_reason;
        acc.outputTokens = ev.usage.output_tokens;
        break;
      case "message_stop":
        break;
      case "error":
        // The single most-skipped case. HTTP 200, headers already flushed, and
        // then an error frame arrives mid-body. If you do not handle it, the
        // stream just ends and the user sees a half-written sentence.
        throw new Error(`stream error [${ev.error.type}]: ${ev.error.message}`);
      default:
        assertNever(ev);
    }
  }
  return acc;
}

// --------------------------------------------------------------------------- //
// 6. Async iterator -> ReadableStream (what you return from a route handler)   //
// --------------------------------------------------------------------------- //

/**
 * This is the whole "edge streaming" story: convert your async iterator into a
 * ReadableStream and hand it to `new Response(stream, {...})`. It works
 * unchanged on Node, Bun, Deno, Cloudflare Workers and Vercel Edge.
 *
 * `pull` (rather than pushing everything in `start`) is what gives you
 * backpressure: the runtime calls pull only when the consumer has drained the
 * queue, so a slow browser throttles your generator instead of ballooning
 * server memory. `cancel` fires when the client navigates away -- that is where
 * you stop paying for tokens nobody will read.
 */
function toReadableStream(events: AsyncIterable<StreamEvent>): ReadableStream<Uint8Array> {
  const it = events[Symbol.asyncIterator]();
  const enc = new TextEncoder();
  return new ReadableStream<Uint8Array>({
    async pull(controller) {
      try {
        const { value, done } = await it.next();
        if (done) {
          controller.enqueue(enc.encode("event: done\ndata: [DONE]\n\n"));
          controller.close();
          return;
        }
        controller.enqueue(enc.encode(frame(value)));
      } catch (err) {
        controller.error(err);
      }
    },
    async cancel(reason) {
      // Client disconnected. Propagate so the upstream model call is aborted.
      await it.return?.(reason);
    },
  });
}

// --------------------------------------------------------------------------- //
// main                                                                         //
// --------------------------------------------------------------------------- //

async function main() {
  const events = scriptedEvents();
  const expectedText =
    "Deployment looks healthy \u{1F680} in Sao Paulo (São).";

  rule("1. BUG 1 in isolation: a fresh TextDecoder per chunk");
  {
    const raw = new TextEncoder().encode("S\u00E3o Paulo \u{1F680}");
    // Split inside the 2-byte 'a-tilde' and again inside the 4-byte rocket.
    const parts = [raw.slice(0, 2), raw.slice(2, 14), raw.slice(14)];
    const naive = parts.map((p) => new TextDecoder().decode(p)).join("");
    const streaming = (() => {
      const d = new TextDecoder("utf-8");
      return parts.map((p) => d.decode(p, { stream: true })).join("") + d.decode();
    })();
    line(`naive    : ${JSON.stringify(naive)}`);
    line(`streaming: ${JSON.stringify(streaming)}`);
    line("");
    line("Same bytes, same order. The only difference is { stream: true } plus one");
    line("decoder instance held across chunks. Every U+FFFD above is a permanent,");
    line("unrecoverable character loss that no downstream code can repair.");
  }

  rule("2. The broken parser (7-byte chunks, i.e. a bad network)");
  const bad = await consume(brokenParser(fakeSocket(events, { chunkBytes: 7 })));
  line(`text     : ${JSON.stringify(bad.text)}`);
  line(`toolCalls: ${bad.toolCalls.length}`);
  line(`stopReason: ${bad.stopReason}`);
  line("");
  line("Almost everything is gone. The parser only ever saw the handful of frames");
  line("that happened to fit inside a single chunk -- which, at 7 bytes, is none.");

  rule("3. The broken parser at 4096-byte chunks (i.e. localhost)");
  const bigChunk = await consume(brokenParser(fakeSocket(events, { chunkBytes: 4096 })));
  line(`text     : ${JSON.stringify(bigChunk.text)}`);
  line(`matches expected: ${bigChunk.text === expectedText}`);
  line("");
  line("This is the trap. One big chunk, everything lines up, all tests pass.");
  line("Then you deploy behind a CDN and the same code drops half the response.");

  rule("4. The correct parser, same hostile 7-byte chunks");
  let rendered = "";
  const good = await consume(sseParser(fakeSocket(events, { chunkBytes: 7 })), (t) => {
    rendered += t; // in a UI this is your setState / controller.enqueue
  });
  line(`text     : ${JSON.stringify(good.text)}`);
  line(`matches expected: ${good.text === expectedText}`);
  line(`no U+FFFD: ${!good.text.includes("�")}`);
  line(`progressive render == final: ${rendered === good.text}`);
  line(`stopReason=${good.stopReason} outputTokens=${good.outputTokens}`);
  line(`toolCalls: ${JSON.stringify(good.toolCalls)}`);
  line("");
  line("The tool arguments were reassembled from three JSON fragments, none of");
  line("which parses on its own. That is why you buffer to content_block_stop.");

  rule("5. Mid-stream error event");
  const withError: StreamEvent[] = [
    ...events.slice(0, 4),
    { type: "error", error: { type: "overloaded_error", message: "Upstream capacity exceeded" } },
  ];
  try {
    await consume(sseParser(fakeSocket(withError, { chunkBytes: 13 })));
    line("no error raised -- this line should be unreachable");
  } catch (e) {
    line(`caught: ${(e as Error).message}`);
    line("The HTTP status was 200 and the headers were flushed long ago, so you");
    line("cannot fail the response. Render the partial text you already have and");
    line("append a visible failure marker -- silence is the worst option.");
  }

  rule("6. AbortController: stop paying for tokens nobody will read");
  const ac = new AbortController();
  setTimeout(() => ac.abort(), 80);
  let partial = "";
  try {
    await consume(
      sseParser(fakeSocket(events, { chunkBytes: 16, delayMs: 2, signal: ac.signal })),
      (t) => { partial += t; },
    );
  } catch (e) {
    const err = e as Error;
    // An abort is a normal control-flow outcome, not a 500. Distinguish it.
    if (err.name === "AbortError") {
      line(`aborted after ${partial.length} characters: ${JSON.stringify(partial)}`);
      line("Keep the partial text, mark the turn as cancelled, and do NOT log an error.");
    } else {
      throw err;
    }
  }

  rule("7. Async iterator -> ReadableStream (the route-handler shape)");
  const stream = toReadableStream(sseParser(fakeSocket(events, { chunkBytes: 64 })));
  const reader = stream.getReader();
  let frames = 0;
  let bytes = 0;
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    frames += 1;
    bytes += value.byteLength;
  }
  line(`re-framed ${frames} SSE frames, ${bytes} bytes`);
  line("");
  line("In a Next.js / Hono / Workers handler this is the entire body:");
  line('  return new Response(stream, { headers: {');
  line('    "Content-Type": "text/event-stream",');
  line('    "Cache-Control": "no-cache, no-transform",');
  line('    "Connection": "keep-alive",');
  line('    "X-Accel-Buffering": "no",   // stops nginx buffering the whole body');
  line("  }});");
  line("Miss no-transform / X-Accel-Buffering and a proxy will happily buffer your");
  line("stream and deliver it all at once -- streaming code, non-streaming UX.");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
