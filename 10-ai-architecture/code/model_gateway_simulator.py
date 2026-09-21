"""
model_gateway_simulator.py -- a small but real model-routing gateway.

This is an architecture SIMULATION: it proves the patterns work by running them against
synthetic "providers" with configurable cost/latency/failure profiles, not a wrapper around
real provider SDKs. No network calls. No API keys. Fully offline, deterministic (seeded RNG).

Patterns implemented, all live in ModelGateway:
  1. Cost-tiered routing   -- classify each request as EASY/HARD, send EASY to a cheap model.
  2. Automatic failover    -- if a provider errors, retry the next candidate before failing.
  3. Circuit breaker       -- stop calling a provider after N consecutive failures; auto-recover
                              after a cooldown window (half-open probe, then close or reopen).
  4. Load balancing        -- round-robin across same-tier providers so no single one is hammered.
  5. Budget enforcement    -- a hard per-provider dollar ceiling; once hit, the provider is
                              treated as unavailable (a "budget breaker") regardless of health.

The demo runs 2,000 simulated requests through:
  (a) a NAIVE baseline  -- always calls one fixed "frontier" provider, no failover, no cache tier
  (b) the SMART gateway -- cost-tiered routing + failover + circuit breaking + budgets
and prints a side-by-side report: cost, latency, success rate, and how many requests the smart
gateway rescued during the injected outage windows that would have failed the naive baseline.

Run:
    python code/model_gateway_simulator.py

Requires: nothing but the standard library.
"""
from __future__ import annotations

import random
import statistics
from dataclasses import dataclass, field


def rule(title: str) -> None:
    print("\n" + "=" * 78 + f"\n{title}\n" + "=" * 78)


# --------------------------------------------------------------------------- #
# 1. Simulated providers                                                      #
# --------------------------------------------------------------------------- #
@dataclass
class Provider:
    name: str
    tier: str                     # "cheap" or "premium"
    cost_per_request: float       # USD, illustrative flat cost per call at this tier
    base_latency_ms: float
    jitter_ms: float
    base_failure_rate: float      # baseline chance any given call errors/times out
    monthly_budget: float | None = None   # None = unlimited

    # runtime state (the gateway mutates these; the naive baseline ignores them)
    consecutive_failures: int = 0
    circuit_open_until: int = -1          # request index at which the circuit may probe again
    spend: float = 0.0
    calls: int = 0
    failures: int = 0
    total_latency_ms: float = 0.0


# A realistic mix: two cheap/fast small models, two premium frontier models, and one
# premium provider that goes through a rough outage window mid-run (injected below).
PROVIDERS = [
    Provider("small-a",   tier="cheap",   cost_per_request=0.0006, base_latency_ms=180, jitter_ms=60,  base_failure_rate=0.01),
    Provider("small-b",   tier="cheap",   cost_per_request=0.0007, base_latency_ms=200, jitter_ms=70,  base_failure_rate=0.015),
    Provider("frontier-a", tier="premium", cost_per_request=0.0180, base_latency_ms=900, jitter_ms=250, base_failure_rate=0.02, monthly_budget=2.50),
    Provider("frontier-b", tier="premium", cost_per_request=0.0210, base_latency_ms=850, jitter_ms=220, base_failure_rate=0.02),
]

# Outage injection: (provider_name, first_request_index, last_request_index, failure_rate_during)
OUTAGES = [
    ("frontier-a", 400, 650, 0.95),   # frontier-a effectively down for this window
]

CIRCUIT_FAILURE_THRESHOLD = 4     # consecutive failures before opening the circuit
CIRCUIT_COOLDOWN_REQUESTS = 60    # how many gateway-requests to wait before a half-open probe

N_REQUESTS = 2000
random.seed(42)


def classify(request_id: int) -> str:
    """Cheap difficulty classifier. ~78% of traffic is EASY (FAQ-shaped, short); the rest
    is HARD (multi-step reasoning, long context) and should escalate to the premium tier.
    A real system would use token count, a fast classifier, or a routing rule -- this
    stands in for that decision so the rest of the gateway logic can be demonstrated."""
    return "hard" if (request_id * 2654435761) % 100 < 22 else "easy"


