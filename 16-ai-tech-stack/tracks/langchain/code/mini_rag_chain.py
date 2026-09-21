"""
mini_rag_chain.py -- a complete RAG pipeline in LCEL, fully offline.

RUNS WITH NO NETWORK AND NO API KEY. The embedding model is a hand-rolled hashing
vectoriser (`fakes.HashingEmbeddings`) and the chat model is a rule-based fake, so
retrieval is deterministic and you can see exactly which chunk won and why.

    /Users/srinip/ai-all/.venv/bin/python mini_rag_chain.py

Pipeline, which is the same six boxes in every RAG system you will ever build:

    load -> split -> embed -> store -> retrieve -> generate
    Document  Text     Embeddings  VectorStore  Retriever   ChatModel
              Splitter

Deep treatment of chunking strategy, hybrid search, reranking and RAG evaluation
lives in ../../../08-rag/ -- this file is about how the LangChain *interfaces* snap
together, not about how to make retrieval good.

Targets langchain-core 1.6.3 / langchain-text-splitters 1.1.2.
"""

from __future__ import annotations

from fakes import FakeChatModel, HashingEmbeddings, rule
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableParallel, RunnablePassthrough
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ---------------------------------------------------------------------------
# 1. LOAD. A document loader's only job is to produce Document objects.
# ---------------------------------------------------------------------------
# In real code this is PyPDFLoader / WebBaseLoader / S3DirectoryLoader / whatever,
# all of which live in langchain-community or a provider package. The interface they
# implement is tiny: `.load() -> list[Document]` and `.lazy_load() -> Iterator[...]`.
# Use lazy_load on anything bigger than your RAM.

RAW_DOCS = [
    Document(
        page_content=(
            "The runbook for the checkout service. Restart the pods with "
            "kubectl rollout restart deployment/checkout. Escalate to the payments "
            "on-call rota if the error rate stays above two percent for ten minutes. "
            "The connection pool size is configured in values.yaml and defaults to "
            "thirty connections per pod."
        ),
        metadata={"source": "runbook-checkout.md", "team": "payments", "year": 2026},
    ),
    Document(
        page_content=(
            "The runbook for the search service. Search is backed by an OpenSearch "
            "cluster with three data nodes. If query latency exceeds four hundred "
            "milliseconds, first check shard rebalancing, then check the index "
            "refresh interval. Never delete an index without a snapshot."
        ),
        metadata={"source": "runbook-search.md", "team": "discovery", "year": 2026},
    ),
    Document(
        page_content=(
            "Expense policy. Meals under forty dollars need no receipt. Flights over "
            "six hours may be booked in premium economy. All software purchases "
            "above five hundred dollars require a security review before the "
            "purchase order is raised."
        ),
        metadata={"source": "expense-policy.md", "team": "finance", "year": 2024},
    ),
]


def demo_1_split() -> list[Document]:
    rule("1. SPLIT -- chunking is the highest-leverage knob in the whole pipeline")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=180,
        chunk_overlap=40,
        # The recursive splitter tries these separators in order, falling back to the
        # next one only when a chunk is still too big. That ordering is the whole
        # idea: split on paragraphs if you can, characters only if you must.
        separators=["\n\n", "\n", ". ", " ", ""],
        add_start_index=True,
    )
    chunks = splitter.split_documents(RAW_DOCS)

    print(f"{len(RAW_DOCS)} documents -> {len(chunks)} chunks")
    for c in chunks:
        print(f"  [{c.metadata['source']:22s} @{c.metadata['start_index']:4d}] "
              f"{c.page_content[:58]}...")
    print("\n  split_documents PRESERVES metadata onto every child chunk. That is what")
    print("  makes citation possible later -- and metadata filtering, see demo 5.")
    print("  Too small and you lose the context that makes a passage make sense;")
    print("  too big and one irrelevant sentence drags the whole chunk into the top-k.")
    return chunks


def demo_2_embed_and_store(chunks: list[Document]) -> InMemoryVectorStore:
    rule("2. EMBED + STORE -- two interfaces, both four methods wide")

    embeddings = HashingEmbeddings(dim=256)
    probe = embeddings.embed_query("connection pool")
    nonzero = [(i, round(v, 3)) for i, v in enumerate(probe) if v]
    print(f"embed_query('connection pool') -> {len(probe)}-dim vector, "
          f"{len(nonzero)} non-zero buckets: {nonzero}")
    print("  (two tokens -> two buckets. A learned embedding is dense; this one is")
    print("   sparse, which is why unrelated chunks can score exactly 0.000 below.)")

    # InMemoryVectorStore ships in langchain-core. Chroma/FAISS/pgvector/Pinecone
    # implement the SAME `VectorStore` interface, so swapping is a one-line change
    # -- which is the strongest single argument for using LangChain at all.
    store = InMemoryVectorStore(embeddings)
    ids = store.add_documents(chunks)
    print(f"stored {len(ids)} chunks in an InMemoryVectorStore")

    print("\nraw similarity search for 'how many database connections per pod':")
    for doc, score in store.similarity_search_with_score(
        "how many database connections per pod", k=3
    ):
        print(f"  {score:.3f}  [{doc.metadata['source']:22s}] {doc.page_content[:50]}...")
    print("\n  Scores are cosine similarity here. They are NOT comparable across")
    print("  embedding models, and they are not probabilities. Do not put a hard")
    print("  threshold on them without measuring on your own data first.")
    return store


def format_docs(docs: list[Document]) -> str:
    """Render retrieved chunks into a prompt block with citation handles."""
    return "\n\n".join(
        f"[{i + 1}] (source: {d.metadata.get('source', '?')})\n{d.page_content}"
        for i, d in enumerate(docs)
    )


