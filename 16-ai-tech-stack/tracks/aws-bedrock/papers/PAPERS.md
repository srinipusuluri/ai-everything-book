# 📄 Primary Sources — Amazon Bedrock

There is no arXiv paper for a cloud API. The primary sources here are the AWS
documentation pages themselves, and reading them properly is the skill.

**Every page below was fetched and verified in September 2026.** AWS ships
weekly; if a page contradicts this track, the page is right. When you find a
discrepancy, fix the track (Exercise 9).

---

## Read these three first

| # | Page | Why it matters |
|---|------|----------------|
| 1 | **[Inference using the Converse API](https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html)** | The single most important page. Full request and response shapes, every ContentBlock type, `inferenceConfig`, the ConverseStream event ordering diagram. Read it twice; write the shapes out from memory the second time. |
| 2 | **[Use a tool to complete a model response](https://docs.aws.amazon.com/bedrock/latest/userguide/tool-use.html)** and **[Client-side tool use](https://docs.aws.amazon.com/bedrock/latest/userguide/tool-use-client-side.html)** | The tool protocol, with a complete working Python loop. Note the three modes now documented — client-side, server-side (Lambda / AgentCore Gateway), and Anthropic-defined tool types. |
| 3 | **[Scaling and throughput best practices](https://docs.aws.amazon.com/bedrock/latest/userguide/scaling-throughput-best-practices.html)** | The page that separates people who have run Bedrock in production from people who have not. Endpoint quota differences, 429 vs 503 vs 529, the ramp-up procedure, the exact botocore retry config. |

---

## The API surface

| Page | Takeaway |
|---|---|
| [What is Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html) | Five quickstarts side by side — Messages, Responses, Chat Completions, Converse, InvokeModel. Useful precisely because it shows how many front doors now exist. |
| [Models at a glance](https://docs.aws.amazon.com/bedrock/latest/userguide/model-cards.html) | The live model catalogue. Model IDs, per-model feature support, Regions. Never hardcode an ID you have not checked here. |
| [Request access to models](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html) | Access is on by default with Marketplace permissions — but Anthropic models need a one-time use-case form. The 15-minute auto-subscription window explains a class of confusing `AccessDeniedException`. |
| [Inference profiles](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles.html) | System-defined vs application profiles; application profiles are how you tag Bedrock costs per team. |
| [Cross-Region inference](https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html) · [Geographic](https://docs.aws.amazon.com/bedrock/latest/userguide/geographic-cross-region-inference.html) | Geographic vs global, the ~10% global discount, and the IAM policy that must list every destination Region. |
| [Prompt caching](https://docs.aws.amazon.com/bedrock/latest/userguide/prompt-caching.html) | Implicit vs explicit, `cachePoint` syntax, per-model minimums, the `tools -> system -> messages` ordering rule, and the `inputTokens` accounting trap. |
| [Provisioned Throughput](https://docs.aws.amazon.com/bedrock/latest/userguide/prov-throughput.html) | Model Units, commitment terms, and the line most people miss: inference profiles do not support PT. |
| [Batch inference](https://docs.aws.amazon.com/bedrock/latest/userguide/batch-inference.html) | Discounted async via S3 JSONL — with no tool calling and no structured output. |
| [Troubleshooting API error codes](https://docs.aws.amazon.com/bedrock/latest/userguide/troubleshooting-api-error-codes.html) | Which errors to retry, which never to. Also the 350-second idle-connection trap, which costs teams a day each time. |
| [Quotas](https://docs.aws.amazon.com/bedrock/latest/userguide/quotas.html) | Token-based quotas, tracked separately per endpoint. |

---

## RAG and agents

| Page | Takeaway |
|---|---|
| [Knowledge Bases](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html) | Managed vs customer-managed. Read the Managed KB section carefully — agentic retrieval, ACL filtering, AgentCore Gateway integration are all recent. |
| [How content chunking works](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-chunking.html) | Default, fixed-size, hierarchical, semantic, none. The hierarchical section explains why you get fewer results than you asked for. |
| [Vector store prerequisites](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-setup.html) | Every supported store with its setup steps. The `faiss`-not-`nmslib` requirement for OpenSearch metadata filtering is buried here and will bite you. |
| [Configure queries and response generation](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-test-config.html) | `numberOfResults`, `overrideSearchType`, the full metadata-filter operator table, implicit filtering, reranking, query decomposition. |
| [Bedrock Agents](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html) | **Read the note at the top.** Agents is now "Agents Classic" and closed to new customers. This one paragraph invalidates most Bedrock agent tutorials written before 2026. |
| [What is AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html) | The replacement: Runtime, Gateway, Memory, Identity, Code Interpreter, Browser, Observability, Policy, Evaluations. Framework-agnostic by design. |

---

## Safety, security and compliance

| Page | Takeaway |
|---|---|
| [Guardrails](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html) · [Create your guardrail](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-components.html) | All six policy types and their configuration fields. |
| [Guardrails with the Converse API](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-use-converse-api.html) | `guardrailConfig`, `guardContent`, `stopReason: "guardrail_intervened"`, the trace shape — **and the table showing that tool results, tool definitions and generated tool arguments are not evaluated.** That table is the most security-relevant thing in the Bedrock docs. |
| [Contextual grounding check](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails-contextual-grounding-check.html) | Grounding vs relevance, the 0–0.99 threshold range, the `grounding_source` / `query` qualifiers, and the four worked grounded/relevant permutations. |
| [Data protection](https://docs.aws.amazon.com/bedrock/latest/userguide/data-protection.html) | The Model Deployment Account architecture — the concrete reason model providers cannot see your prompts. |
| [Interface VPC endpoints](https://docs.aws.amazon.com/bedrock/latest/userguide/vpc-interface-endpoints.html) | Every endpoint service name, the FIPS variants and their Regions, and endpoint policies. |
| [Identity-based policy examples](https://docs.aws.amazon.com/bedrock/latest/userguide/security_iam_id-based-policy-examples.html) | Allow, deny, provisioned-model and console-minimum policies. |
| [Model invocation logging](https://docs.aws.amazon.com/bedrock/latest/userguide/model-invocation-logging.html) | Off by default. Full log schema, the 100 KB inline limit, and the `identity.arn` attribution query. |
| [Evaluate Bedrock resources](https://docs.aws.amazon.com/bedrock/latest/userguide/evaluation.html) | Programmatic, human, judge-model and RAG evaluation. |
| [Amazon Bedrock pricing](https://aws.amazon.com/bedrock/pricing/) | The only rates you should ever quote. Bookmark it; do not memorise it. |

---

## Background reading worth the time

| Source | Why |
|---|---|
| [Timeouts, retries and backoff with jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) — Amazon Builders' Library, Marc Brooker | Why *full* jitter beats backoff-plus-noise. Short, canonical, and it explains the botocore retry formula you are configuring. |
| [Retry with backoff pattern](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/retry-backoff.html) | The AWS prescriptive-guidance version, with the decision tree for retryable vs not. |
| [Boto3 retries guide](https://docs.aws.amazon.com/boto3/latest/guide/retries.html) | Legacy vs standard vs adaptive. The default is `legacy`; you want `standard`. |
| [AWS Well-Architected — Generative AI Lens](https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/generative-ai-lens.html) | AWS's own opinion on GenAI architecture, mapped to the six pillars. Read it critically — it is a vendor document — but the operational-excellence section is genuinely good. |
| [Model Context Protocol specification](https://modelcontextprotocol.io/) | AgentCore Gateway speaks MCP. Module 09 covers it; this is the source. |

---

## How to read an AWS service doc (it is not like reading a paper)

1. **Start at the API reference, not the user guide.** The user guide tells you
   what a feature is for; the API reference tells you what the JSON actually
   looks like. You need the second.
2. **Read the Notes and Important callouts first.** That is where the
   limitations live. "Batch inference does not support tool calling" is a Note.
   "Agents is closed to new customers" is a Note.
3. **Check the date on everything else.** A blog post from 2024 describing
   Bedrock Agents is not wrong about 2024. It is wrong about today.
4. **Verify every model ID and every quota against your own account.**
   `aws bedrock list-foundation-models`, `aws bedrock list-inference-profiles`,
   and the Service Quotas console are ground truth. Documentation is a snapshot.
5. **Keep a one-paragraph note per page you rely on**, with the date you read
   it. In six months the note tells you what to re-check.
