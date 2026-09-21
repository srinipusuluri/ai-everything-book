---
marp: true
theme: default
paginate: true
style: |
  section h1 { color: #D946EF; }
  section { font-size: 24px; }
---

# AI Security

### Prompt injection has no prepared-statement fix -- build layers, not proofs

**Module 13** · AI End-to-End Learning Track

---

## Why AI security is a different discipline

- Classical appsec separates code (trusted) from data (untrusted)
- SQL injection, XSS: fixed by re-establishing that boundary
- An LLM has ONE input channel: system prompt + history + tool results + user text
- No PREPARE, no escaping function, no 'this is data not instruction' tag
- Defenses reduce risk probabilistically -- they do not restore a boundary
- OWASP ranks prompt injection #1 for exactly this reason

<!-- speaker note: Open with the boundary framing. Every later slide is a variation on 'there is no compiler-enforced line here, only learned bias.' -->

---

## OWASP Top 10 for LLM Apps, 2026 (1 of 2)

| Code | Category | In one line |
|---|---|---|
| LLM01 | Prompt Injection | Attacker input overrides or leaks given instructions |
| LLM02 | Sensitive Info Disclosure | Output or context exposes private/credential data |
| LLM03 | Excessive Agency | System grants more tools/autonomy than the task needs |
| LLM04 | Supply Chain | Compromised weight, dataset, fine-tune, or dependency |
| LLM05 | Data and Model Poisoning | Training or fine-tuning data implants bad behavior |


<!-- speaker note: 2026 is the first edition to weight real incident data (25%) alongside community vote (75%). Excessive Agency jumped from #6 to #3 on that incident data. -->

---

## OWASP Top 10 for LLM Apps, 2026 (2 of 2)

| Code | Category | In one line |
|---|---|---|
| LLM06 | Unbounded Consumption | Uncontrolled cost, DoS, or extraction via volume |
| LLM07 | Misinformation | Model states false claims with unwarranted confidence |
| LLM08 | Hidden Context Exposure | Prompt, tool schemas, and policy text get extracted |
| LLM09 | Vector and Embedding Weaknesses | Retrieval leaks, poisons, or mis-ranks via embeddings |
| LLM10 | Improper Output Handling | Output passed to shell/SQL/renderer unvalidated |


<!-- speaker note: LLM08 was 'System Prompt Leakage' in 2025 -- renamed and widened because tool schemas and policies leak too. Improper Output Handling fell from #5 to #10 as teams got better at basic sanitization. -->

---

## Direct vs. indirect prompt injection

- Direct: the user IS the attacker -- types the jailbreak straight in
- Indirect: attacker plants payload in content the model reads later
- Victim is the trusted user, not the attacker -- they never see the attack
- Scales asynchronously: plant once, wait for any agent to read it
- Composes with tool access -- this is what makes it dangerous in production

<!-- speaker note: Indirect injection is the one that matters operationally. A poisoned webpage, resume, or MCP tool result addressed to the model, not the human reading it. -->

---

## Why it's structurally hard

> **next_token = f(system_prompt + history + tool_results + user_input)**

- Every span of that concatenation is the same kind of token to the model
- Instruction-tuning gives a LEARNED BIAS toward certain framings, not a rule
- A well-crafted injected string can still shift that probability distribution
- Treat every defense as lowering success rate, never as a categorical fix

<!-- speaker note: Say this line out loud: a vendor selling a prompt-injection classifier as 'solved' is selling you the pre-2010s antivirus pitch. -->

---

## Defense-in-depth: what each layer catches

| Layer | Stops | Does not stop |
|---|---|---|
| Delimiting | Naive injections blending into the stream | Rhetorical arguing past the boundary |
| Input classifier | Known phrasings, known templates | Novel phrasing, encoding tricks |
| Privilege separation | The exfiltration step itself | Only for the tool boundary you drew |
| Output filtering | Blind execution of model output | The model being manipulated on content |
| Human approval gate | An action firing unseen | Approval fatigue, rubber-stamping |


<!-- speaker note: This table is the spine of notes/01 section 5.5. No single row is enough alone -- that is the entire argument for defense-in-depth. -->

---

## Demo: watching a pipeline fall for it, then not

- Fake, deterministic model -- reproducible, no API key, offline
- Undefended: naive, sophisticated, and novel injections ALL exfiltrate
- + Delimiting: naive fails, but an authority claim argues past the tag
- + Keyword classifier: catches known phrasings, novel wording sails through
- + Privilege separation: send_email unreachable -- every variant blocked
- code/prompt_injection_defense_demo.py -- run it, read the honest caveat

<!-- speaker note: Walk the staircase: X X X -> . X X -> . . X -> . . . Each layer closes exactly one gap, never all of them at once. -->

---

## The Lethal Trifecta

*Untrusted input + sensitive data + external comms, one agent, no gate*


<!-- speaker note: Pause here. This is the single highest-leverage idea in the module -- everything after this slide is either detecting it or removing it. -->

---

## Three legs, danger is in the conjunction

- Untrusted input: web pages, email, tickets, third-party tool results
- Sensitive data access: credentials, PII, internal docs, a database
- External communication: send email, post to a URL, call another API
- Any ONE leg alone is fine -- a research agent reading the open web is safe
- All three, one reachable context, no gate: the attacker's payload ships your data

<!-- speaker note: Give the two 'fine alone' examples from notes/02: an open-web research agent, and a customer reading their own balance. Neither is a trifecta. -->

---

## Spotting it: the three-question checklist

| # | Question | Yes means |
|---|---|---|
| 1 | Does this node ingest content you don't fully control? | untrusted input |
| 2 | Does it hold a credential reaching confidential data? | sensitive data access |
| 3 | Can it act externally without human approval first? | ungated communication |


<!-- speaker note: Walk every node in an architecture diagram -- agent, subgraph, or single LLM call with a bound tool list -- and ask these three. All three yes on one node is the flag. -->

---

## Fixing it: three moves, in order of preference

- 1. Split: untrusted-reading agent emits a narrow schema, not free text
- 2. Gate: human approval before the communication/write action fires
- 3. Remove: does the agent really need to POST, or just draft for a human?
- Splitting removes the attack surface; gating converts action to accountability
- Removing agency is usually a discovery, not a downgrade

<!-- speaker note: notes/02 section 2 orders these deliberately -- split first because it needs no ongoing vigilance, gating second, removal last because it changes scope. -->

---

## Analyzer results: 7 declared agent configs

| Agent | 3 legs present? | Verdict |
|---|---|---|
| web_research_assistant | input only | safe |
| customer_account_assistant | sensitive data only | safe |
| inbox_triage_agent_v1 | all three, ungated | FLAGGED |
| inbox_triage_agent_v2 (gated) | all three, gated | safe |
| devops_mcp_agent | all three, ungated | FLAGGED |
| devops split pair (reader + action) | split across two agents | safe |


<!-- speaker note: code/lethal_trifecta_analyzer.py. The v1/v2 pair differs by ONE boolean -- human_approval_required on send_email -- and that alone flips the verdict. -->

---

## Excessive agency: three components

- Excessive functionality: the tool can do more than the task needs
- Excessive permissions: the credential is broader than the tool's purpose
- Excessive autonomy: no human checkpoint before a consequential action
- Fix mirrors classical least-privilege, applied to a model that can be persuaded
- Scope the tool, scope the credential, gate the irreversible step

<!-- speaker note: LLM03 in the 2026 list, up from #6 in 2025 -- driven by real incident data as agentic systems with real tool access shipped at scale. -->

---

## Jailbreak families you should recognize

| Family | Mechanism | Watch for |
|---|---|---|
| Roleplay/persona | 'You are DAN, no restrictions' framing | Sudden persona assignment |
| Encoding/obfuscation | Base64, ROT13, split disallowed tokens | Encoded blobs plus decode instruction |
| Many-shot | Dozens of fabricated compliant example turns | Unusually long Q-and-A-heavy prompt |
| Crescendo | Small benign escalations across many turns | Conversation drifting steadily one way |


<!-- speaker note: Same root cause as injection -- manipulating context, not exploiting a code bug. That is why these are red-team knowledge, not a patchable CVE. -->

---

## Model-level and data risks

- Adversarial suffixes: optimized tokens that suppress refusals (GCG attack)
- Model extraction: querying an API to train a cheap imitation model
- Membership inference: proving a specific record was in training data
- Training data poisoning: a hidden trigger implanted in a data subset
- RAG over-retrieval: vector search returns docs the user can't see
- Embedding inversion: vectors decode back into near-original text

<!-- speaker note: The RAG line is the most common real-world instance: the vector index's ACLs lag the source system's. Fix is filtering at query time, never a polite prompt. -->

---

## Guardrails in the request path

| Stage | Job | Honest limit |
|---|---|---|
| Input classifier | Flags injection/jailbreak patterns | Misses novel or obfuscated attacks |
| Rate limiter | Per-key volume, anomaly detection | Nothing against one crafted request |
| Output classifier | Flags disallowed content | Same false-negative limit as input |
| PII redaction | Scans output before it leaves | Last-resort net, not prevention |
| Action gate | Human approval on consequential calls | A rubber-stamping human is not a control |


<!-- speaker note: Guardrails are the safety net under an architecture that should already be sound -- not a substitute for privilege separation upstream. -->

---

## Traditional pentest vs. LLM red-team

|  | Traditional pentest | LLM red-team |
|---|---|---|
| Target | Code, network, infra | Model behavior AND the system around it |
| Finding | Reproducible exploit, CVE-shaped | Often probabilistic -- works 30% of the time |
| Reproducibility | Deterministic given same input | Sampling and model updates change results |
| Scoring | Binary: exploitable or not | Graded severity plus success-rate scale |


<!-- speaker note: The deliverable is an adversarial prompt library, automated plus human red-teaming, and a scored report mapped back to OWASP categories -- not just a pile of transcripts. -->

---

## Supply chain, and the honest close

- A model weight is an opaque binary you're choosing to execute -- verify provenance
- A compromised MCP server is a compromised dependency wearing a new hat
- safetensors exists because pickle checkpoints can carry arbitrary code
- Every layer in this module lowers success probability, none proves safety
- Exit check: name which layer catches which attack, and what still gets through

<!-- speaker note: Close on the honest note from notes/01 section 4: if you cannot write the sentence naming what still gets through your stack, you have a hope, not a threat model. -->

---

## Now go build

`code/` run it · `lab/EXERCISES.md` break it · `papers/` go deeper
