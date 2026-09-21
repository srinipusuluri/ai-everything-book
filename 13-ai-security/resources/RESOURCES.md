# 🔗 Resources — AI Security

## Frameworks and living references

| Resource | What it's for | Link |
|---|---|---|
| **OWASP GenAI Security Project — LLM Top 10** | The taxonomy this module organizes around; check for a new edition roughly annually | https://genai.owasp.org/llm-top-10/ |
| **OWASP GenAI Security Project — home** | Also publishes the Agentic AI Security guidance, an AI security checklist, and a MAESTRO threat-modeling framework for multi-agent systems | https://genai.owasp.org/ |
| **MITRE ATLAS** | ATT&CK-style knowledge base of adversary tactics/techniques against AI systems, with real case studies — use it to threat-model a system the way you'd use ATT&CK for a network | https://atlas.mitre.org/ |
| **NIST AI Risk Management Framework (AI RMF 1.0)** | The US government's map/measure/manage/govern framework; pairs with Module 12/14's governance and compliance framing | https://www.nist.gov/itl/ai-risk-management-framework |

## Tools worth running yourself

| Tool | What it does | Link |
|---|---|---|
| **garak** (NVIDIA) | An "nmap for LLMs" — a CLI vulnerability scanner that runs a library of probes (jailbreaks, injections, data leakage, toxicity) against a target model and reports which ones land | https://github.com/NVIDIA/garak |
| **promptfoo** (red-team mode) | Declarative-config LLM eval and red-teaming tool: define a target, pick attack plugins (injection, jailbreak, PII, excessive agency, and more), get a scored report — usable in CI | https://www.promptfoo.dev/docs/red-team/ |
| **PyRIT** (Microsoft) | Python framework for orchestrating red-team attacks against generative AI systems at scale, including a working implementation of the Crescendo multi-turn attack from papers/PAPERS.md | https://github.com/microsoft/PyRIT |
| **Anthropic's red-teaming resources** | Anthropic's public research and practices around red-teaming, jailbreak robustness, and Constitutional Classifiers (their defense against universal jailbreaks) | https://www.anthropic.com/research |
| **vec2text** | The reference implementation behind the embedding-inversion paper in papers/PAPERS.md — run it yourself to see how much text a "just numbers" embedding actually reveals | https://github.com/vec2text/vec2text |

## Courses and structured learning (free)

| Course | Who it's for | Link |
|---|---|---|
| **OWASP GenAI Security Project — LLM Top 10 guidance docs** | The most direct, free, no-signup path into this module's core frame, per-category | https://genai.owasp.org/llm-top-10/ |
| **Learn Prompting — Prompt Hacking course** | Free, hands-on introduction to injection and jailbreak techniques from the offensive side, useful for building intuition before you defend | https://learnprompting.org/docs/category/-prompt-hacking |
| **Microsoft — AI red teaming learning path (Learn)** | Structured, free modules on red-teaming generative AI systems using PyRIT | https://learn.microsoft.com/en-us/security/ai-red-team/ |
| **Stanford CS 329T / related AI security seminars** | Academic depth on adversarial ML if you want the underlying math, not just the applied practice | https://cs329t.stanford.edu/ |

## Repositories worth cloning

| Repo | What's inside |
|---|---|
| https://github.com/NVIDIA/garak | The scanner itself, plus its probe/detector library — read the probes directory to see the current attack catalog |
| https://github.com/promptfoo/promptfoo | The eval/red-team engine; `site/docs/red-team/` is a genuinely good written curriculum on its own |
| https://github.com/microsoft/PyRIT | Orchestrators, targets, and scorers for automated multi-turn red-teaming |
| https://github.com/llm-attacks/llm-attacks | Official code for the GCG adversarial-suffix attack (papers/PAPERS.md) — read, don't deploy |
| https://github.com/vec2text/vec2text | Embedding inversion reference implementation |
| https://github.com/microsoft/PromptBench | Adversarial prompt robustness benchmarking |

Clone the starter set with: `bash ../_tools/clone_repos.sh 13-ai-security`

## Communities

- OWASP GenAI Security Project Slack/mailing list — linked from https://genai.owasp.org/
- r/artificial and r/MachineLearning (safety- and red-teaming-tagged threads) — https://www.reddit.com/r/MachineLearning/
- AI Village (DEF CON) — the AI/ML security community that runs the annual DEF CON AI red-teaming events — https://aivillage.org/
- Papers with Code, "adversarial attack" and "red teaming" task pages — https://paperswithcode.com/

## Cheat sheets

- OWASP LLM Top 10 quick-reference card (linked from the project page) — https://genai.owasp.org/llm-top-10/
- MITRE ATLAS technique matrix (the visual overview, same idea as the ATT&CK matrix) — https://atlas.mitre.org/matrices/ATLAS
- Also see [../../_shared/cheatsheets/](../../_shared/cheatsheets/)
