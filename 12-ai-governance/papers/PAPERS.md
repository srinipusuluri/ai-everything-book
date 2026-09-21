# 📄 Papers & Primary Sources — AI Governance

Unlike most modules in this track, the primary sources here are **frameworks and standards documents**, not
papers with a novel method. Read the frameworks first — everything else in this module operationalizes them.
A handful of research papers underpin the concrete artifacts (model cards, datasheets) and the risk taxonomy
this module's risk register is built from; those are worth reading in full too, they're short.

## Read these two first

| # | Source | Why it matters | Link |
|---|-------|----------------|------|
| 1 | **NIST AI Risk Management Framework 1.0** (NIST AI 100-1, Jan 2023) | The four-function structure (Govern/Map/Measure/Manage) this module's notes/01 §2 is built on. Free, voluntary, and the closest thing to a lingua franca for AI risk in the US. | [PDF](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf) · [NIST landing page](https://www.nist.gov/itl/ai-risk-management-framework) |
| 2 | **Model Cards for Model Reporting** — Mitchell, Wu, Zaldivar, Barnes, Vasserman, Hutchinson, Spitzer, Raji, Gebru (FAT* 2019) | The paper that invented the model card as a governance artifact. `code/model_card_template.md` is a direct descendant of this structure (intended use, factors, metrics, evaluation data, training data, ethical considerations, caveats). | [arXiv:1810.03993](https://arxiv.org/abs/1810.03993) |

## Frameworks and standards (the core reading)

| Source | Publisher / Year | One-line takeaway | Link |
|---|---|---|---|
| **AI RMF Playbook** | NIST, 2023 (updated periodically) | Suggested actions per AI RMF subcategory — the practical companion to the framework itself; adapt, don't copy verbatim. | [AIRC Playbook](https://airc.nist.gov/airmf-resources/playbook) |
| **NIST AI 600-1 — Generative AI Profile** | NIST, July 2024 | Maps the four AI RMF functions to 12 risks specific to or amplified by generative AI (confabulation, data privacy, information integrity, value-chain integration, and others). Read this if your use case involves an LLM, which in this track is almost always. | [PDF](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) |
| **ISO/IEC 42001:2023 — AI management systems** | ISO/IEC, Dec 2023 | The certifiable AI management system standard behind notes/01 §3 — Harmonized Structure, clauses 4-10, Annex A's 38 controls across 9 groups, Statement of Applicability. The standard text itself is paywalled; the overview page is authoritative and free. | [ISO overview](https://www.iso.org/standard/42001) |
| **SR 11-7 — Supervisory Guidance on Model Risk Management** | Federal Reserve / OCC, 2011 | The banking-sector origin of the model risk management (MRM) discipline this module borrows in notes/02 §2 — independent validation, separate from model development, as a structural control. Still the reference text bank examiners cite. | [PDF](https://www.federalreserve.gov/boarddocs/srletters/2011/sr1107.pdf) |
| **OECD AI Principles** | OECD, 2019, updated May 2024 | The first intergovernmental AI standard (47 adherents as of 2024); five principles — human-centered values, transparency, robustness/safety, accountability, inclusive growth — that most national frameworks (including the EU AI Act's recitals) trace back to. | [OECD.AI](https://oecd.ai/en/ai-principles) |
| **Singapore Model AI Governance Framework** (+ Generative AI and Agentic AI extensions) | IMDA / PDPC, 2019-2026 | A genuinely practical, non-binding, proportionality-first governance framework — worth reading specifically because it's less legalistic than the EU AI Act and closer in spirit to this module's internal-process focus. The 2026 Agentic AI extension is a useful bridge to [Module 07](../../07-agentic-ai/). | [PDPC](https://www.pdpc.gov.sg/help-and-resources/2020/01/model-ai-governance-framework) |

## Foundational documentation-transparency papers

| Paper | Year | One-line takeaway | Link |
|---|---|---|---|
| Datasheets for Datasets — Gebru, Morgenstern, Vecchione, Vaughan, Wallach, Daumé III, Crawford | 2018 (rev. 2021) | The dataset-side sibling of the model card: motivation, composition, collection process, recommended and discouraged uses. `code/model_card_template.md` §4's "training/grounding data summary" is a compressed datasheet. | [arXiv:1803.09010](https://arxiv.org/abs/1803.09010) |
| "Model Cards for Model Reporting" in 2024: Reclassifying Ethical Considerations — various | 2024 | A five-years-later retrospective reframing the original model card's "ethical considerations" section in terms of trustworthiness and risk management — useful for seeing how the artifact has aged. | [arXiv:2403.15394](https://arxiv.org/abs/2403.15394) |
| GPT-4 System Card — OpenAI | 2023 | The most-cited real-world example of a **system card** (vs. model card) — explicitly analyzes the deployed system including non-model mitigations (usage policies, access controls), which is exactly the distinction notes/02 §3 draws for the RAG example. | [PDF](https://cdn.openai.com/papers/gpt-4-system-card.pdf) |

## Risk taxonomy and incident evidence

| Paper / resource | Year | One-line takeaway | Link |
|---|---|---|---|
| Ethical and Social Risks of Harm from Language Models — Weidinger et al. (DeepMind) | 2021 (FAccT '22 companion) | 21 risks in 6 categories (discrimination, information hazards, misinformation, malicious use, human-computer interaction harms, environmental/socioeconomic harms) — the taxonomy most "what could go wrong" governance intake forms are quietly built from. | [arXiv:2112.04359](https://arxiv.org/abs/2112.04359) |
| AI Incident Database (AIID) | Partnership on AI / Responsible AI Collaborative, ongoing since 2020 | 1,200+ real, sourced AI incidents. The single best antidote to "that would never happen here" in a governance committee meeting — pull three incidents in your sector before your next risk review. | [incidentdatabase.ai](https://incidentdatabase.ai/) |

## How to read a governance framework document (30 minutes)

Frameworks aren't papers — read them differently:

1. **Pass 1 (10 min):** scope and unit of analysis. Is this voluntary guidance, a certifiable standard, or
   binding law? Who is it written for (a whole org, a single system, a specific sector)?
2. **Pass 2 (15 min):** the structure itself — the functions/clauses/categories. Map each one to something
   your organization already does or is missing; that gap list is your adoption backlog.
3. **Pass 3 (5 min):** what evidence would prove you're actually doing this, not just intending to. If the
   framework doesn't suggest an artifact (a document, a log, a sign-off), it's a value statement, not a
   control — note it as aspirational and move on.

Keep one paragraph per framework: what it's for, what it isn't for, and which of your existing artifacts
already partially satisfies it. In six months that paragraph is worth more than the PDF.