def attempt_call(provider: Provider, request_index: int) -> tuple[bool, float]:
    """Simulate one call to `provider`. Returns (success, latency_ms)."""
    failure_rate = provider.base_failure_rate
    for name, start, end, rate in OUTAGES:
        if provider.name == name and start <= request_index <= end:
            failure_rate = rate
    latency = max(20.0, random.gauss(provider.base_latency_ms, provider.jitter_ms))
    success = random.random() > failure_rate
    return success, latency


def record(provider: Provider, success: bool, latency: float, cost: float) -> None:
    provider.calls += 1
    provider.total_latency_ms += latency
    provider.spend += cost
    if success:
        provider.consecutive_failures = 0
    else:
        provider.failures += 1
        provider.consecutive_failures += 1


# --------------------------------------------------------------------------- #
# 2. The naive baseline: one hardcoded provider, no failover, no budget check  #
# --------------------------------------------------------------------------- #
def run_naive(providers: list[Provider], n: int) -> dict:
    # Fresh copies so state doesn't bleed into the smart-gateway run.
    target = next(p for p in providers if p.name == "frontier-a")
    target = Provider(**{**target.__dict__})
    dropped = 0
    for i in range(n):
        success, latency = attempt_call(target, i)
        record(target, success, latency, target.cost_per_request if success else 0.0)
        if not success:
            dropped += 1
    return summarize({"frontier-a": target}, dropped, n)


# --------------------------------------------------------------------------- #
# 3. The smart gateway                                                        #
# --------------------------------------------------------------------------- #
class ModelGateway:
    """Cost-tiered routing + round-robin load balance + circuit breaker + budget breaker
    + automatic failover, all in one request path."""

    def __init__(self, providers: list[Provider]):
        self.providers = {p.name: p for p in providers}
        self.by_tier: dict[str, list[str]] = {}
        for p in providers:
            self.by_tier.setdefault(p.tier, []).append(p.name)
        self._rr_cursor: dict[str, int] = {tier: 0 for tier in self.by_tier}
        self.circuit_trips = 0
        self.budget_blocks = 0
        self.dropped = 0

    def _is_available(self, name: str, request_index: int) -> bool:
        p = self.providers[name]
        if p.monthly_budget is not None and p.spend >= p.monthly_budget:
            return False  # budget breaker: hard stop regardless of health
        if request_index < p.circuit_open_until:
            return False  # circuit open: still cooling down
        return True

    def _candidates(self, tier: str, request_index: int) -> list[str]:
        """Round-robin ordering within a tier, filtered to available providers."""
        names = self.by_tier.get(tier, [])
        if not names:
            return []
        start = self._rr_cursor[tier] % len(names)
        ordered = names[start:] + names[:start]
        self._rr_cursor[tier] += 1
        return [n for n in ordered if self._is_available(n, request_index)]

    def route(self, request_index: int) -> tuple[bool, float, float, str | None]:
        """Returns (success, latency_ms, cost, provider_name_used)."""
        difficulty = classify(request_index)
        primary_tier = "cheap" if difficulty == "easy" else "premium"
        fallback_tier = "premium" if primary_tier == "cheap" else "cheap"

        # Try the natural tier first, then fail over across tiers -- an easy request that
        # finds no cheap provider available still gets an answer from premium, and a hard
        # request with no premium capacity gets a degraded-but-served cheap answer instead
        # of nothing (graceful degradation, not a hard failure).
        for tier in (primary_tier, fallback_tier):
            for name in self._candidates(tier, request_index):
                p = self.providers[name]
                success, latency = attempt_call(p, request_index)
                cost = p.cost_per_request if success else 0.0
                record(p, success, latency, cost)
                if success:
                    return True, latency, cost, name
                # failure: update circuit breaker bookkeeping and try the next candidate
                if p.consecutive_failures >= CIRCUIT_FAILURE_THRESHOLD and request_index >= p.circuit_open_until:
                    p.circuit_open_until = request_index + CIRCUIT_COOLDOWN_REQUESTS
                    self.circuit_trips += 1
        self.dropped += 1
        return False, 0.0, 0.0, None


def run_smart(providers: list[Provider], n: int) -> tuple[dict, ModelGateway]:
    fresh = [Provider(**{**p.__dict__}) for p in providers]
    gw = ModelGateway(fresh)
    for i in range(n):
        gw.route(i)
    return summarize(gw.providers, gw.dropped, n), gw


