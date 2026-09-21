# 🔗 Resources — AI on AWS with Amazon Bedrock

Real URLs only. Anything undated should be assumed stale until you check it
against [`docs.aws.amazon.com`](https://docs.aws.amazon.com/bedrock/).

---

## Official documentation (start here)

| Doc | What it is |
|---|---|
| [Amazon Bedrock User Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/) | The main guide. Concepts, features, walkthroughs. |
| [Amazon Bedrock API Reference](https://docs.aws.amazon.com/bedrock/latest/APIReference/) | The JSON shapes. `Converse`, `ConverseStream`, `ContentBlock`, `TokenUsage` — where you settle arguments. |
| [Amazon Bedrock AgentCore Developer Guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/) | The current agent platform. Runtime, Gateway, Memory, Identity, Policy. |
| [Amazon Bedrock pricing](https://aws.amazon.com/bedrock/pricing/) | The only place to get rates. |
| [Service Quotas for Bedrock](https://docs.aws.amazon.com/general/latest/gr/bedrock.html) | Endpoints and default quotas per Region. |
| [Service Authorization Reference — Bedrock](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonbedrock.html) | Every IAM action, resource type and condition key. Use it when writing least-privilege policies. |
| [AWS Well-Architected Generative AI Lens](https://docs.aws.amazon.com/wellarchitected/latest/generative-ai-lens/generative-ai-lens.html) | AWS's architectural opinion, mapped to the six pillars. |
| [Boto3 bedrock-runtime reference](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime.html) | Python method signatures for `converse`, `converse_stream`, `apply_guardrail`. |
| [Boto3 bedrock-agent-runtime reference](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agent-runtime.html) | `retrieve`, `retrieve_and_generate`, and the agent runtime calls. |

---

## Repositories worth cloning

| Repo | What's inside |
|---|---|
| https://github.com/aws-samples/amazon-bedrock-workshop | The official hands-on workshop. Notebooks for Converse, tool use, Knowledge Bases, Guardrails. The fastest path from reading to running. |
| https://github.com/awsdocs/aws-doc-sdk-examples | Canonical SDK examples across languages. `python/example_code/bedrock-runtime/` is the one you want; these are the snippets the docs embed. |
| https://github.com/aws-samples/amazon-bedrock-samples | Broader sample collection — RAG patterns, agents, evaluation, fine-tuning. Quality varies by folder; check commit dates. |
| https://github.com/aws-samples/generative-ai-cdk-constructs | L3 CDK constructs for Bedrock Knowledge Bases, agents and guardrails. The fastest way to get RAG infrastructure into IaC. |
| https://github.com/strands-agents/sdk-python | Strands Agents — AWS's open-source agent framework, a first-class citizen on AgentCore Runtime. |
| https://github.com/hashicorp/terraform-provider-aws | Check `website/docs/r/bedrock*` for which Bedrock resources are actually covered before you plan a Terraform module. |
| https://github.com/boto/boto3 | When a parameter is not documented, the service model JSON in botocore is ground truth. |
| https://github.com/modelcontextprotocol/servers | Reference MCP servers. Relevant because AgentCore Gateway speaks MCP. |

---

## Courses and structured learning

| Course | Who it's for | Link |
|---|---|---|
| **AWS Skill Builder — Generative AI learning plans** | Free digital courses, including Bedrock-specific paths | https://skillbuilder.aws/ |
| **Amazon Bedrock Workshop** (self-paced, official) | The hands-on companion to this track | https://catalog.workshops.aws/ |
| **AWS Certified AI Practitioner (AIF-C01)** | If you need the credential; heavy on Bedrock vocabulary | https://aws.amazon.com/certification/certified-ai-practitioner/ |
| **AWS Certified Machine Learning Engineer – Associate (MLA-C01)** | The SageMaker-side certification; useful for the Bedrock-vs-SageMaker boundary | https://aws.amazon.com/certification/certified-machine-learning-engineer-associate/ |
| **DeepLearning.AI — Serverless LLM apps with Amazon Bedrock** | Short, free, practical | https://www.deeplearning.ai/short-courses/ |

---

## Blogs and ongoing sources

| Source | Why follow it |
|---|---|
| [AWS Machine Learning Blog](https://aws.amazon.com/blogs/machine-learning/) | Where new Bedrock capabilities get explained with code, usually a day after launch. |
| [What's New with AWS — Bedrock filter](https://aws.amazon.com/about-aws/whats-new/machine-learning/) | The changelog. Skim weekly; it is how you learn a model was deprecated. |
| [AWS Architecture Blog](https://aws.amazon.com/blogs/architecture/) | Reference architectures, occasionally including honest post-mortems. |
| [Amazon Builders' Library](https://aws.amazon.com/builders-library/) | Not Bedrock-specific and better for it. The retry, timeout and load-shedding articles are the intellectual basis for §3 of the production-craft note. |
| [AWS re:Post — Amazon Bedrock](https://repost.aws/tags/TAWTLWvsLoQZOgRLuWD5r0zA/amazon-bedrock) | Where the errors nobody documented get answered. Search it before opening a support case. |
| [AWS Service Terms](https://aws.amazon.com/service-terms/) and [third-party model licences](https://aws.amazon.com/legal/bedrock/third-party-models/) | The actual legal text your compliance team will ask for. |

---

## Communities

| Where | Notes |
|---|---|
| [AWS re:Post](https://repost.aws/) | Official Q&A; AWS staff answer. Higher signal than Stack Overflow for service behaviour. |
| [r/aws](https://www.reddit.com/r/aws/) | Good for "is this broken for everyone?" Poor for correctness. |
| [AWS Community (community.aws)](https://community.aws/) | Builder-written content; the Converse API developer guides for Java and JavaScript linked from the official docs live here. |
| [MCP community](https://modelcontextprotocol.io/) | For the AgentCore Gateway side of agent work. |

---

## Tooling

| Tool | Use |
|---|---|
| [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) | `aws bedrock list-foundation-models`, `list-inference-profiles`, `get-foundation-model-availability`. Ground truth for what your account can actually call. |
| [IAM Access Analyzer policy validation](https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-policy-validation.html) | Run every policy in this track through it before deploying. |
| [AWS Cost Explorer](https://aws.amazon.com/aws-cost-management/aws-cost-explorer/) + [Budgets](https://aws.amazon.com/aws-cost-management/aws-budgets/) | Set the budget alarm before the first live call, not after the first surprise. |
| [CloudWatch Logs Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AnalyzingLogData.html) | Querying model invocation logs; see the `identity.arn` attribution query in the code folder. |
| [LiteLLM](https://github.com/BerriAI/litellm) | If you must abstract over Bedrock *and* other providers. Understand Converse first — an abstraction over an abstraction you do not understand is how you end up unable to debug anything. |
| [LangChain `ChatBedrockConverse`](https://python.langchain.com/docs/integrations/chat/bedrock/) | The LangChain binding that uses Converse rather than per-provider bodies. See the [LangChain track](../../langchain/) in this module. |

---

## Sibling tracks in Module 16

| Track | Relationship |
|---|---|
| [LangChain](../../langchain/) | `ChatBedrockConverse` is the adapter; same tool-call semantics, different ergonomics |
| [LangGraph](../../langgraph/) | Runs well on AgentCore Runtime; the graph is your loop |
| [LangSmith](../../langsmith/) | Tracing alternative to CloudWatch + X-Ray for LLM-shaped spans |
| [Python](../../python/) / [TypeScript](../../typescript/) | The SDK ergonomics underneath all of this |
