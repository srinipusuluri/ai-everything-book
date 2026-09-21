# 🔗 Resources — Retrieval-Augmented Generation

## Start here

| Resource | Why | Link |
|---|---|---|
| **Pinecone Learning Center** | The best free running explainer on vector search, HNSW/IVF, hybrid search, and chunking — vendor-run but not vendor-biased in its explanations | https://www.pinecone.io/learn/ |
| **LlamaIndex — Building Production-Ready RAG Applications** | The most complete practitioner walkthrough of the failure modes this module covers, with working code | https://docs.llamaindex.ai/en/stable/optimizing/production_rag/ |
| **LangChain RAG conceptual guide** | Clear diagrams of the retrieve-then-generate pipeline and its variants (multi-query, parent-document, self-querying) | https://python.langchain.com/docs/concepts/rag/ |
| **Microsoft GraphRAG project page** | The reference implementation and accompanying explainer for GraphRAG, straight from the paper's authors | https://microsoft.github.io/graphrag/ |
| **MTEB Leaderboard** | Compare embedding models on real retrieval benchmarks before picking one — read this before, not after, choosing | https://huggingface.co/spaces/mteb/leaderboard |
| **DeepLearning.AI — Building and Evaluating Advanced RAG** (short course, free) | Hands-on notebook covering sentence-window and auto-merging retrieval plus RAGAS-style eval | https://www.deeplearning.ai/short-courses/building-evaluating-advanced-rag/ |

## Vector databases — pick on your actual constraints, not hype

| Database | What it's for | Link |
|---|---|---|
| **Chroma** | Embedded, zero-ops, the fastest path from "I have some text" to "I can query it" — great for prototyping and small-to-medium corpora | https://github.com/chroma-core/chroma |
| **Qdrant** | Production-grade, Rust-based, strong filtered-HNSW support (the filtering strategy actually matters — see notes/01 §4) | https://github.com/qdrant/qdrant |
| **Weaviate** | Production-grade, built-in hybrid search (BM25 + vector) out of the box, GraphQL API | https://github.com/weaviate/weaviate |
| **pgvector** | A Postgres extension — the right choice when you already run Postgres and don't want a new piece of infrastructure to operate | https://github.com/pgvector/pgvector |
| **Milvus** | Built for very large scale (billions of vectors), more operational overhead than the others | https://github.com/milvus-io/milvus |
| **FAISS** (Meta) | Not a database — a library of ANN index implementations (HNSW, IVF, IVF-PQ). What several of the databases above use under the hood | https://github.com/facebookresearch/faiss |

## Retrieval / RAG frameworks and libraries

| Repo | What's inside |
|---|---|
| https://github.com/run-llama/llama_index | The most RAG-specific of the major frameworks — chunking strategies, retrievers, rerankers, query engines all in one place |
| https://github.com/langchain-ai/langchain | Broader agent/chain framework with a full retrieval module; `langchain-community` has integrations for every vector DB above |
| https://github.com/UKPLab/sentence-transformers | Bi-encoder and cross-encoder models, including ready-to-use rerankers — the library behind most of `code/hybrid_search_and_rerank.py`'s real-world equivalent |
| https://github.com/stanford-futuredata/ColBERT | Reference implementation of late-interaction retrieval |
| https://github.com/explodinggradients/ragas | The reference RAGAS implementation — run it for real (LLM judge, not the offline proxy in this module's code) once you have API access |
| https://github.com/microsoft/graphrag | Microsoft's reference GraphRAG implementation, indexing pipeline included |
| https://github.com/xhluca/bm25s | A fast, dependency-light BM25 implementation in Python if you want a real one instead of the from-scratch version in this module |

Clone the starter set with: `bash ../_tools/clone_repos.sh 08-rag`

## Interactive tools

- **Vespa's ANN visualizer / blog series on HNSW** — concrete, implementation-level detail on the graph structure — https://blog.vespa.ai/
- **LangSmith / LangFuse** — tracing what a RAG pipeline actually retrieved and generated per request, essential once you're past a demo — https://www.langchain.com/langsmith · https://langfuse.com/
- **Tiktokenizer** — check how much of your context budget a retrieved chunk actually costs — https://tiktokenizer.vercel.app/

## Communities

- **r/LangChain** and **r/LocalLLaMA** (Reddit) — active, opinionated, and quick to call out RAG anti-patterns
- **LlamaIndex Discord** — https://discord.gg/dGcwcsnxhU
- **Qdrant Discord** — https://qdrant.to/discord
- **MTEB / Hugging Face forums** — for embedding-model-specific questions — https://discuss.huggingface.co/

## Datasets for building your own retrieval eval set

- **BEIR** (a heterogeneous IR benchmark — good source of realistic query/relevance-judgment triples) — https://github.com/beir-cellar/beir
- **MS MARCO** (large-scale passage ranking, the dataset most dense retrievers are benchmarked on) — https://microsoft.github.io/msmarco/
- **Natural Questions** (real Google search queries with Wikipedia-grounded answers) — https://ai.google.com/research/NaturalQuestions