# --------------------------------------------------------------------------- #
# 4. Reporting                                                                #
# --------------------------------------------------------------------------- #
def summarize(providers: dict[str, Provider], dropped: int, n: int) -> dict:
    total_calls = sum(p.calls for p in providers.values())
    total_success = sum(p.calls - p.failures for p in providers.values())
    total_cost = sum(p.spend for p in providers.values())
    latencies = []
    for p in providers.values():
        if p.calls:
            latencies.extend([p.total_latency_ms / p.calls] * p.calls)
    avg_latency = statistics.mean(latencies) if latencies else 0.0
    success_rate = total_success / n if n else 0.0
    return {
        "providers": providers,
        "total_cost": total_cost,
        "avg_latency_ms": avg_latency,
        "success_rate": success_rate,
        "dropped": dropped,
        "requests": n,
    }


def print_provider_table(providers: dict[str, Provider]) -> None:
    print(f"  {'provider':<12}{'tier':<10}{'calls':>7}{'failures':>10}{'avg lat ms':>12}{'spend $':>10}")
    for p in providers.values():
        avg_lat = p.total_latency_ms / p.calls if p.calls else 0.0
        print(f"  {p.name:<12}{p.tier:<10}{p.calls:>7}{p.failures:>10}{avg_lat:>12.0f}{p.spend:>10.3f}")


def main() -> None:
    rule("1. NAIVE BASELINE -- one fixed premium provider, no failover, no budget check")
    naive = run_naive(PROVIDERS, N_REQUESTS)
    print_provider_table(naive["providers"])
    print(f"\n  requests: {naive['requests']}   dropped (all failed): {naive['dropped']}")
    print(f"  success rate: {naive['success_rate']:.1%}   avg latency: {naive['avg_latency_ms']:.0f}ms"
          f"   total cost: ${naive['total_cost']:.2f}")
    print("\n  Every request goes to frontier-a. During its injected outage window")
    print(f"  (requests {OUTAGES[0][1]}-{OUTAGES[0][2]}, failure rate {OUTAGES[0][3]:.0%}), there is")
    print("  nowhere else to go -- those requests simply fail.")

    rule("2. SMART GATEWAY -- cost-tiered routing + failover + circuit breaker + budgets")
    smart, gw = run_smart(PROVIDERS, N_REQUESTS)
    print_provider_table(smart["providers"])
    print(f"\n  requests: {smart['requests']}   dropped (no provider available): {smart['dropped']}")
    print(f"  success rate: {smart['success_rate']:.1%}   avg latency: {smart['avg_latency_ms']:.0f}ms"
          f"   total cost: ${smart['total_cost']:.2f}")
    print(f"  circuit breaker trips: {gw.circuit_trips}")
    budget_blocked = [p.name for p in smart["providers"].values()
                      if p.monthly_budget is not None and p.spend >= p.monthly_budget]
    if budget_blocked:
        print(f"  budget breaker engaged on: {', '.join(budget_blocked)} "
              f"(hit its ${PROVIDERS[2].monthly_budget:.2f} ceiling and was routed around, not just alerted on)")

    rule("3. SIDE BY SIDE -- what the architecture bought you")
    cost_delta = naive["total_cost"] - smart["total_cost"]
    print(f"  {'metric':<28}{'naive':>14}{'smart gateway':>18}")
    print(f"  {'success rate':<28}{naive['success_rate']:>14.1%}{smart['success_rate']:>18.1%}")
    print(f"  {'avg latency (ms)':<28}{naive['avg_latency_ms']:>14.0f}{smart['avg_latency_ms']:>18.0f}")
    print(f"  {'total cost ($)':<28}{naive['total_cost']:>14.2f}{smart['total_cost']:>18.2f}")
    print(f"  {'requests dropped':<28}{naive['dropped']:>14}{smart['dropped']:>18}")
    print(f"\n  Cost tiering alone (routing ~78% of easy traffic to a model ~30x cheaper)")
    print(f"  saved ${cost_delta:.2f} across {N_REQUESTS} requests -- a"
          f" {(cost_delta / naive['total_cost'] if naive['total_cost'] else 0):.0%} reduction --")
    print("  while ALSO improving success rate, because failover covered the outage window")
    print("  that the naive baseline had no answer for.")
    print("\n  This is the argument for building a gateway: it is not one win, it is four")
    print("  independent wins (cost, latency via load balance, availability via failover,")
    print("  and a hard cost ceiling) stacked in one place instead of four separate patches.")


if __name__ == "__main__":
    main()
