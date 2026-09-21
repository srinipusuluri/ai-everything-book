"""
Hand-off information loss: a concrete, measurable demonstration.

The scenario: a triage agent reads a customer support ticket and produces a
rich internal trace of everything it noticed. It then hands off to a
resolution agent -- but not with the full trace, because that's how hand-offs
actually work in production (you summarize, you don't paste the whole
transcript into every downstream agent's context forever). The hand-off
summary is a deterministic "lossy compression" step: truncate to the first
N characters, or extract keywords, the way a cheap summarizer or an
over-eager prompt ("summarize this in 2 sentences") actually behaves.

The critical detail -- the customer already tried the standard fix, so the
resolution agent's default first move will waste the customer's time again --
is buried in paragraph 3 of the ticket. A good hand-off keeps it. A lossy
one drops it. We measure the downstream agent's decision quality with and
without that detail to make the cost of the summary concrete rather than
asserted.

    python code/handoff_information_loss.py

Requires: nothing beyond the Python standard library.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# --------------------------------------------------------------------------- #
# The ticket. Read it once, the way a human triage agent would. Notice        #
# where the critical fact lives: paragraph 3, not the opening or closing.     #
# --------------------------------------------------------------------------- #
TICKET = """\
Subject: App keeps logging me out every few minutes

Paragraph 1: Hi, I'm having a really frustrating issue with the mobile app.
Every few minutes it just logs me out completely and I have to sign back in
with my password, which is extremely annoying especially when I'm in the
middle of filling out a long form.

Paragraph 2: This started about a week ago, right around when I updated to
version 4.2 of the app. Before that it worked fine for months. I'm on an
iPhone 14 running the latest iOS.

Paragraph 3: I already tried the standard fix from your help center --
uninstalling and reinstalling the app, and also clearing the app's cache
from the phone's settings menu. Neither one helped at all, the problem
came right back within a few minutes of signing in again.

Paragraph 4: I've been a customer for 3 years and this is the first real
problem I've had. I'd really appreciate a fix soon since I use this app for
work every day and the constant re-logins are killing my productivity.

