# Learn AI, end to end.

Sixteen modules, in the order the field actually builds on itself — from the math under a linear
model to shipping a governed, evaluated agent in production. Every module has notes, runnable code,
a lab, primary sources, and a slide deck.

**16** core modules · **7** tech-stack tracks · **50+** runnable scripts · **30+** slide decks · **0** API keys required

📖 Prefer a book? The whole track is also compiled into one print-ready PDF:
[`book/AI-End-to-End-Learning-Track.pdf`](book/AI-End-to-End-Learning-Track.pdf), plus a
standalone PDF per chapter in [`book/chapters/`](book/chapters/).

---

## How to use this repo

Open a module's `README.md` for its syllabus, read `notes/`, run everything in `code/`, do
`lab/EXERCISES.md`, skim `papers/PAPERS.md` and `resources/RESOURCES.md`, then present it back with
the deck in `slides/`. Rebuild any deck with
`.venv/bin/python _tools/build_decks.py <module-folder>`.

Every module follows the same shape:

```
<module>/
├── README.md              the syllabus: objectives, suggested path, exit check
├── notes/                 01-core-concepts.md (teaching prose) + 02-deep-dive.md (craft)
├── code/                  2+ runnable, heavily commented scripts — no API keys required
├── lab/EXERCISES.md       graded exercises with stated deliverables and checks
├── papers/PAPERS.md       primary sources — real papers, real URLs, annotated
├── resources/RESOURCES.md courses, repos, communities
└── slides/                deck.json (source) + a built .pptx + a Marp-compatible slides.md
```

New here? Start at [`00-launchpad/`](00-launchpad/) for setup and a one-week fast path.

---

## The learning path

| # | Module | Focus | Time |
|---|--------|-------|------|
| 01 | 🧮 [Machine Learning Foundations](01-ml-foundations/README.md) | The math, models and mindset every AI practitioner starts with. | 20–25h |
| 02 | 🧠 [Deep Learning](02-deep-learning/README.md) | Neural networks, backprop, CNNs, RNNs and the training craft. | 25–30h |
| 03 | 🗣️ [Natural Language Processing](03-nlp/README.md) | From tokens and embeddings to attention and transformers. | 25h |
| 04 | 📚 [Large Language Models](04-llm/README.md) | Pretraining, scaling laws, alignment, inference and prompting. | 25h |
| 05 | 🎨 [Generative AI](05-genai/README.md) | Diffusion, multimodal generation, and creative model families. | 18–22h |
| 06 | 🤖 [AI Agents](06-ai-agents/README.md) | Tool use, planning loops, memory and the ReAct family. | 18–22h |
| 07 | 🕸️ [Agentic AI Systems](07-agentic-ai/README.md) | Multi-agent orchestration, autonomy, hand-offs and control. | 16–20h |
| 08 | 🔍 [Retrieval-Augmented Generation](08-rag/README.md) | Chunking, embeddings, vector search, rerankers and advanced RAG. | 18–22h |
| 09 | 🔌 [Model Context Protocol](09-mcp/README.md) | The open standard for wiring tools, data and prompts into models. | 10–14h |
| 10 | 🏗️ [AI Architecture](10-ai-architecture/README.md) | Reference architectures, patterns and production system design. | 18–22h |
| 11 | 🗺️ [The LLM Model Landscape](11-llm-models/README.md) | Frontier and open models, selection, cost and migration. | 10–14h |
| 12 | ⚖️ [AI Governance](12-ai-governance/README.md) | Policy, risk management, model cards and operating models. | 14–18h |
| 13 | 🛡️ [AI Security](13-ai-security/README.md) | Prompt injection, data exfiltration, red teaming and defenses. | 16–20h |
| 14 | 📋 [AI Compliance](14-ai-compliance/README.md) | EU AI Act, NIST AI RMF, ISO 42001 and audit-ready evidence. | 14–18h |
| 15 | 📊 [AI Evaluation](15-ai-evals/README.md) | Benchmarks, LLM-as-judge, regression suites and online evals. | 16–20h |
| 16 | 🧰 [AI Tech Stack](16-ai-tech-stack/README.md) | The end-to-end tooling map from data to serving to observability. | 60–70h |

Work top to bottom on a first pass. Each module's README states its prerequisites and links back to
what it builds on — 01–04 are load-bearing, 05–11 are applied AI, 12–15 are the responsible-AI layer,
and 16 is the hands-on capstone.

**Only have a week?** Modules 01 → 03 → 04 → 06 → 08, plus the `python` and one of
`langchain`/`langgraph` tracks from Module 16 — see [`00-launchpad/`](00-launchpad/).

---

## 🧰 Module 16 — AI Tech Stack

The capstone: languages, frameworks and runtimes for shipping everything above as software.
[Open the module overview →](16-ai-tech-stack/README.md)

| # | Track | Focus |
|---|-------|-------|
| 16.1 | [Python for AI Engineering](16-ai-tech-stack/tracks/python/README.md) | Modern tooling (uv, ruff), async for LLM batching, Pydantic for structured output |
| 16.2 | [TypeScript for AI Applications](16-ai-tech-stack/tracks/typescript/README.md) | The application layer: streaming, typed tool calls, Zod, the Vercel/Anthropic SDKs |
| 16.3 | [LangChain](16-ai-tech-stack/tracks/langchain/README.md) | The Runnable interface, LCEL, tools, retrieval — and when to skip the framework |
| 16.4 | [LangGraph](16-ai-tech-stack/tracks/langgraph/README.md) | Agents as stateful graphs: persistence, human-in-the-loop, multi-agent patterns |
| 16.5 | [LangSmith: Tracing & Evals](16-ai-tech-stack/tracks/langsmith/README.md) | Tracing, LLM-as-judge evals, the trace→dataset→fix→ship operating loop |
| 16.6 | [AI on AWS with Bedrock](16-ai-tech-stack/tracks/aws-bedrock/README.md) | Shipping AI on AWS: Converse API, Knowledge Bases, Guardrails, IAM, cost |
| 16.7 | [Claude Code & Agent SDK](16-ai-tech-stack/tracks/claude-code/README.md) | Using the harness well, then building your own agent on the SDK |

---

## 🎓 Capstones & shared resources

- [`99-capstones/`](99-capstones/) — three end-to-end capstone projects
- [`_shared/cheatsheets/`](_shared/cheatsheets/) — quick-reference tables pulled from across the track
- [`_shared/glossary/`](_shared/glossary/) — one line per term, grouped by owning module
- [`00-launchpad/`](00-launchpad/) — setup, rebuilding decks, and the suggested order

---

## Build tooling

`_tools/build_decks.py` renders every `slides/deck.json` into a `.pptx` and a Marp-compatible
`slides.md`. `_tools/AUTHORING_SPEC.md` documents the content contract every module follows, if you
want to extend the track yourself.

```bash
.venv/bin/python _tools/build_decks.py                    # rebuild every deck in the repo
.venv/bin/python _tools/build_decks.py 04-llm              # rebuild just one module
.venv/bin/python _tools/build_decks.py claude-code          # matches by folder name anywhere, incl. tracks/
```

No script in this repository requires an API key or network access to run. Anything that talks to a
real hosted service (Bedrock, LangSmith, the Claude API) is either simulated with a deterministic
fake, or guarded to print a clear explanation and exit cleanly when credentials aren't present.
