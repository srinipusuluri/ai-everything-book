# 📄 Papers & Primary Sources — AI Evaluation

Read the three starred papers first — they are the benchmark canon, the judge-bias canon, and the statistics
canon respectively. The rest are organized by the section of the notes they back up.

## The canon (read in this order)

| # | Paper | Year | Why it matters | Link |
|---|-------|------|-----------------|------|
| 1 | **Measuring Massive Multitask Language Understanding** (MMLU) — Hendrycks et al. | 2020 | The benchmark you'll see quoted more than any other. Read it to know exactly what its 57 subjects do and don't cover before quoting its number. | [arXiv:2009.03300](https://arxiv.org/abs/2009.03300) |
| 2 | ★ **Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena** — Zheng et al. | 2023 | The paper that names and measures position bias, verbosity bias, and self-enhancement bias in LLM judges, and shows GPT-4-as-judge reaches ~80%+ agreement with humans on MT-Bench. The direct source for `code/judge_bias_and_calibration.py`'s bias catalog. | [arXiv:2306.05685](https://arxiv.org/abs/2306.05685) |
| 3 | ★ **Holistic Evaluation of Language Models** (HELM) — Liang et al. | 2022 | Multi-metric, multi-scenario evaluation as the honest alternative to a single leaderboard number; the methodology behind "report accuracy, calibration, robustness, fairness, and cost together, not just one." | [arXiv:2211.09110](https://arxiv.org/abs/2211.09110) |
| 4 | ★ **The Hitchhiker's Guide to Testing Statistical Significance in NLP** — Dror, Baumer, Shlomov & Reichart | 2018 | Surveyed a year of ACL/TACL papers and found most skipped significance testing entirely. The practical protocol for choosing the right test — the paper `code/statistical_rigor_for_evals.py`'s McNemar/bootstrap choices are built on. | [ACL Anthology P18-1128](https://aclanthology.org/P18-1128/) · companion material: [arXiv:1809.01448](https://arxiv.org/abs/1809.01448) |

## Benchmark literacy

| Paper | Year | One-line takeaway | Link |
|---|---|---|---|
| **Evaluating Large Language Models Trained on Code** (Codex / HumanEval) — Chen et al. | 2021 | Introduces HumanEval and `pass@k`; read it to see how narrow the original 164 hand-written problems really are. | [arXiv:2107.03374](https://arxiv.org/abs/2107.03374) |
| **SWE-bench: Can Language Models Resolve Real-World GitHub Issues?** — Jimenez et al. | 2023 | Real GitHub issues, real repos, tests as the pass/fail oracle — the credible successor to toy code benchmarks, with its own narrowness (12 popular Python repos). | [arXiv:2310.06770](https://arxiv.org/abs/2310.06770) |
| **GPQA: A Graduate-Level Google-Proof Q&A Benchmark** — Rein et al. | 2023 | 448 PhD-level science questions; also reports the striking gap between domain experts (~65%) and skilled non-experts with web access (~34%) — a good citation for "expertise, not search, is the bottleneck." | [arXiv:2311.12022](https://arxiv.org/abs/2311.12022) |

## Benchmark contamination

| Paper | Year | One-line takeaway | Link |
|---|---|---|---|
| **Time Travel in LLMs: Tracing Data Contamination in Large Language Models** — Golchin & Surdeanu | 2023 | The "guided instruction" technique: prompt the model with a dataset name plus a truncated instance and see if it completes the rest verbatim. Found GPT-4 contaminated on several standard datasets. | [arXiv:2308.08493](https://arxiv.org/abs/2308.08493) |
| **Pretraining on the Test Set Is All You Need** — Schaeffer | 2023 | A deliberately absurd 1M-parameter model trained directly on benchmark data "beats" every real foundation model on the leaderboards it was trained on. The cleanest possible demonstration of why a leaderboard number alone proves nothing about capability. | [arXiv:2309.08632](https://arxiv.org/abs/2309.08632) |

## LLM-as-judge and human evaluation

| Paper | Year | One-line takeaway | Link |
|---|---|---|---|
| **Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena** — Zheng et al. | 2023 | (See canon above — the bias catalog paper.) | [arXiv:2306.05685](https://arxiv.org/abs/2306.05685) |
| **Holistic Evaluation of Language Models** (HELM) — Liang et al. | 2022 | (See canon above.) | [arXiv:2211.09110](https://arxiv.org/abs/2211.09110) |

## Statistical rigor

| Paper | Year | One-line takeaway | Link |
|---|---|---|---|
| **The Hitchhiker's Guide to Testing Statistical Significance in NLP** — Dror et al. | 2018 | (See canon above.) | [ACL Anthology P18-1128](https://aclanthology.org/P18-1128/) |
| **Show Your Work: Improved Reporting of Experimental Results** — Dodge et al. | 2019 | Variance across random seeds is often larger than the "improvement" a paper reports; argues for reporting expected validation performance as a function of compute budget, not a cherry-picked best run. Directly relevant to the p-hacking section of `code/statistical_rigor_for_evals.py`. | [arXiv:1909.03004](https://arxiv.org/abs/1909.03004) |

## How to read an eval paper (30 minutes, 3 passes)

1. **Pass 1 (5 min):** what exactly is being measured — read the task definition and one full example, not just
   the headline metric name.
2. **Pass 2 (15 min):** how was the reference/gold label produced (human annotation? another model? scraped?),
   and what's the inter-annotator or inter-judge agreement, if reported at all.
3. **Pass 3 (10 min):** the limitations section, and specifically whether the authors discuss contamination
   risk or benchmark saturation. If a benchmark paper has neither, treat every score derived from it a little
   more skeptically.

Keep a one-paragraph note per paper: what it measures, what it doesn't, and the one number you'd actually want
next to any score quoted from it (an interval, an agreement statistic, a contamination check).
