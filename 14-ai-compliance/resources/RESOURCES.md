# 🔗 Resources — AI Compliance

This module ages faster than any other in the track. The most useful thing on this page is the **"how to
stay current"** list at the bottom — treat everything above it as a snapshot, not a subscription.

## Official trackers and primary sources (bookmark these, not a summary of them)

| Source | What it's for | Link |
|---|---|---|
| EU AI Act Service Desk | Official European Commission Q&A and implementation guidance | https://ai-act-service-desk.ec.europa.eu/ |
| EU AI Act Implementation Timeline | Independently maintained, closely tracks official dates and amendments | https://artificialintelligenceact.eu/implementation-timeline/ |
| EUR-Lex — Regulation (EU) 2024/1689 | The actual binding legal text, all EU languages | https://eur-lex.europa.eu/eli/reg/2024/1689/oj |
| European Commission — AI Act policy page | The Commission's own framing and links to related instruments | https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai |
| NIST AI Risk Management Framework | Core framework + profiles (Generative AI, and others as released) | https://www.nist.gov/itl/ai-risk-management-framework |
| FTC — AI enforcement | Enforcement actions and policy statements, posted directly | https://www.ftc.gov/industry/technology/artificial-intelligence |
| IAPP US State AI Governance Legislation Tracker | The best single view of the fastest-moving part of the US landscape | https://iapp.org/resources/article/us-state-ai-governance-legislation-tracker |
| IAPP Global AI Law and Policy Tracker | Same idea, worldwide | https://iapp.org/resources/article/global-ai-legislation-tracker |
| ISO/IEC 42001:2023 | Official standard page — confirm current edition before citing | https://www.iso.org/standard/81230.html |
| FDA — AI/ML-Enabled Medical Devices | FDA's living page on SaMD AI/ML guidance, including PCCP | https://www.fda.gov/medical-devices/software-medical-device-samd/artificial-intelligence-and-machine-learning-aiml-enabled-medical-devices |
| Federal Reserve Supervisory Letters (SR) | Where SR 11-7 / SR 26-2 and other bank guidance is published directly | https://www.federalreserve.gov/supervisionreg/srletters/srletters.htm |
| NYC Department of Consumer and Worker Protection — Local Law 144 | Official page for the AEDT bias-audit law, including filed audit summaries | https://www.nyc.gov/site/dca/about/automated-employment-decision-tools.page |

## Courses

| Course | Who it's for | Link |
|---|---|---|
| **IAPP AI Governance Professional (AIGP) certification prep** | The closest thing to an industry-standard credential for this exact job | https://iapp.org/certify/aigp/ |
| **Coursera — AI Governance / EU AI Act specializations** (search current offerings; providers rotate) | Structured intro for engineers new to the legal side | https://www.coursera.org/ |
| **NIST AI RMF playbook workshops / webinars** | Free, direct from the framework's authors | https://www.nist.gov/itl/ai-risk-management-framework |
| **Future of Privacy Forum training and reports** | Deep, practitioner-oriented on data protection + AI overlap | https://fpf.org/ |

## Communities and ongoing reading

| Resource | Why | Link |
|---|---|---|
| IAPP (International Association of Privacy Professionals) | The professional home base for this entire discipline — news, trackers, local chapters | https://iapp.org/ |
| r/AIPolicy / r/artificial policy threads | Faster than law-firm blogs for "did anyone else see this filing" | https://www.reddit.com/r/AIPolicy/ |
| Tech Policy Press | Independent journalism specifically on AI/tech regulation, less law-firm-marketing-flavored than most alternatives | https://www.techpolicy.press/ |
| Law firm client alerts (use plural, cross-check) | Fast, free, but incentivized to be alarming — read at least two on any big development before believing either | e.g. Gibson Dunn, Wilson Sonsini, DWT, Hogan Lovells AI practice pages |

## How to stay current — the habit, not just the bookmarks

This list matters more than any single link above. Before you state a regulatory fact as settled in a
design doc or a compliance sign-off:

1. **Check the primary source directly**, not a summary of it — see the "Official trackers" table above.
   Summaries lag by weeks to months and compound each other's errors once one gets it slightly wrong.
2. **Ask what changed since your last check**, not just "what does it say now" — a law that was
   comprehensive six months ago and is narrow-and-delayed today (Colorado, notes/01) is a different
   compliance program, not an update to the old one.
3. **Track litigation, not just legislation** — a statute's text and its enforceable reality can diverge
   (the EO 14365 preemption fight, the NYT v. OpenAI case) and the gap is exactly where "I read the law"
   stops being sufficient.
4. **Re-run this module's two tools against a current use case on a quarterly cadence**, the same way
   you'd re-run a security scan — a classifier or mapper that's never re-exercised silently drifts out of
   sync with both the law and your own product surface.
5. **When two sources disagree, prefer the one closer to the regulator** — the Service Desk over a law
   firm blog, the Federal Reserve's own SR-letter page over a summary of it, EUR-Lex over a tracker site
   (trackers are excellent for *finding* what to check, not for *citing* as the final word).

See also [../../12-ai-governance/resources/RESOURCES.md](../../12-ai-governance/resources/RESOURCES.md)
for the internal-governance side of this same reading list, and
[../../15-ai-evals/](../../15-ai-evals/) for the evaluation tooling this module's obligations point back to.
