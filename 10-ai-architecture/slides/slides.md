---
marp: true
theme: default
paginate: true
style: |
  section h1 { color: #F97316; }
  section { font-size: 24px; }
---

# AI Architecture

### Combining Modules 01-09 into a production system

**Module 10** · AI End-to-End Learning Track

---

## Architecture is a separate skill from model literacy

- Knowing how a transformer works does not tell you where the cache goes
- This module assumes 01-09 and asks: how do these pieces become ONE system
- Every layer boundary is a place bugs hide and costs leak
- The goal: a system a new engineer can reason about from the diagram alone

---

## The layered reference architecture

- Client -> API Gateway/BFF -> Orchestration -> Model layer <-> Tool/Retrieval -> Data
- Observability is NOT a box -- it is horizontal, touching every layer from day one
- The gateway is the FIRST prompt-injection surface (Module 13)
- The orchestration layer owns planning, checkpointing, human-in-the-loop, retries

<!-- speaker note: Draw this diagram on a whiteboard from notes/01 section 2. Spend real time here -- everything else in the deck hangs off it. -->

---

## What leaks when a layer is done badly

| Layer skipped/weak | What leaks |
|---|---|
| No gateway validation | prompt injection reaches the model layer raw |
| No orchestration idempotency | a retried agent step fires a side effect twice |
| No model-layer routing | every request pays frontier prices |
| No data-layer freshness | RAG answers from a stale index, confidently |
| No observability from day one | the first incident is also the first time you look |


---

## The model gateway: four wins in one place

- Cost-tiered routing: easy requests to a cheap model (Module 04's cost lesson, operationalized)
- Automatic failover across providers when one is down
- Circuit breaker: stop calling a failing provider, auto-recover after cooldown
- A hard budget ceiling that no code path can bypass
- code/model_gateway_simulator.py measures all four against a naive single-provider baseline

<!-- speaker note: Run the simulator live: cost-tiering alone typically shows 60-70% cost reduction while ALSO improving success rate during a simulated outage. -->

---

## Build vs. buy for the gateway

| Option | Choose it when |
|---|---|
| LiteLLM (open source) | you want control and no vendor lock-in |
| Hosted gateway (Portkey, OpenRouter) | you want it running today, ops isn't your job |
| Hand-rolled | your routing logic is genuinely unique to your business |


---

## Caching is not one thing

> **Exact-match cache, semantic cache, prompt/prefix cache, and embedding cache solve different problems.**

- Semantic cache: a real latency/cost win on true paraphrases
- ...and a real CORRECTNESS RISK on near-duplicates that differ in a load-bearing detail
- 'refund policy under $50' vs 'under $500' can collide at the wrong threshold

<!-- speaker note: code/semantic_cache_correctness.py demonstrates the wrong-answer case numerically, then fixes it with an entity/number guard. -->

---

## The semantic cache fix

- Tightening the similarity threshold alone trades hit rate for safety
- Better: add an entity/number guard -- block a hit when queries differ
-   in a number or named entity, regardless of embedding similarity
- Ship a semantic cache only where you've measured BOTH sides for YOUR query distribution

---

## Data architecture: the RAG freshness problem

- Ingestion pipeline: crawl/sync -> clean -> chunk -> embed -> index
- The hard part isn't building it once -- it's keeping the index FRESH
- A stale index gives confidently wrong answers, indistinguishable from a fresh one
- Vector DB selection: managed vs self-hosted, hybrid search support, metadata filtering, scale

---

## Scalability and reliability patterns

- Async/queue-based processing for long-running agent tasks -- don't block a web request
- Idempotency keys for retries -- see LangGraph's re-execution trap (Module 16)
- Circuit breakers and graceful degradation when a provider is down
- Multi-region/multi-provider redundancy for anything customer-facing
- Streaming architecture (SSE/WebSocket) at the API layer for perceived latency

---

## A prompt change IS a deploy

> **Treat it like one: review, version, canary, rollback path.**

- Blue-green and canary deploys apply to prompts and models, not just code
- Shadow deployment: test a new model against production traffic without serving it
- The model/prompt registry pattern gives you versioning AND rollback

<!-- speaker note: This is the bridge to Module 12's governance requirement for auditability and Module 16's LangSmith prompt versioning. -->

---

## Security controls: where they actually live

- Input validation and delimiting -- at the GATEWAY, before orchestration sees it
- Privilege separation for tool access -- in the ORCHESTRATION layer
- Output filtering/guardrails -- before the response leaves the model layer
- Human approval gates -- in orchestration, for consequential actions
- No single layer is sufficient. This is Module 13's theory, placed on a diagram

---

## Observability: instrument before launch

- Traces, structured logs, metrics, and cost meters are ONE architecture concern
- Not four tools bolted on after the first incident
- Decide what to log BEFORE launch: prompt hash, model version, tokens, latency, cost
- See Module 16's LangSmith track for the concrete implementation

---

## Cost architecture: from model to decision

- The cost model from Module 04 becomes an architecture decision:
-   WHERE you put a router, WHERE you cache, WHERE you set a budget circuit breaker
- A cost target is a design constraint, not a monthly surprise
- Work backward from a target cost-per-request to the architecture that hits it

---

## The capstone architecture

- One complete, labeled diagram: an enterprise RAG + agent assistant with tool access
- Every point above -- gateway, cache, orchestration, security, observability -- in one place
- notes/02 section 6 has the full diagram and component-by-component rationale
- Use this as the template when you draw your own system in the lab

<!-- speaker note: This is the slide to leave up while people do lab exercise 1 -- drawing their own architecture. -->

---

## Exit check

- Draw the full layered architecture for a real system you know
- Run code/model_gateway_simulator.py and explain the four separate wins it produces
- Break your own semantic cache, then fix it with an entity/number guard
- Trace a prompt-injection attempt through your diagram and name what catches it
- Next: Module 11 -- The LLM Model Landscape

---

## Now go build

`code/` run it · `lab/EXERCISES.md` break it · `papers/` go deeper
