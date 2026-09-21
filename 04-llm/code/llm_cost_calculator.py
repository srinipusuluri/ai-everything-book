"""
LLM cost & capacity calculator — run this BEFORE you choose an architecture.

Answers the four questions that decide whether a feature is viable:
  1. What does one request cost?
  2. What does the feature cost per month at my traffic?
  3. What does prompt caching actually save me?
  4. How much GPU memory does self-hosting need, and how many users fit?

    python code/llm_cost_calculator.py

PRICES CHANGE. The table below is an illustrative TIER structure, not a quote.
Put your provider's current published prices in PRICES before trusting any number.

Requires: nothing but the standard library.
"""
from __future__ import annotations

from dataclasses import dataclass

# --------------------------------------------------------------------------- #
# Edit these. USD per 1,000,000 tokens.                                        #
# Illustrative tiers, NOT current vendor pricing -- always check the pricing page.
# --------------------------------------------------------------------------- #
PRICES: dict[str, dict[str, float]] = {
    "frontier-large":  {"in": 15.00, "out": 75.00, "cached_in": 1.50},
    "frontier-mid":    {"in":  3.00, "out": 15.00, "cached_in": 0.30},
    "small-fast":      {"in":  0.25, "out":  1.25, "cached_in": 0.03},
    "open-7b-hosted":  {"in":  0.10, "out":  0.30, "cached_in": 0.02},
}


def rule(t: str) -> None:
    print("\n" + "=" * 76 + f"\n{t}\n" + "=" * 76)


@dataclass
class Workload:
    name: str
    system_tokens: int          # stable prefix: system prompt + few-shot
    context_tokens: int         # retrieved chunks / documents / history
    user_tokens: int            # the actual user turn
    output_tokens: int
    turns: int = 1              # agent loops re-send a growing transcript
    requests_per_month: int = 100_000

    def tokens_per_request(self, cached: bool = False) -> tuple[int, int, int]:
        """Returns (fresh_input, cached_input, output) summed across turns."""
        fresh = cached_in = out = 0
        for t in range(self.turns):
            # Each turn re-sends everything before it: this is why agents are expensive.
            history = (self.user_tokens + self.output_tokens) * t
            if cached:
                cached_in += self.system_tokens
                fresh += self.context_tokens + self.user_tokens + history
            else:
                fresh += self.system_tokens + self.context_tokens + self.user_tokens + history
            out += self.output_tokens
        return fresh, cached_in, out


def cost(model: str, fresh: int, cached: int, out: int) -> float:
    p = PRICES[model]
    return (fresh * p["in"] + cached * p["cached_in"] + out * p["out"]) / 1e6


WORKLOADS = [
    Workload("Simple chat turn",        system_tokens=400,  context_tokens=0,
             user_tokens=80,   output_tokens=250,  turns=1, requests_per_month=1_000_000),
    Workload("RAG Q&A (20 chunks)",     system_tokens=800,  context_tokens=10_000,
             user_tokens=60,   output_tokens=400,  turns=1, requests_per_month=200_000),
    Workload("Doc summarisation (50p)", system_tokens=300,  context_tokens=40_000,
             user_tokens=40,   output_tokens=800,  turns=1, requests_per_month=20_000),
    Workload("Agent, 10 tool turns",    system_tokens=2_000, context_tokens=3_000,
             user_tokens=120,  output_tokens=300,  turns=10, requests_per_month=50_000),
]


def demo_per_request() -> None:
    rule("1. COST PER REQUEST, BY MODEL TIER")
    print(f"  {'workload':<26}{'model':<18}{'in':>9}{'out':>8}{'$/request':>12}{'$/1k req':>11}")
    for w in WORKLOADS:
        fresh, cached, out = w.tokens_per_request()
        for m in PRICES:
            c = cost(m, fresh, cached, out)
            print(f"  {w.name:<26}{m:<18}{fresh:>9,}{out:>8,}{c:>12.5f}{c*1000:>11.2f}")
        print()
    print("  Read the agent row: 10 turns of a growing transcript is ~10x a chat turn")
    print("  on input tokens alone. Agent cost grows roughly quadratically in turns.")


def demo_monthly() -> None:
    rule("2. MONTHLY BILL AT STATED TRAFFIC")
    print(f"  {'workload':<26}{'req/month':>12}" + "".join(f"{m:>18}" for m in PRICES))
    totals = dict.fromkeys(PRICES, 0.0)
    for w in WORKLOADS:
        fresh, cached, out = w.tokens_per_request()
        row = f"  {w.name:<26}{w.requests_per_month:>12,}"
        for m in PRICES:
            month = cost(m, fresh, cached, out) * w.requests_per_month
            totals[m] += month
            row += f"{'$' + format(month, ',.0f'):>18}"
        print(row)
    print(f"  {'TOTAL':<26}{'':>12}" + "".join(f"{'$' + format(totals[m], ',.0f'):>18}" for m in PRICES))
    print("\n  The spread between the top and bottom tier is roughly 100x.")
    print("  The single highest-leverage optimisation in most LLM products is")
    print("  ROUTING: send the easy 80% of traffic to a small model and escalate")
    print("  the rest. Measure quality per tier first -- see Module 15.")


