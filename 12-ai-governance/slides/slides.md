---
marp: true
theme: default
paginate: true
style: |
  section h1 { color: #EC4899; }
  section { font-size: 24px; }
---

# AI Governance

### Who decides, who signs off, and what you show the auditor a year later

**Module 12** · AI End-to-End Learning Track

---

## Why this module exists

- Every other module teaches how to build AI. This one teaches whether you should
- Governance = internal policy, process, org design -- not law, not technical controls
- Module 14 = external law. Module 13 = technical controls. This module = who signs off
- The question every incident traces back to: who decided this was low-risk, and why

<!-- speaker note: Open by drawing the three-way split on the whiteboard: governance / security / compliance. Students conflate all three constantly. -->

---

## Why AI breaks traditional IT governance

- Confidently wrong on purpose -- a hallucination looks exactly like a real answer
- Behavior is emergent, not specified -- you can't read the weights like you read code
- Agentic systems act, not just answer -- the risk surface is 'it might DO something'
- You often don't own the supply chain -- a vendor's silent version bump changes your product

<!-- speaker note: Four gaps, four reasons the old change-management playbook doesn't cover AI. Everything else in this module is a response to one of these four. -->

---

## NIST AI RMF -- four functions

| Function | Asks | Output |
|---|---|---|
| Govern | Do we have policy and accountability first? | Charter, committee, named roles |
| Map | What is this system, for whom, in what context? | Use-case inventory entry |
| Measure | Does it perform, is it trustworthy? | Eval results, bias testing |
| Manage | What do we mitigate, monitor, or kill? | Risk treatment, monitoring plan |


<!-- speaker note: Govern is cross-cutting -- it wraps the other three continuously, it doesn't run once. Voluntary guidance, not a certificate. -->

---

## ISO/IEC 42001 -- the certifiable sibling

- An AI Management System (AIMS) standard -- same shape as ISO 27001
- Clauses 4-10, Plan-Do-Check-Act, an accredited body can certify you
- Annex A: 38 reference controls across 9 areas, plus a Statement of Applicability
- Reach for this when a customer or regulator wants third-party-audited proof

<!-- speaker note: If they already run ISO 27001 this will look immediately familiar -- same harmonized structure. -->

---

## Choosing a framework

|  | NIST AI RMF | ISO/IEC 42001 | EU AI Act |
|---|---|---|---|
| Nature | Voluntary guidance | Certifiable standard | Binding law |
| Proves | We thought about this | An auditor verified it | Legally permitted in EU |
| Cost | Low -- a mapping exercise | Medium-high -- audits | Mandatory if in scope |


<!-- speaker note: Not competitors. Most mature programs run AI RMF internally and pursue ISO 42001 only when there's an external audience demanding the certificate. -->

---

## Risk tiering

*The mechanic every framework converges on*


<!-- speaker note: Transition slide. Everything above is acronyms; this is the actual mechanic underneath all of them. -->

---

## Four attributes that predict harm

| Attribute | Low end | High end |
|---|---|---|
| Data sensitivity | Public info | Special-category (health, biometric) |
| Decision autonomy | Advisory, human decides | Fully autonomous, no override |
| Population scale | A handful of users | General public / systemic |
| Reversibility | Edit and resend | Irreversible (denied care, wrongful loss) |


<!-- speaker note: A spell-checker and an autonomous fraud-blocker are not the same risk even though both are 'AI'. These four axes are why. -->

---

## Demo: the risk register in action

- code/ai_risk_register_template.py scores 6 real-shaped use cases on these 4 axes
- Medical triage assistant: 86/100 -- health data + high autonomy + irreversibility
- Resume screener: 76/100 -- an EU AI Act Annex III 'employment' use case
- Internal code assistant: 24/100 -- advisory only, tiny population, trivially reversible
- If every use case lands in the same tier, your weights aren't discriminating -- that's a bug

<!-- speaker note: Run this live: python code/ai_risk_register_template.py --demo --legend. Let them see the score breakdown per use case, not just the final tier. -->

---

## Tiers -> proportional controls

| Tier | Example | Review required |
|---|---|---|
| Minimal | Internal code assistant | Self-attestation, AI inventory entry |
| Limited | Customer FAQ chatbot | Business-owner sign-off, model card |
| High | Fraud-detection flagging | Governance committee + MRM validation |
| Critical | Medical triage, autonomous txns | Executive sign-off, human-in-command |


<!-- speaker note: The entire point of tiering: a low-risk internal tool should never drag the same review machinery as a customer-facing credit decision. -->

---

## Operating model

*Who does the work, day to day*


<!-- speaker note: Transition. A framework tells you what to think about; an operating model tells you which named human is on the hook. -->

---

## Roles and what they actually do

| Role | Does | Does NOT do |
|---|---|---|
| Governance committee | Sets policy, approves High/Critical launches | Review every prompt tweak |
| MRM function | Independently validates a specific system | Build the model -- independence is the point |
| Responsible AI office | Owns standards, trains teams | Hold veto power itself |
| Accountable executive | Signs deployment, owns the outcome | Skip this role. Don't skip this role. |


<!-- speaker note: MRM comes from banking (SR 11-7, post-2008) -- the team that built the model is structurally bad at grading its own homework, not from bad faith. -->

---

## Model cards as governance artifacts, not paperwork

- The single artifact committee, MRM, legal, and an auditor all read first
- Intended use = the boundary the committee actually approved
- Out-of-scope uses = what stops 'repurpose the chatbot for medical advice'
- For a RAG/agentic system, call it a system card -- it's a pipeline, not one model

<!-- speaker note: Point to code/model_card_template.md -- a full worked example for a customer-support RAG assistant, annotated section by section with the governance reason each part exists. -->

---

## Three human-oversight postures

| Posture | Human does | Fits |
|---|---|---|
| Human-in-the-loop | Approves before every action | High / Critical |
| Human-on-the-loop | Monitors a stream, can intervene | Limited / High |
| Human-in-command | Sets boundaries, standing override | Critical |


<!-- speaker note: A HITL gate fails as a control the moment the approver has no time, no context, or no consequence for rubber-stamping. Design against that, not just for the label. -->

---

## The rubber-stamp trap

> **An approver with a 100% approve rate over 500 decisions is a signal the gate isn't doing what you think it's doing.**

- Show the approver WHY the system proposed the action, not just the output
- Set an SLA the volume actually allows -- 500/day on one queue is HOTL wearing HITL's paperwork
- Sample-audit the approvals themselves as an ongoing MRM metric

<!-- speaker note: This is the slide that makes 'human in the loop' stop being a magic phrase people say to sound responsible. -->

---

## Vendor and third-party AI risk

- Most orgs call a model API or embed a vendor AI feature -- they don't train foundation models
- Standard vendor security questionnaires don't ask the AI-specific questions
- Ask: do you train on our data, what happens on a version bump, what's your incident SLA
- Require: data-use restriction, version pinning or notice, audit rights, sub-model disclosure

<!-- speaker note: The single most common way an AI vendor silently breaks your product: a default-model change with zero notice. Contract for pinning or advance notice. -->

---

## Change management: a prompt edit is a deployment

- Behavior can change via: prompt edit, vendor model bump, corpus update, sampling params
- None of these touch a pull request in most orgs -- and all four are governed changes
- Rule: any change that can shift output distribution gets the review rigor of its tier
- A High-tier model doesn't stop being High-tier because 'only the prompt' changed

<!-- speaker note: This is the rule teams skip most often, because it doesn't feel like a deployment. It is one. -->

---

## Incident response, the governance-specific version

- Triage against the risk tier, not just severity
- Contain at the layer that's actually broken -- prompt, corpus, tool access, guardrail
- Root-cause past 'the model hallucinated' -- that's a restatement, not a cause
- Feed the finding back into the eval suite and the risk register, or it wasn't reviewed

<!-- speaker note: An incident review that changes nothing in the eval suite or the register was closed, not reviewed. That distinction is the whole slide. -->

---

## Audit trail as a byproduct, not a chore

- A regulator/auditor asks for: inventory + tier, model card, oversight evidence, change history
- Every one of those should already exist from good engineering practice
- Eval suite output IS the evidence. Traces tagged with prompt/model version ARE the change log
- The governance function's job: make sure it exists and is legible, not invent a parallel trail

<!-- speaker note: Landing point: governance done well is nearly invisible in daily work because it rides on practices you'd want anyway. -->

---

## Your exit check

- Take a real use case through code/ai_risk_register_template.py, get a defensible tier
- Name the specific committee/role that signs off at that tier
- Sketch the human-oversight posture it needs and why
- List three pieces of evidence an auditor would ask for a year later
- Then: Module 13 -- AI Security, or Module 14 -- AI Compliance

<!-- speaker note: If they can do all four without reopening the README, the module landed. -->

---

## Now go build

`code/` run it · `lab/EXERCISES.md` break it · `papers/` go deeper
