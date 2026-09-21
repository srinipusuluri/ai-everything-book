"""
The lethal trifecta, as a static analyzer instead of a diagram-reading exercise.

notes/02 section 2 gives a three-question decision framework for spotting the
lethal trifecta (untrusted input + sensitive data access + external communication,
all reachable by one agent, with no gate) in an architecture diagram:

    1. Does this node ingest content from a source not fully controlled by you?
    2. Does this node have a live credential/connection that reaches confidential data?
    3. Does this node have a tool that causes an external effect a human does not
       have to approve first?

This script turns that checklist into code. You declare each TOOL once, tagged with
the three booleans the checklist asks about. You declare each AGENT as a name plus
the list of tools it can reach (optionally marking a tool as gated behind human
approval, which neutralizes leg 3 per the checklist's own wording: "...that a human
does NOT have to approve first"). The analyzer unions the tags across an agent's
reachable tools -- exactly the "walk every node, ask three yes/no questions" method
-- and flags any agent where all three answers come back yes.

This is a teaching tool, not a security scanner: it only knows what you tell it in
the declarative TOOLS/AGENTS data below. A real system's tool doesn't announce
"reads_untrusted_content=True" -- you have to make that judgment call yourself, the
same way you'd read an architecture diagram. What the script buys you is *forcing*
that judgment call to be made explicitly, per tool, and refusing to let a trifecta
hide across three tools nobody looked at together.

Run:
    /Users/srinip/ai-all/.venv/bin/python code/lethal_trifecta_analyzer.py

Requires: nothing outside the Python standard library.
"""
from __future__ import annotations

from dataclasses import dataclass, field


def rule(title: str) -> None:
    print("\n" + "=" * 78 + f"\n{title}\n" + "=" * 78)


# --------------------------------------------------------------------------- #
# 1. Declare tools -- the three tags are the entire checklist from notes/02   #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Tool:
    name: str
    reads_untrusted_content: bool
    accesses_sensitive_data: bool
    can_communicate_externally: bool
    description: str


TOOLS: dict[str, Tool] = {
    t.name: t for t in [
        Tool("web_search", True, False, False,
             "Searches the open web. Results are third-party content -- untrusted."),
        Tool("summarize_text", False, False, False,
             "Pure text transform, no I/O of its own."),
        Tool("get_own_account_balance", False, True, False,
             "Reads the CURRENT authenticated user's own balance from an internal DB."),
        Tool("reply_to_current_user", False, False, False,
             "Renders text back to the same user who is already in this conversation "
             "-- not 'external communication' in the risky sense (notes/02 section 2: "
             "'the communication is just rendering to the user who already has "
             "legitimate access to that data')."),
        Tool("read_inbound_email", True, False, False,
             "Reads email FROM ANYONE who emails the shared inbox -- untrusted content."),
        Tool("search_crm", False, True, False,
             "Live connection to the CRM: customer PII, deal notes, internal data."),
        Tool("send_email", False, False, True,
             "Sends email to an arbitrary address -- external, effectful, irreversible."),
        Tool("read_github_issue", True, False, False,
             "Reads issue bodies filed by any GitHub user -- untrusted content."),
        Tool("read_secrets_manager", False, True, False,
             "Reads API keys / credentials from the secrets manager."),
        Tool("post_to_slack", False, False, True,
             "Posts a message to an arbitrary Slack channel -- external, effectful."),
        Tool("produce_structured_summary", False, False, False,
             "Emits a schema-constrained (title, tags, priority) record -- no free "
             "text, no tool access, no sensitive data. The designed 'narrow handoff' "
             "output of a split-agent pattern (notes/02 section 2, fix #1)."),
    ]
}


# --------------------------------------------------------------------------- #
# 2. Declare agents -- a name, a description, and the tools it can reach     #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ToolGrant:
    tool_name: str
    human_approval_required: bool = False   # neutralizes leg 3 for THIS tool if True


@dataclass(frozen=True)
class AgentConfig:
    name: str
    description: str
    grants: tuple[ToolGrant, ...]