def demo_caching() -> None:
    rule("3. WHAT PROMPT CACHING ACTUALLY SAVES")
    print(f"  {'workload':<26}{'model':<18}{'no cache':>12}{'cached':>12}{'saving':>10}")
    for w in WORKLOADS:
        f0, c0, o0 = w.tokens_per_request(cached=False)
        f1, c1, o1 = w.tokens_per_request(cached=True)
        for m in ("frontier-mid", "small-fast"):
            a, b = cost(m, f0, c0, o0), cost(m, f1, c1, o1)
            print(f"  {w.name:<26}{m:<18}{a:>12.5f}{b:>12.5f}{(1-b/a):>9.1%}")
    print("\n  Caching only pays when the prefix is LONG, STABLE and BYTE-IDENTICAL.")
    print("  Structure every prompt as:  [system + few-shot]  [retrieved context]  [user turn]")
    print("  Put a timestamp or a user name in the system prompt and you cache nothing.")


def demo_output_bias() -> None:
    rule("4. OUTPUT TOKENS ARE THE EXPENSIVE ONES")
    m = "frontier-mid"
    p = PRICES[m]
    print(f"  Using '{m}': input ${p['in']}/M, output ${p['out']}/M  "
          f"-> output costs {p['out']/p['in']:.0f}x more per token\n")
    print(f"  {'requested output':<24}{'tokens':>9}{'$/1k requests':>16}")
    for label, n in [("one-word answer", 5), ("a short paragraph", 120),
                     ("a full page", 700), ("'be thorough'", 2000),
                     ("reasoning + answer", 6000)]:
        c = cost(m, 2000, 0, n) * 1000
        print(f"  {label:<24}{n:>9,}{c:>16.2f}")
    print("\n  'Be concise' is a cost control, not a style preference.")
    print("  Reasoning models bill for thinking tokens you never see -- budget for them.")


def demo_self_host() -> None:
    rule("5. SELF-HOSTING: MEMORY AND CONCURRENCY")
    print("  weights_GB = params_B * bytes_per_param")
    print("  kv_GB      = 2 * layers * kv_heads * head_dim * seq * batch * bytes / 1e9\n")
    configs = [
        ("8B  GQA", 8, 32, 8, 128),
        ("70B GQA", 70, 80, 8, 128),
        ("405B GQA", 405, 126, 8, 128),
    ]
    print(f"  {'model':<10}{'precision':<11}{'weights':>10}{'KV @32k/seq':>14}{'fits 1x80GB?':>14}{'seats @32k':>12}")
    for name, pb, layers, kv, hd in configs:
        for prec, bpp in (("bf16", 2), ("int8", 1), ("4-bit", 0.5)):
            w = pb * bpp
            kv_gb = 2 * layers * kv * hd * 32768 * 1 * 2 / 1e9
            free = 80 - w - 6                      # 6 GB for activations/framework
            seats = max(0, int(free // kv_gb)) if free > 0 else 0
            fits = "yes" if w + 6 < 80 else "no"
            print(f"  {name:<10}{prec:<11}{w:>9.1f}G{kv_gb:>13.2f}G{fits:>14}{seats:>12}")
        print()
    print("  Note what caps you: a 70B at 4-bit fits in 80GB with room for only a")
    print("  handful of 32k-token sessions. KV CACHE -- not weights -- is the ceiling.")
    print("  This is why GQA, PagedAttention and quantized KV cache exist.")

    rule("6. BUILD vs BUY, THE ROUGH BREAK-EVEN")
    gpu_hour = 2.50          # illustrative on-demand H100-class rate
    util = 0.45              # realistic sustained utilisation, not peak
    tps = 2200               # output tokens/sec for a well-batched 8B-class server
    monthly_gpu = gpu_hour * 24 * 30
    monthly_tokens = tps * util * 3600 * 24 * 30
    self_host = monthly_gpu / (monthly_tokens / 1e6)
    print(f"  Assumptions: ${gpu_hour}/GPU-hour, {util:.0%} utilisation, {tps:,} out-tok/s")
    print(f"  -> self-hosted cost ~= ${self_host:.3f} per 1M output tokens")
    print(f"  -> hosted 'open-7b' tier is ${PRICES['open-7b-hosted']['out']:.2f} per 1M output tokens\n")
    print(f"  Break-even volume ~ {monthly_gpu / PRICES['open-7b-hosted']['out']:,.0f}M output tokens/month.")
    print("  Below that, hosting your own is more expensive AND more work.")
    print("  These assumptions are the whole ballgame -- especially utilisation.")
    print("  A GPU idling overnight is the most common reason self-hosting loses.")


if __name__ == "__main__":
    demo_per_request()
    demo_monthly()
    demo_caching()
    demo_output_bias()
    demo_self_host()
    print("\nEdit PRICES and WORKLOADS with YOUR numbers, then re-run.")
    print("Bring the output to the architecture review. It ends more arguments than opinions do.\n")
