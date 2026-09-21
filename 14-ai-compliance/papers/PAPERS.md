# 📄 Papers & Primary Sources — AI Compliance

**Read the primary legal texts first, commentary second.** Law-firm blog posts and LinkedIn summaries
lag the actual text and compound each other's errors — a pattern this module warns about repeatedly.
Every link below was checked at the time this file was written (September 2026); re-verify anything
date-sensitive per [notes/03's "how to stay current"](../notes/03-building-a-compliance-program.md#4-how-to-stay-current).

## Read these two first

| # | Source | Why it matters | Link |
|---|---|---|---|
| 1 | **Regulation (EU) 2024/1689** (the EU AI Act) — official consolidated text | The actual binding law. Everything in notes/01 is a summary of this; cite this, never the summary, for anything load-bearing. | [EUR-Lex](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) |
| 2 | **NIST AI RMF 1.0** (NIST AI 100-1, Jan 2023) | The most-referenced US framework — voluntary, but cited by the FTC, CFPB, FDA, SEC, and EEOC. The Govern/Map/Measure/Manage structure this module's US material assumes. | [PDF](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf) |

## The EU AI Act — text, guidance, and the Digital Omnibus

| Source | What it is | Link |
|---|---|---|
| Regulation (EU) 2024/1689 — full text, all languages | The primary source | [EUR-Lex](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) |
| EU AI Act Service Desk | European Commission's official Q&A and guidance portal, updated as amendments land | [ai-act-service-desk.ec.europa.eu](https://ai-act-service-desk.ec.europa.eu/) |
| Implementation Timeline tracker | Independently maintained but closely tracks official dates; the single best place to check "what's in force right now" | [artificialintelligenceact.eu/implementation-timeline](https://artificialintelligenceact.eu/implementation-timeline/) |
| European Commission — AI Act policy page | The Commission's own framing of the regulatory approach | [digital-strategy.ec.europa.eu](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai) |
| GPAI Code of Practice | The Commission's voluntary code for general-purpose-AI providers (transparency, copyright, safety/security) | [digital-strategy.ec.europa.eu](https://digital-strategy.ec.europa.eu/en/policies/contents-code-gpai) |
| Digital Omnibus on AI (2026 amendment) | The 2026 package that deferred several high-risk deadlines — read this to understand *why* notes/01's timeline table has "deferred" rows, not just *that* it does | Search EUR-Lex for the Digital Omnibus's official regulation number at time of reading; the number was still being finalized in secondary sources as of this module's last check — confirm via the Service Desk link above rather than trusting a specific citation here |

## NIST AI Risk Management Framework and profiles

| Source | What it is | Link |
|---|---|---|
| NIST AI RMF 1.0 (NIST AI 100-1) | The core framework | [PDF](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf) |
| NIST AI RMF: Generative AI Profile (NIST AI 600-1, July 2024) | Adapts Govern/Map/Measure/Manage to generative AI and agentic systems; 12 named risk categories | [PDF](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) |
| NIST AI RMF program page | Where new profiles get posted as they're released | [nist.gov/itl/ai-risk-management-framework](https://www.nist.gov/itl/ai-risk-management-framework) |

## Standards

| Source | What it is | Link |
|---|---|---|
| ISO/IEC 42001:2023 | The certifiable AI management system standard (structured like ISO 27001/9001). The standard text is paywalled by ISO; the page below is the authoritative place to confirm the current edition and scope before citing it. | [iso.org](https://www.iso.org/standard/81230.html) |

## Policy and law-review scholarship

| Paper | Author(s) / Venue | One-line takeaway | Link |
|---|---|---|---|
| **The Brussels Effect** | Anu Bradford, Northwestern University Law Review, 2012 | The foundational argument for *why* the EU can set de facto global tech rules through market access alone — the intellectual frame for "the EU AI Act matters even if you never ship there directly" | [Northwestern Scholarly Commons](https://scholarlycommons.law.northwestern.edu/nulr/vol107/iss1/1/) |
| **The Brussels Effect** (book-length treatment) | Anu Bradford, Oxford University Press, 2020 | Full-length version of the above, with AI/tech regulation as a running case study | [Oxford Academic](https://academic.oup.com/book/36491) |
| Working paper / SSRN copy of "The Brussels Effect" | Anu Bradford | Freely downloadable working-paper version if the journal link above is unavailable | [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2770634) |

## How to read a regulatory text (30 minutes, adapted from the ML-paper method)

1. **Pass 1 (10 min):** recitals (the "whereas" clauses) and definitions article. Ask: what problem is
   this solving, and what does it call the things I care about?
2. **Pass 2 (15 min):** the operative articles relevant to your question, plus any annex they reference.
   Ask: who exactly does this bind (provider? deployer? both?), and what's the actual trigger condition?
3. **Pass 3 (5 min):** the transitional/entry-into-force provisions. Ask: is this even in force yet, and
   has it been amended since the copy I'm reading was published? This pass is the one people skip and
   the one that gets them in trouble with a fast-moving law like this one.

Keep a one-paragraph note per source with the date you checked it — for this module more than any other
in the track, that date is load-bearing information, not metadata.