def build_rag_chain(store: InMemoryVectorStore):
    """prompt-with-context chain, assembled from Runnables."""
    retriever = store.as_retriever(search_kwargs={"k": 2})

    model = FakeChatModel(
        rules=[
            ("connection pool", "The pool defaults to thirty connections per pod, "
                                "configured in values.yaml [1]."),
            ("opensearch", "Search runs on a three-node OpenSearch cluster; check "
                           "shard rebalancing first [1]."),
            ("receipt", "Meals under forty dollars need no receipt [1]."),
        ],
        default="The retrieved context does not answer that question.",
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Answer ONLY from the context below. If the context does not contain "
                "the answer, say so. Cite sources as [n].\n\nContext:\n{context}",
            ),
            ("human", "{question}"),
        ]
    )

    # RunnableParallel fans the question out to the retriever AND passes it through
    # untouched. Without the passthrough the prompt would have no {question} to fill.
    # This shape -- {"context": retriever | format, "question": passthrough} -- is
    # THE canonical LCEL RAG chain. Memorise it.
    return (
        RunnableParallel(
            context=retriever | RunnableLambda(format_docs),
            question=RunnablePassthrough(),
        )
        | prompt
        | model
        | StrOutputParser()
    ), retriever


def demo_3_the_chain(store: InMemoryVectorStore) -> None:
    rule("3. RETRIEVE + GENERATE -- the canonical LCEL RAG chain")

    chain, retriever = build_rag_chain(store)

    for question in (
        "How big is the connection pool?",
        "What backs the search service?",
        "Do I need a receipt for a thirty dollar lunch?",
        "What is our parental leave policy?",
    ):
        print(f"\nQ: {question}")
        hits = retriever.invoke(question)
        print(f"   retrieved: {[h.metadata['source'] for h in hits]}")
        print(f"   A: {chain.invoke(question)}")

    print("\n  The last question is the one that matters, and it just failed on")
    print("  purpose. Nothing in the corpus mentions parental leave; the retriever")
    print("  returned its two nearest chunks anyway (a retriever ALWAYS returns k")
    print("  results, however bad they are); and the model answered with the")
    print("  connection-pool fact. That is a textbook grounded-looking hallucination.")
    print("  Fixes, in order of value: (1) a score threshold or a reranker so weak")
    print("  matches are dropped before the prompt is built, (2) a system prompt that")
    print("  makes abstention the default, (3) an eval that scores abstention as a")
    print("  correct answer. See ../../../08-rag/ and ../../../15-ai-evals/.")


def demo_4_returning_sources(store: InMemoryVectorStore) -> None:
    rule("4. Returning the answer AND its sources, without a second retrieval")

    chain, retriever = build_rag_chain(store)

    # Retrieve once, then branch: one branch answers, the other hands back the docs.
    # The naive version -- calling the retriever again to build the citation list --
    # doubles your vector-store traffic and can return different documents.
    with_sources = RunnableParallel(
        docs=retriever,
        question=RunnablePassthrough(),
    ) | RunnablePassthrough.assign(
        answer=(
            RunnableLambda(lambda d: {"context": format_docs(d["docs"]),
                                      "question": d["question"]})
            | chain.steps[1]   # the prompt
            | chain.steps[2]   # the model
            | chain.steps[3]   # the parser
        )
    )

    out = with_sources.invoke("How big is the connection pool?")
    print("answer :", out["answer"])
    print("sources:", [d.metadata["source"] for d in out["docs"]])
    print("\n  `RunnablePassthrough.assign` is doing the work: it adds `answer` while")
    print("  keeping `docs` and `question`. This is how you get citations that")
    print("  actually correspond to what the model saw.")


def demo_5_metadata_filtering(store: InMemoryVectorStore) -> None:
    rule("5. Filtering -- the cheapest accuracy win in RAG")

    payments_only = store.as_retriever(
        search_kwargs={"k": 2, "filter": lambda d: d.metadata.get("team") == "payments"}
    )
    question = "What should I check first?"
    print("unfiltered:", [d.metadata["source"] for d in
                          store.as_retriever(search_kwargs={"k": 2}).invoke(question)])
    print("team=payments:", [d.metadata["source"] for d in payments_only.invoke(question)])

    print("\n  InMemoryVectorStore takes a predicate; production stores take a")
    print("  backend-specific filter dict (pgvector -> SQL, Pinecone -> metadata")
    print("  filter DSL). The interface is portable, the filter syntax is NOT.")
    print("  Tenant isolation belongs in this filter -- never in the prompt.")


def demo_6_streaming_a_rag_chain(store: InMemoryVectorStore) -> None:
    rule("6. Streaming through a retriever")

    chain, _ = build_rag_chain(store)
    print("stream: ", end="", flush=True)
    for token in chain.stream("How big is the connection pool?"):
        print(token, end="", flush=True)
    print()
    print("\n  Retrieval blocks -- there is nothing to stream until the model starts.")
    print("  So your time-to-first-token includes the embed + search round trip.")
    print("  That is the number to optimise, and the reason people cache embeddings.")


if __name__ == "__main__":
    chunks = demo_1_split()
    store = demo_2_embed_and_store(chunks)
    demo_3_the_chain(store)
    demo_4_returning_sources(store)
    demo_5_metadata_filtering(store)
    demo_6_streaming_a_rag_chain(store)
    rule("Done")
    print("Retrieval quality itself -- chunking, hybrid search, reranking, eval --")
    print("is Module 08: ../../../08-rag/")