AGENTS: list[AgentConfig] = [
    AgentConfig(
        name="web_research_assistant",
        description="Answers questions by searching the web and summarizing results.",
        grants=(
            ToolGrant("web_search"),
            ToolGrant("summarize_text"),
        ),
    ),
    AgentConfig(
        name="customer_account_assistant",
        description="Lets a logged-in customer ask about their own account balance.",
        grants=(
            ToolGrant("get_own_account_balance"),
            ToolGrant("reply_to_current_user"),
        ),
    ),
    AgentConfig(
        name="inbox_triage_agent_v1",
        description="Reads inbound support email, looks up the customer in the CRM, "
                     "and emails a reply -- fully autonomous, no gate.",
        grants=(
            ToolGrant("read_inbound_email"),
            ToolGrant("search_crm"),
            ToolGrant("send_email"),                       # <- ungated
        ),
    ),
    AgentConfig(
        name="inbox_triage_agent_v2_gated",
        description="Same as v1, but every outbound send requires a human to click "
                     "approve first -- the notes/02 section 2 fix #2 applied.",
        grants=(
            ToolGrant("read_inbound_email"),
            ToolGrant("search_crm"),
            ToolGrant("send_email", human_approval_required=True),   # <- gated
        ),
    ),
    AgentConfig(
        name="devops_mcp_agent",
        description="Reads GitHub issues, has secrets-manager access for deploy "
                     "credentials, and posts status to Slack -- the exact shape "
                     "Module 16's Claude Code notes describe as '.env + WebFetch + "
                     "Bash, all three at once.'",
        grants=(
            ToolGrant("read_github_issue"),
            ToolGrant("read_secrets_manager"),
            ToolGrant("post_to_slack"),                     # <- ungated
        ),
    ),
    AgentConfig(
        name="devops_reader_agent (split, half 1 of 2)",
        description="Reads GitHub issues and emits ONLY a schema-constrained "
                     "summary. No secrets access, no communication tool -- fix #1 "
                     "from notes/02 section 2 applied to devops_mcp_agent above.",
        grants=(
            ToolGrant("read_github_issue"),
            ToolGrant("produce_structured_summary"),
        ),
    ),
    AgentConfig(
        name="devops_action_agent (split, half 2 of 2)",
        description="Consumes ONLY the structured summary from the reader agent "
                     "above (never raw issue text), holds the secrets access and "
                     "the Slack tool. Has nowhere for an injected instruction to "
                     "travel, because its input is a schema, not free text.",
        grants=(
            ToolGrant("read_secrets_manager"),
            ToolGrant("post_to_slack"),
        ),
    ),
]