Paragraph 5: Let me know if you need any more information from my end,
happy to help however I can to get this sorted out quickly.
"""

CRITICAL_FACT = "already tried the standard fix"
STANDARD_FIRST_MOVE = "reinstall the app and clear cache"


# --------------------------------------------------------------------------- #
# Two deterministic "lossy compression" hand-off strategies, standing in for  #
# what a real hand-off summarizer does: truncate, or extract keywords.       #
# Neither one is malicious -- both are exactly what a reasonable, cheap      #
# summarization prompt produces under a length budget.                       #
# --------------------------------------------------------------------------- #
def truncate_handoff(ticket: str, char_budget: int) -> str:
    """The laziest possible hand-off: keep the first N characters.
    Models real behavior: 'summarize the customer's issue' with no
    instruction to scan the whole ticket first can behave exactly like this
    when the model front-loads its summary from what it read first."""
    return ticket[:char_budget].rstrip() + " [...truncated...]"


KEYWORDS = ["logout", "logs me out", "version 4.2", "iPhone", "iOS", "frustrat",
            "3 years", "productivity", "form"]


def keyword_handoff(ticket: str, keywords: list[str]) -> str:
    """A 'smarter' hand-off: pull out sentences containing known keywords.
    Still lossy -- it only keeps what someone THOUGHT to list as a keyword,
    and nobody listed 'already tried' or 'reinstall' because the keyword
    list was built from the SYMPTOM, not from the customer's own diagnostic
    history. This is exactly how real keyword/entity-extraction hand-offs
    fail: they compress toward what the summarizer expected to matter."""
    sentences = re.split(r"(?<=[.!?])\s+", ticket.replace("\n", " "))
    kept = [s for s in sentences if any(k.lower() in s.lower() for k in keywords)]
    return " ".join(kept)


def full_handoff(ticket: str) -> str:
    """The expensive but lossless option: hand off the whole ticket verbatim.
    This is what context isolation asks you to give up in exchange for a
    clean context window -- see notes/02 section 1."""
    return ticket


# --------------------------------------------------------------------------- #
# The downstream "resolution agent". It is deliberately simple and           #
# deterministic: IF it can see the critical fact in what it was handed, it   #
# skips the standard first move and escalates directly. IF it cannot see    #
# the critical fact, it defaults to the standard first move -- which the    #
# customer explicitly already tried and told us didn't work.                #
# --------------------------------------------------------------------------- #
@dataclass
class Decision:
    action: str
    correct: bool
    reasoning: str


def resolution_agent(handoff_text: str) -> Decision:
    if CRITICAL_FACT in handoff_text or "reinstall" in handoff_text.lower():
        return Decision(
            action="Escalate directly to engineering with logs (skip standard fix)",
            correct=True,
            reasoning="Hand-off preserved that the customer already tried the standard fix.",
        )
    return Decision(
        action=f"Reply with standard first move: '{STANDARD_FIRST_MOVE}'",
        correct=False,
        reasoning="Hand-off did not mention prior troubleshooting; agent defaults to step 1, "
                  "which the customer already did and reported as ineffective. "
                  "Customer receives an answer that wastes their time a second time.",
    )


# --------------------------------------------------------------------------- #
# Demo                                                                        #
# --------------------------------------------------------------------------- #
def rule(t: str) -> None:
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


def show_handoff(name: str, text: str, char_budget_note: str = "") -> Decision:
    print(f"\n  --- hand-off produced by: {name} {char_budget_note}---")
    preview = text if len(text) <= 260 else text[:260] + " [...]"
    print(f"  {preview!r}")
    print(f"  ({len(text)} chars, vs. {len(TICKET)} chars in the original ticket "
          f"-- {len(text) / len(TICKET):.0%} retained)")
    decision = resolution_agent(text)
    verdict = "CORRECT" if decision.correct else "WRONG -- repeats a step the customer already tried"
    print(f"  downstream agent decision: {decision.action}")
    print(f"  verdict: {verdict}")
    print(f"  why: {decision.reasoning}")
    return decision


def main() -> None:
    rule("THE TICKET (what the triage agent actually read, in full)")
    print(TICKET)
    print(f"  Critical detail lives in paragraph 3: the customer already tried")
    print(f"  the standard fix. A good hand-off preserves this. Watch what happens")
    print(f"  when it doesn't.")

    rule("HAND-OFF STRATEGY 1: TRUNCATE TO A CHARACTER BUDGET")
    print("  Models a hand-off summarizer with a hard length limit that front-loads")
    print("  from the start of the document -- exactly what happens when a prompt says")
    print("  'summarize in a few sentences' with no instruction to scan for buried facts.")
    for budget in (200, 450, 700):
        text = truncate_handoff(TICKET, budget)
        show_handoff(f"truncate({budget} chars)", text, f"[budget={budget}] ")

    rule("HAND-OFF STRATEGY 2: KEYWORD EXTRACTION")
    print("  Models a 'smarter' extractive summarizer that pulls sentences containing")
    print("  pre-defined keywords. Still lossy: the keyword list was built from the")
    print("  SYMPTOM (logout, version, device) -- nobody thought to list 'already tried'")
    print("  or 'reinstall', because those words describe the customer's diagnostic")
    print("  history, not the bug report itself.")
    kw_text = keyword_handoff(TICKET, KEYWORDS)
    show_handoff("keyword-extraction", kw_text)

    rule("HAND-OFF STRATEGY 3: FULL TICKET, VERBATIM (the expensive baseline)")
    print("  What you'd get if you paid the token cost of context isolation's opposite:")
    print("  no compression at all. This is the 'right answer' every lossy strategy")
    print("  above is being compared against.")
    show_handoff("full ticket", full_handoff(TICKET))

    rule("SIDE-BY-SIDE: DECISION QUALITY vs. INFORMATION RETAINED")
    strategies = [
        ("truncate(200)", truncate_handoff(TICKET, 200)),
        ("truncate(450)", truncate_handoff(TICKET, 450)),
        ("truncate(700)", truncate_handoff(TICKET, 700)),
        ("keyword-extraction", kw_text),
        ("full ticket", full_handoff(TICKET)),
    ]
    print(f"  {'strategy':<20} {'chars kept':>10} {'% of original':>14} {'decision correct?':>18}")
    print("  " + "-" * 66)
    for name, text in strategies:
        d = resolution_agent(text)
        pct = len(text) / len(TICKET)
        print(f"  {name:<20} {len(text):>10} {pct:>13.0%} {str(d.correct):>18}")

    rule("THE LESSON")
    print("  The critical fact was ONE clause in a five-paragraph ticket. Two out of")
    print("  three truncation budgets and the keyword extractor all dropped it, and")
    print("  the downstream agent's decision quality degraded EXACTLY where it was")
    print("  dropped -- not gradually, but as a hard flip from correct to wrong the")
    print("  moment the clause fell outside the summary.")
    print("")
    print("  This is not a summarization-quality problem you fix with a better prompt.")
    print("  It is structural: any hand-off that compresses information can silently")
    print("  drop the one detail that determines the right next action, and neither")
    print("  the summarizing agent nor the receiving agent has a way to know it")
    print("  happened -- the receiving agent doesn't know what it wasn't told.")
    print("  See notes/02 section 3 ('information loss in summarized hand-offs') and")
    print("  section 1's context-isolation trade-off: this is the cost side of that")
    print("  trade, made concrete.")


if __name__ == "__main__":
    main()
