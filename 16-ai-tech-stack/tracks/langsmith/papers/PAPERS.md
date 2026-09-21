# 📄 Primary Sources — LangSmith, Tracing & LLM Evaluation

LangSmith is a product, not a research field, so the primary sources here are **official docs** first and
papers second. Every doc URL below was verified in September 2026. Where a deep path may move, the
section root is given instead.

## Read these three first

| # | Source | Why it matters | Link |
|---|--------|----------------|------|
| 1 | **LangSmith observability concepts** | The exact definitions of run, trace, thread, trajectory, project, feedback, tag, metadata. Read it once and the UI stops being mysterious. | https://docs.langchain.com/langsmith/observability-concepts |
| 2 | **LangSmith evaluation concepts** | Datasets, examples, splits, dataset versions, experiments, evaluators, LLM-as-judge, pairwise, offline vs online evaluation. The vocabulary for the whole second half of this track. | https://docs.langchain.com/langsmith/evaluation-concepts |
| 3 | **Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena** — Zheng et al., 2023 | The paper that named position bias, verbosity bias and self-enhancement bias, and measured them. Everything in §3 of note 02 traces back here. | [arXiv:2306.05685](https://arxiv.org/abs/2306.05685) |

## Official LangSmith documentation

| Topic | What to take from it | Link |
|---|---|---|
| Observability quickstart | The env vars, `@traceable`, `wrap_openai` — the minimum viable instrumentation | https://docs.langchain.com/langsmith/observability-quickstart |
| Trace sampling | `LANGSMITH_TRACING_SAMPLING_RATE`, 0.0–1.0, applied at the root | https://docs.langchain.com/langsmith/sample-traces |
| Mask inputs and outputs | The four PII seams: `process_inputs`, `create_anonymizer`, `hide_inputs`, `LANGSMITH_HIDE_*` | https://docs.langchain.com/langsmith/mask-inputs-outputs |
| Evaluate an LLM application | The `evaluate()` / `aevaluate()` signature and the evaluator contract | https://docs.langchain.com/langsmith/evaluate-llm-application |
| Pairwise evaluation | `evaluate_comparative()` and `randomize_order` as position-bias mitigation | https://docs.langchain.com/langsmith/evaluate-pairwise |
| Manage datasets | `create_dataset`, `create_examples`, splits, automatic versions, `update_dataset_tag` | https://docs.langchain.com/langsmith/manage-datasets |
| Annotation queues | Rubrics, reviewer config, multiple reviewers, reservations, pairwise queues, Add to Dataset | https://docs.langchain.com/langsmith/annotation-queues |
| Online evaluations | Attaching judges to live traffic: filters, sampling rate, spend limits, backfill | https://docs.langchain.com/langsmith/online-evaluations |
| Automations and rules | Routing runs to datasets, queues and webhooks automatically | https://docs.langchain.com/langsmith/rules |
| Dashboards and alerts | What to monitor, and how alerting is wired | https://docs.langchain.com/langsmith/dashboards |
| Prompt engineering concepts | Commits, commit tags, reserved `staging`/`production` tags, `pull_prompt` | https://docs.langchain.com/langsmith/prompt-engineering-concepts |
| Trace with OpenTelemetry | OTLP ingest and export — the escape hatch that makes this a reversible bet | https://docs.langchain.com/langsmith/trace-with-opentelemetry |
| Platform setup | Cloud / BYOC / self-hosted, and which plan gates which | https://docs.langchain.com/langsmith/platform-setup |
| LangSmith Engine | 2026 feature: mines traces for recurring failure patterns, proposes fixes and datasets | https://docs.langchain.com/langsmith/engine-overview |
| Python SDK reference | The authoritative signatures when the guides disagree | https://reference.langchain.com/python/langsmith |
| `langsmith-sdk` on GitHub | Read `run_helpers.py` — it is the real version of `minimal_tracer.py` | https://github.com/langchain-ai/langsmith-sdk |

## Papers worth the time

| Paper | Year | One-line takeaway | Link |
|---|---|---|---|
| Judging LLM-as-a-Judge (MT-Bench / Chatbot Arena) — Zheng et al. | 2023 | Judge biases, named and measured; ~80% agreement with humans at best | [arXiv:2306.05685](https://arxiv.org/abs/2306.05685) |
| G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment — Liu et al. | 2023 | Chain-of-thought + form-filling judging; the template most rubric judges descend from | [arXiv:2303.16634](https://arxiv.org/abs/2303.16634) |
| Large Language Models are not Fair Evaluators — Wang et al. | 2023 | Position bias quantified; swapping candidate order flips verdicts | [arXiv:2305.17926](https://arxiv.org/abs/2305.17926) |
| Benchmarking Cognitive Biases in LLMs as Evaluators (CoBBLEr) | 2023 | Six evaluator biases beyond position and verbosity | [arXiv:2309.17012](https://arxiv.org/abs/2309.17012) |
| Hidden Technical Debt in Machine Learning Systems — Sculley et al. | 2015 | The model is 5% of the system; monitoring and data debt are the rest. The intellectual ancestor of this entire track. | [PDF](https://proceedings.neurips.cc/paper_files/paper/2015/file/86df7dcfd896fcaf2674f757a2463eba-Paper.pdf) |
| Dapper, a Large-Scale Distributed Systems Tracing Infrastructure — Sigelman et al. | 2010 | Where spans, parent ids and trace sampling come from. LangSmith's data model is Dapper with token counts. | [PDF](https://research.google/pubs/pub36356/) |
| Constitutional AI: Harmlessness from AI Feedback — Bai et al. | 2022 | The origin of "a model can score another model's output against written criteria" | [arXiv:2212.08073](https://arxiv.org/abs/2212.08073) |

## Standards and neighbours

| Source | Why | Link |
|---|---|---|
| OpenTelemetry GenAI semantic conventions | The vendor-neutral span/attribute spec. Instrument to this and your backend becomes a choice. | https://github.com/open-telemetry/semantic-conventions-genai |
| OpenTelemetry tracing specification | Spans, context propagation, samplers — the concepts LangSmith renames | https://opentelemetry.io/docs/concepts/signals/traces/ |
| NIST AI Risk Management Framework | The "Measure" and "Manage" functions are this track, in policy language | https://www.nist.gov/itl/ai-risk-management-framework |

## How to read a vendor doc without getting sold

1. **Find the data model page first.** Products are easy once you know their nouns. Skip the tutorials.
2. **Then find the limits page.** Retention, rate limits, trace size caps, plan gating. This is where the
   architecture constraints hide, and it is never in the tutorial.
3. **Then find the escape hatch.** Export, OTLP, self-hosting. If there isn't one, price that in.
4. **Only then read a quickstart.** By that point you are checking syntax, not learning concepts.