# --------------------------------------------------------------------------- #
# 3. The analyzer -- literally the three-question checklist, unioned          #
# --------------------------------------------------------------------------- #
@dataclass
class LegFinding:
    present: bool
    contributing_tools: list[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    agent_name: str
    untrusted_input: LegFinding
    sensitive_data: LegFinding
    external_comm_ungated: LegFinding
    gated_external_tools: list[str]
    flagged: bool


def analyze_agent(agent: AgentConfig, registry: dict[str, Tool]) -> AnalysisResult:
    untrusted = LegFinding(False)
    sensitive = LegFinding(False)
    comm_ungated = LegFinding(False)
    gated_comm_tools: list[str] = []

    for grant in agent.grants:
        tool = registry[grant.tool_name]
        if tool.reads_untrusted_content:
            untrusted.present = True
            untrusted.contributing_tools.append(tool.name)
        if tool.accesses_sensitive_data:
            sensitive.present = True
            sensitive.contributing_tools.append(tool.name)
        if tool.can_communicate_externally:
            if grant.human_approval_required:
                gated_comm_tools.append(tool.name)
            else:
                comm_ungated.present = True
                comm_ungated.contributing_tools.append(tool.name)

    flagged = untrusted.present and sensitive.present and comm_ungated.present
    return AnalysisResult(agent.name, untrusted, sensitive, comm_ungated, gated_comm_tools, flagged)


def suggest_mitigations(agent: AgentConfig, result: AnalysisResult) -> list[str]:
    """Mirror notes/02 section 2's three fixes, in the same order of preference,
    made concrete with the actual tool names that triggered the flag."""
    if not result.flagged:
        return []
    comm_tools = ", ".join(result.external_comm_ungated.contributing_tools)
    untrusted_tools = ", ".join(result.untrusted_input.contributing_tools)
    sensitive_tools = ", ".join(result.sensitive_data.contributing_tools)
    return [
        f"SPLIT: move {{{untrusted_tools}}} into a read-only agent that emits a "
        f"schema-constrained summary (no free text, no tool access); have a second "
        f"agent hold {{{sensitive_tools}}} and {{{comm_tools}}} and consume ONLY "
        f"that structured output, never the raw untrusted content.",
        f"GATE: require human approval before any of {{{comm_tools}}} fires -- "
        f"converts 'the model did something' into 'a named person authorized this'.",
        f"REMOVE: does this agent actually need {{{comm_tools}}}, or would returning "
        f"a draft for a human to send satisfy the real requirement?",
    ]


# --------------------------------------------------------------------------- #
# 4. Run it                                                                    #
# --------------------------------------------------------------------------- #
def main() -> None:
    rule(f"LETHAL TRIFECTA STATIC ANALYZER -- {len(AGENTS)} example agent configurations")
    print("Checklist (notes/02 section 2), applied per agent by unioning its tools' tags:")
    print("  1. untrusted input?        2. sensitive data access?    3. ungated external comm?")
    print("  All three 'yes' on the SAME agent = lethal trifecta.\n")

    flagged_count = 0
    for agent in AGENTS:
        result = analyze_agent(agent, TOOLS)
        flagged_count += result.flagged

        rule(f"AGENT: {agent.name}")
        print(f"  {agent.description}")
        print(f"  tools granted: {[g.tool_name for g in agent.grants]}\n")

        def leg_line(label: str, finding: LegFinding) -> str:
            yn = "YES" if finding.present else "no"
            via = f"  (via: {', '.join(finding.contributing_tools)})" if finding.contributing_tools else ""
            return f"    [{yn:>3}] {label}{via}"

        print(leg_line("reads untrusted content", result.untrusted_input))
        print(leg_line("accesses sensitive data", result.sensitive_data))
        print(leg_line("ungated external communication", result.external_comm_ungated))
        if result.gated_external_tools:
            print(f"    (note: {', '.join(result.gated_external_tools)} can communicate "
                  f"externally but requires human approval -- does not count toward leg 3)")

        verdict = "*** LETHAL TRIFECTA FLAGGED ***" if result.flagged else "safe -- at most two legs present"
        print(f"\n  VERDICT: {verdict}")

        for suggestion in suggest_mitigations(agent, result):
            print(f"    -> {suggestion}")

    rule("SUMMARY")
    print(f"  {flagged_count} of {len(AGENTS)} agent configurations flagged.\n")
    name_w = max(len(a.name) for a in AGENTS) + 2
    print(f"  {'agent':<{name_w}}{'untrusted':<12}{'sensitive':<12}{'ext.comm':<12}{'verdict'}")
    for agent in AGENTS:
        r = analyze_agent(agent, TOOLS)
        print(f"  {agent.name:<{name_w}}"
              f"{'yes' if r.untrusted_input.present else 'no':<12}"
              f"{'yes' if r.sensitive_data.present else 'no':<12}"
              f"{'yes' if r.external_comm_ungated.present else 'no':<12}"
              f"{'FLAGGED' if r.flagged else 'safe'}")

    rule("WHY THE PAIRED CONFIGS MATTER")
    print("""
  inbox_triage_agent_v1 and inbox_triage_agent_v2_gated grant the IDENTICAL three
  tools. The only difference is one boolean: human_approval_required on send_email.
  That single flag is the entire difference between "lethal trifecta" and "safe."
  This is deliberate -- it is the clearest illustration in this module that the
  trifecta is a property of the ARCHITECTURE (is the third leg gated or not), not
  of which tools exist in the abstract. Compare their two blocks above directly.

  Also note what did NOT get flagged: web_research_assistant has untrusted input
  and nothing else (no sensitive data, nowhere consequential to send it -- fine,
  per notes/02 section 2's own example). customer_account_assistant has sensitive
  data access and nothing else, because reply_to_current_user renders back to the
  same authenticated user who already owns that data -- not external communication
  in the risky sense. Both are correctly-scoped agents, not accidentally-safe ones.

  devops_reader_agent and devops_action_agent are the SPLIT fix (notes/02 section 2,
  fix #1) applied to devops_mcp_agent: the same three capabilities exist somewhere
  in the system, but no single agent holds all three anymore. The reader agent has
  untrusted input and nothing else; the action agent has sensitive data and comms
  and nothing else. An injected instruction in a GitHub issue has no path to the
  secrets manager or Slack, because the only thing that crosses the boundary is a
  structured summary, not the raw text the attacker controlled.
""")

    rule("WHAT THIS ANALYZER DOES NOT DO -- an honest limitation")
    print("""
  This script is exactly as good as the tags you assign it. It cannot discover, on
  its own, that a tool you marked accesses_sensitive_data=False actually has read
  access to a database with a customer table joined in "just in case" -- that
  judgment call is still yours, the same way reading the architecture diagram by
  eye was in notes/02 before this script existed. Treat this as a forcing function
  that makes you write the judgment down per tool, not a proof that a system tagged
  correctly here is safe against a threat model this analyzer was never told about.
""")


if __name__ == "__main__":
    main()
