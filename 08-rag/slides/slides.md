---
marp: true
theme: default
paginate: true
style: |
  section h1 { color: #EAB308; }
  section { font-size: 24px; }
---

# Retrieval-Augmented Generation

### Give a frozen model fresh, private, citable knowledge

**Module 08** · AI End-to-End Learning Track

---

## Why RAG exists

- An LLM's weights are a frozen, lossy snapshot of training data
- Problem 1: frozen knowledge -- it can't know last week's incident
- Problem 2: no provenance -- a fact with no way to verify it
- Problem 3: private data -- it was never trained on your wiki
- RAG's fix: retrieve fresh, citable, access-controlled text per query

<!-- speaker note: Most 'the AI is wrong' tickets are a chunker or retriever bug, not the LLM. Set that expectation early. -->

---

## RAG vs fine-tuning vs long-context -- pick on cost, not vibes

| Approach | Teaches the model | Best for |
|---|---|---|
| RAG | nothing -- stays frozen | fresh facts, citations, private data |
| Fine-tuning | a skill, tone, format | consistent style, jargon, structure |
| Long-context | nothing, same as RAG | small, static corpora only |


<!-- speaker note: They are complementary, not competing. Fine-tune the model to USE retrieved context well; use RAG to supply the facts. -->

---

## The pipeline: ingestion once, retrieval every query

- Ingestion: documents -> chunk -> embed -> vector index (offline)
- Serving: query -> embed -> retrieve top-k -> rerank -> generate
- Ingestion decisions become invisible bugs at serving time
- Most quality problems trace back to the chunker, not the model

<!-- speaker note: This is why chunking gets covered before embeddings or vector search -- it's the earliest decision and the hardest to undo. -->

---

## Four chunking strategies

| Strategy | Mechanism | Still has this problem |
|---|---|---|
| Fixed-size | text[i:i+size], nothing more | cuts words/facts in half blindly |
| Recursive | try nicest separator, fall back | one size for different sections |
| Sentence-window | unit=sentence; LLM gets neighbors | more units to embed/index |
| Structure-aware | split on headers, keep as metadata | only as good as doc structure |


<!-- speaker note: code/chunking_strategies.py plants a fact that straddles a fixed-size boundary and shows recursive and sentence-window both save it, by different mechanisms. -->

---

## Chunk-size sweep: reading the curve

- Margin falls steadily as chunk size grows: 0.46 to 0.05
- Bigger chunks dilute the embedding with more filler
- Whole-doc chunking: least precise AND most expensive per hit
- But shrinking a FIXED-size chunk just slices facts smaller
- Fix: boundary-respecting chunking at a moderate size

<!-- speaker note: Run code/chunking_strategies.py live here -- the printed table makes this argument better than any slide can. -->

---

## Embeddings for retrieval: three facts that matter

- Normalize vectors -> cosine similarity becomes a dot product
- Asymmetric search needs instruction prefixes: 'query:' vs 'passage:'
- Getting the prefix backwards degrades retrieval SILENTLY
- Dimensionality trades quality for index size and latency
- Check MTEB before committing to an embedding model

<!-- speaker note: Full embedding theory lives in Module 03. This slide is only the retrieval-specific gotchas -- the prefix bug is the most common real one. -->

---

## Exact search vs. ANN indexes

| Method | Mechanism | Trade-off |
|---|---|---|
| Exact kNN | compare against every vector | perfect recall, O(n) per query |
| HNSW | multi-layer navigable graph | read-optimized, big memory graph |
| IVF | k-means clusters, search nprobe | cheaper to build, needs good clusters |


<!-- speaker note: Every ANN knob (ef_search, M, nprobe, nlist) moves you along the recall/latency/memory triangle. Don't guess the values -- sweep them against a labeled eval set. -->

---

## Metadata filtering is an access-control boundary

- Post-filter: retrieve top-k, then discard non-matches
- Post-filter can return FEWER than k, or zero, results
- Pre-filter: restrict the ANN search before ranking
- Filtered HNSW: filter integrated into graph traversal itself
- For multi-tenant systems, wrong filtering is a data leak

<!-- speaker note: Ask any vector DB vendor whether their 'metadata filtering' is real filtered search or silent post-filtering. The answer changes your data-leak risk. -->

---

## Hybrid Search and Reranking

*Neither sparse nor dense wins alone*


<!-- speaker note: This is the section with real, measured numbers in code/hybrid_search_and_rerank.py -- run it live if time allows. -->

---

## BM25 vs. Dense: what each one wins

| Query type | Winner | Why |
|---|---|---|
| Exact codes, SKUs, IDs | BM25 (sparse) | the token IS the query |
| Paraphrase, no shared words | Dense (embeddings) | bridges the vocabulary gap |
| Both mixed in one corpus | Hybrid (RRF) | never the worst on either type |


<!-- speaker note: code/hybrid_search_and_rerank.py: BM25 gets MRR=1.0 on error-code queries where dense/LSA nearly zeroes out, and the reverse on paraphrased queries. -->

---

## Why Reciprocal Rank Fusion, not averaging scores

> **A BM25 score of 8.3 and a cosine of 0.31 are not comparable numbers.**

- RRF(doc) = sum over systems of 1 / (k + rank)
- Only looks at RANK, never at score -- no calibration needed
- k=60 (Cormack et al., 2009) controls how much rank-1 dominates
- Trivially extends to 3+ retrieval systems

<!-- speaker note: This is the single most reusable idea in the whole module -- rank fusion generalizes to combining any two uncalibrated scoring systems, not just BM25 and dense. -->

---

## Bi-encoder (retrieval) vs. cross-encoder (rerank)

|  | Bi-encoder | Cross-encoder |
|---|---|---|
| Encodes | query, doc separately | query and doc together |
| Precomputable | yes -- index once, offline | no -- runs per query |
| Scale | millions of documents | only a short shortlist |
| Accuracy | good | better -- sees interactions |


<!-- speaker note: Retrieve broadly and cheap, rerank narrowly and expensive. A reranker cannot recover a doc that never made the retrieval shortlist -- it sharpens, it does not substitute. -->

---

## Advanced retrieval patterns -- each fixes a NAMED problem

| Pattern | Fixes |
|---|---|
| Query rewriting | vague or underspecified queries |
| HyDE | query/document stylistic mismatch |
| Multi-query | one query phrasing missing the right doc |
| Parent-document / small-to-big | precision vs completeness trade-off |
| Self-querying | semantic ask + hard structured filter |
| Agentic / iterative RAG | multi-hop questions, single pass can't adapt |


<!-- speaker note: Add one of these because you profiled a specific failure, not because it sounds sophisticated. Each row has a paper behind it in papers/PAPERS.md. -->

---

## GraphRAG, conceptually

- Extract an entity/relationship graph from the corpus, offline
- Cluster the graph, have an LLM summarize each community
- At query time, answer GLOBAL questions from summaries
- Expensive offline indexing; win is concentrated on multi-hop
- For 'find the passage that answers this', plain RAG is cheaper

<!-- speaker note: Don't build a knowledge graph because it sounds advanced. Build one because real user questions are corpus-spanning multi-hop, and you measured that. -->

---

## Generation: citation assembly and abstention

- Tag every chunk with a stable ID before it hits the prompt
- Instruct the model to cite that ID for every claim
- Abstention: 'I don't know' when context is weak -- and TEST it
- Default failure: model answers anyway from parametric memory
- Put the best chunk first or last, never buried mid-context

<!-- speaker note: The abstention instruction is the single highest-leverage half-sentence in a RAG prompt, and the one everyone forgets to test adversarially. -->

---

## Retrieval eval metrics -- each has a blind spot

| Metric | Answers | Blind spot |
|---|---|---|
| Recall@k | did relevant docs reach top-k | ignores order entirely |
| MRR | how far to the FIRST hit | ignores everything after it |
| NDCG@k | order AND grade, through top-k | needs graded judgments |


<!-- speaker note: code/rag_eval_metrics.py hand-verifies every formula, then shows a case where recall@k and MRR rank two systems in OPPOSITE order -- report more than one metric. -->

---

## Faithfulness: did generation stick to the evidence

- RAGAS decomposes an answer into claims, checks each vs context
- code/rag_eval_metrics.py: a free, offline keyword-overlap proxy
- Ordering held on 3 answers: faithful 1.00, partial 0.67, none 0.00
- Known blind spots: negation, and true paraphrase, both miscored
- Use it as a cheap pre-filter before spending LLM-judge budget

<!-- speaker note: Say the caveat out loud: a well-paraphrased true claim can score UNSUPPORTED here. That's the trade for being free and instant. -->

---

## Production failure modes

| Failure | Root cause | Fix |
|---|---|---|
| Lost-in-the-middle | attention primacy/recency bias | best chunk first or last |
| Stale indexes | ingestion ran once, never refreshed | index = cache with a TTL |
| Chunk-boundary splits | naive chunking mid-sentence | boundary-respecting chunkers |
| Retrieval-gen mismatch | weak grounding instructions | explicit abstention + eval |
| Silent index drift | corpus shape changes unnoticed | monitor recall@k on a schedule |


<!-- speaker note: Every one of these is invisible in a 3-query demo and shows up only under real query volume and corpus churn. Build the eval harness before the incident, not after. -->

---

## Exit check

- Chunker with a stated boundary strategy, not fixed-size by default
- Hybrid retriever (BM25 + dense), fused with RRF, then reranked
- Recall@k / MRR / NDCG@k on a labeled query set you judged yourself
- A faithfulness score for generated answers, not just a vibe check
- Next: Module 15 -- AI Evals, for the full RAGAS + LLM-judge treatment

<!-- speaker note: The deliverable is the lab capstone: two retrieval configurations, compared on real numbers, plus a recommendation that cites those numbers. -->

---

## Now go build

`code/` run it · `lab/EXERCISES.md` break it · `papers/` go deeper
