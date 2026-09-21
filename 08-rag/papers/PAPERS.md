# 📄 Papers — Retrieval-Augmented Generation

`bash ../_tools/fetch_papers.sh 08-rag` downloads these into this folder.

## Read #1 twice. It named the whole field.

| # | Paper | Year | Why | Link |
|---|---|---|---|---|
| 1 | **Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks** — Lewis et al. (Meta AI) | 2020 | The paper that coined "RAG": a generator conditioned on retrieved passages, trained end-to-end. Nearly every production RAG system is a much simpler, non-differentiable descendant of this idea | [arXiv:2005.11401](https://arxiv.org/abs/2005.11401) |

## Dense retrieval and the retriever/reranker split

| Paper | Takeaway | Link |
|---|---|---|
| Dense Passage Retrieval (DPR) — Karpukhin et al., 2020 | Two BERT encoders (query, passage) trained contrastively beat BM25 on open-domain QA — the paper that made dense retrieval credible | [arXiv:2004.04906](https://arxiv.org/abs/2004.04906) |
| REALM: Retrieval-Augmented Language Model Pre-Training — Guu et al., 2020 | Retrieval integrated into pretraining itself, not bolted on afterward | [arXiv:2002.08909](https://arxiv.org/abs/2002.08909) |
| Leveraging Passage Retrieval with Generative Models (Fusion-in-Decoder) — Izacard & Grave, 2020 | Encode each retrieved passage separately, fuse in the decoder — scales gracefully to many retrieved passages | [arXiv:2007.01282](https://arxiv.org/abs/2007.01282) |
| ColBERT: Efficient and Effective Passage Search via Late Interaction — Khattab & Zaharia, 2020 | Token-level late interaction instead of one pooled vector — a middle ground between bi-encoder speed and cross-encoder accuracy | [arXiv:2004.12832](https://arxiv.org/abs/2004.12832) |
| ColBERTv2 — Santhanam et al., 2022 | Compression + distillation that makes late interaction practical at production scale | [arXiv:2112.01488](https://arxiv.org/abs/2112.01488) |
| Reciprocal Rank Fusion outperforms Condorcet and Individual Rank Learning Methods — Cormack, Clarke & Buettcher, 2009 | The RRF paper implemented in `code/hybrid_search_and_rerank.py` — rank-only fusion, no score calibration needed | [PDF (Waterloo)](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf) |

## Query enhancement and iterative retrieval

| Paper | Takeaway | Link |
|---|---|---|
| Precise Zero-Shot Dense Retrieval without Relevance Labels (HyDE) — Gao et al., 2022 | Embed a hypothetical LLM-generated answer instead of the raw query — closes the query/document stylistic gap | [arXiv:2212.10496](https://arxiv.org/abs/2212.10496) |
| Query Rewriting for Retrieval-Augmented Large Language Models — Ma et al., 2023 | Trains a small rewriter model specifically to help downstream retrieval, rather than hand-tuning prompts | [arXiv:2305.14283](https://arxiv.org/abs/2305.14283) |
| Interleaving Retrieval with Chain-of-Thought Reasoning (IRCoT) — Trivedi et al., 2022 | Retrieve, reason a step, retrieve again — the paper behind the "agentic/iterative RAG" pattern for multi-hop questions | [arXiv:2212.10509](https://arxiv.org/abs/2212.10509) |
| Active Retrieval Augmented Generation (FLARE) — Jiang et al., 2023 | Decide *when* to retrieve mid-generation by watching the model's own confidence, instead of retrieving once upfront | [arXiv:2305.06983](https://arxiv.org/abs/2305.06983) |
| Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection — Asai et al., 2023 | Trains the model to emit special tokens deciding whether to retrieve and whether its own output is well-supported | [arXiv:2310.11511](https://arxiv.org/abs/2310.11511) |

## Structured and graph-based retrieval

| Paper | Takeaway | Link |
|---|---|---|
| From Local to Global: A Graph RAG Approach to Query-Focused Summarization (GraphRAG) — Edge et al. (Microsoft Research), 2024 | Extract an entity graph, summarize it hierarchically, and answer global/multi-hop questions from community summaries instead of raw chunks | [arXiv:2404.16130](https://arxiv.org/abs/2404.16130) |

## Context behavior and evaluation

| Paper | Takeaway | Link |
|---|---|---|
| Lost in the Middle: How Language Models Use Long Contexts — Liu et al., 2023 | Retrieval accuracy degrades measurably for facts placed in the middle of a long context, even when the model can technically "see" them — the paper behind the production failure mode in `notes/02` | [arXiv:2307.03172](https://arxiv.org/abs/2307.03172) |
| RAGAS: Automated Evaluation of Retrieval Augmented Generation — Es et al., 2023 | Reference-free faithfulness, answer relevance, and context precision/recall metrics computed with an LLM judge — the paper `code/rag_eval_metrics.py`'s faithfulness check is a cheap offline proxy for | [arXiv:2309.15217](https://arxiv.org/abs/2309.15217) |

## Foundational IR (pre-dates deep learning, still the vocabulary everyone uses)

| Paper | Takeaway | Link |
|---|---|---|
| The Probabilistic Relevance Framework: BM25 and Beyond — Robertson & Zaragoza, 2009 | The definitive BM25 reference; read this before trusting any BM25 implementation, including the one in this module | [Foundations & Trends in IR (PDF)](https://www.staff.city.ac.uk/~sbrp622/papers/foundations_bm25_review.pdf) |
| Cumulated Gain-Based Evaluation of IR Techniques — Järvelin & Kekäläinen, 2002 | The original NDCG paper — read it once so `code/rag_eval_metrics.py`'s formula stops looking arbitrary | [ACM DL](https://dl.acm.org/doi/10.1145/582415.582418) |

## The best explainers

- **Pinecone's Learning Center** (vector search, HNSW, hybrid search, chunking) — https://www.pinecone.io/learn/
- **LlamaIndex — Building Production-Ready RAG Applications** — https://docs.llamaindex.ai/en/stable/optimizing/production_rag/
- **LangChain — RAG conceptual guide** — https://python.langchain.com/docs/concepts/rag/
- **Microsoft Research GraphRAG project page** (with the accompanying blog explainer) — https://microsoft.github.io/graphrag/
