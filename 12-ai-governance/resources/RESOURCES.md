# 🔗 Resources — AI Governance

## Frameworks and standards bodies (the primary references)

| Framework | Publisher | What it's for | Link |
|---|---|---|---|
| **AI Risk Management Framework (AI RMF 1.0)** | NIST | Voluntary four-function structure (Govern/Map/Measure/Manage) — the fastest free starting point for any org | https://www.nist.gov/itl/ai-risk-management-framework |
| **AI RMF Playbook** | NIST | Suggested actions per subcategory | https://airc.nist.gov/airmf-resources/playbook |
| **NIST AI 600-1 — Generative AI Profile** | NIST | 12 generative-AI-specific risk categories mapped onto the AI RMF | https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf |
| **ISO/IEC 42001:2023** | ISO/IEC | The certifiable AI management system (AIMS) standard | https://www.iso.org/standard/42001 |
| **SR 11-7 — Model Risk Management** | Federal Reserve / OCC | Origin of the MRM discipline this module borrows for independent model validation | https://www.federalreserve.gov/boarddocs/srletters/2011/sr1107.pdf |
| **OECD AI Principles** | OECD | The intergovernmental baseline most national frameworks cite | https://oecd.ai/en/ai-principles |
| **Singapore Model AI Governance Framework** (+ Gen AI / Agentic AI extensions) | IMDA / PDPC | A proportionality-first, non-binding framework — good contrast to the EU AI Act's binding tiers | https://www.pdpc.gov.sg/help-and-resources/2020/01/model-ai-governance-framework |
| **AI Verify** | IMDA (Singapore) | An actual open-source testing toolkit/framework for validating AI system claims against governance principles, not just a document | https://aiverifyfoundation.sg/ |

## Organizations and communities

| Org | What they do | Link |
|---|---|---|
| **Partnership on AI** | Multi-stakeholder nonprofit; runs the AI Incident Database and the ABOUT ML documentation-standards project | https://partnershiponai.org/ |
| **AI Incident Database (AIID)** | 1,200+ sourced, searchable real-world AI failure reports — the best "this actually happened" evidence for a risk committee | https://incidentdatabase.ai/ |
| **NIST AI Resource Center (AIRC)** | Hub for all NIST AI RMF materials, crosswalks (e.g. NIST 600-1 vs. IMDA AI Verify), and profiles | https://airc.nist.gov/ |
| **OECD.AI Policy Observatory** | Tracks national AI policy and governance initiatives across 47+ countries | https://oecd.ai/ |
| **ForHumanity** | Independent nonprofit building auditable, certifiable AI governance criteria (used in some EU AI Act conformity assessments) | https://forhumanity.center/ |

## Cloud-provider responsible AI programs (useful for vendor-risk review, notes/02 §5)

| Provider | Program | Link |
|---|---|---|
| Google Cloud | Responsible AI practices, Vertex AI model cards, Frontier Safety Framework | https://cloud.google.com/responsible-ai · https://ai.google/responsibility/ |
| Microsoft | Responsible AI Standard + per-service Transparency Notes (Azure AI Foundry) | https://www.microsoft.com/en-us/ai/responsible-ai · https://learn.microsoft.com/en-us/azure/ai-foundry/responsible-ai/openai/transparency-note |
| AWS | Responsible AI policy, AWS Well-Architected Responsible AI Lens, Skill Builder courses | https://aws.amazon.com/ai/responsible-ai/policy/ · https://aws.amazon.com/machine-learning/responsible-ai/ |

When you're assessing a vendor per notes/02 §5, these pages are exactly the kind of evidence to ask for —
"can you point me to your model/system card and your responsible-AI documentation for the specific model
version we'd be calling" is a fair, answerable question precisely because these programs exist.

## Courses (free or free-to-audit)

| Course | Who it's for | Link |
|---|---|---|
| **AWS Skill Builder — Introduction to Responsible AI / Security, Compliance & Governance for AI Solutions** | Practitioners who want a vendor's-eye view of governance controls | https://skillbuilder.aws/ |
| **Google — Responsible AI: Applying AI Principles with Google Cloud** | Product/eng teams shipping on Vertex AI | https://www.skills.google/course_templates/388 |
| **Google for Developers — Introduction to Responsible AI** | Quick, free, conceptual grounding | https://developers.google.com/machine-learning/guides/intro-responsible-ai |
| **Coursera — AI Governance / Responsible AI courses** (search current catalog; offerings rotate) | Structured, credentialed option if your org wants a certificate | https://www.coursera.org/ |

## Tools worth knowing about

| Tool | What it does | Link |
|---|---|---|
| **AI Verify** | Open-source testing framework/toolkit to validate AI system claims (fairness, robustness, transparency) against governance principles | https://aiverifyfoundation.sg/ |
| `code/ai_risk_register_template.py` (this module) | The risk-tiering mechanic implemented as a runnable, adjustable tool — start here before reaching for anything heavier | [../code/ai_risk_register_template.py](../code/ai_risk_register_template.py) |
| Model card generation tooling (Hugging Face Hub model cards) | A widely-used, real implementation of the Mitchell et al. model card structure, worth studying as a working example | https://huggingface.co/docs/hub/en/model-cards |

## Cross-references inside this track

- [Module 13 — AI Security](../../13-ai-security/) — the technical controls a governance policy points at
  (prompt injection defenses, red teaming).
- [Module 14 — AI Compliance](../../14-ai-compliance/) — the external, binding-law side of the same
  risk-tiering logic (EU AI Act, sector regulation).
- [Module 15 — AI Evals](../../15-ai-evals/) — where a model/system card's evaluation section actually
  comes from.
- [Module 16 — LangGraph track](../../16-ai-tech-stack/tracks/langgraph/) — the technical mechanism
  (`interrupt()` / `Command(resume=...)`) that implements a human-oversight policy in code.

## Communities

- Partnership on AI mailing list / workstreams — https://partnershiponai.org/
- r/artificial and r/MachineLearning (governance and policy threads surface regularly) — https://www.reddit.com/r/artificial/
- OECD.AI network of experts — https://oecd.ai/en/network-of-experts
