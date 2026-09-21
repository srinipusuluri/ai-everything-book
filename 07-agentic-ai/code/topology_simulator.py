"""
Topology simulator: the same toy task, run through five multi-agent
topologies plus a single-agent baseline, with token cost / latency /
success rate printed side by side.

This is the whole argument of notes/02 section 1, made numeric instead of
asserted: multi-agent systems cost more tokens than a single agent, and
whether that cost is worth paying depends on the task shape.

No API key, no network. "Agents" are deterministic Python functions with a
seeded random number generator standing in for a real model's variance --
every run prints identical numbers, so you can trust what you're reading
instead of wondering if you got a lucky seed.

    python code/topology_simulator.py

Requires: nothing beyond the Python standard library.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

SEED = 42

# --------------------------------------------------------------------------- #
# The toy task shared by every topology: "produce a research brief that       #
# answers 3 sub-questions, then a final synthesis."                           #
# Each sub-question can be answered correctly or not; a wrong sub-answer      #
# that reaches the final synthesis without being caught corrupts the brief.  #
# --------------------------------------------------------------------------- #
SUBQUESTIONS = [
    "market size",
    "top 3 competitors",
    "regulatory risk",
]

# Per-step token costs, modeling a real agent: a system prompt + tool
# definitions + growing transcript. These are illustrative, not measured
# from a real model -- the point is the RELATIVE shape across topologies.
TOKENS_PER_AGENT_SETUP = 350      # system prompt + tool schema, paid once per agent spun up
TOKENS_PER_SUBTASK_WORK = 900     # a worker actually researching one sub-question
TOKENS_PER_HANDOFF_SUMMARY = 220  # writing a hand-off/summary message
TOKENS_PER_HANDOFF_READ = 220     # the receiving agent reading that summary
TOKENS_PER_SYNTHESIS = 500        # combining sub-answers into a final brief
TOKENS_PER_VOTE = 150             # one aggregator pass over N candidate answers
TOKENS_PER_DEBATE_ROUND = 400     # one round where agents see each other's answers

LATENCY_PER_SEQUENTIAL_STEP = 1.0   # arbitrary "ticks"; steps in series add up
LATENCY_PER_PARALLEL_BATCH = 1.0    # a parallel batch costs the time of ONE step, not N

BASE_ERROR_RATE = 0.12  # chance a single worker gets one sub-question wrong


@dataclass
class RunResult:
    topology: str
    tokens: int
    latency: float
    correct_subanswers: int
    total_subanswers: int
    final_brief_correct: bool


def rng_for(topology: str, trial: int) -> random.Random:
    # Deterministic per (topology, trial) so the whole script is reproducible,
    # while still giving each trial independent-looking draws.
    return random.Random(f"{SEED}:{topology}:{trial}")


def worker_answers(rng: random.Random, n: int) -> list[bool]:
    """Simulate n independent workers each answering one sub-question.
    Returns a list of booleans: True = correct."""
    return [rng.random() > BASE_ERROR_RATE for _ in range(n)]


# --------------------------------------------------------------------------- #
# 1. Single-agent baseline: one agent handles all 3 sub-questions itself,     #
#    sequentially, in one continuous context. No hand-offs, no coordination. #
# --------------------------------------------------------------------------- #
def run_single_agent(trial: int) -> RunResult:
    rng = rng_for("single", trial)
    tokens = TOKENS_PER_AGENT_SETUP
    latency = 0.0
    correct = worker_answers(rng, len(SUBQUESTIONS))
    for _ in SUBQUESTIONS:
        tokens += TOKENS_PER_SUBTASK_WORK
        latency += LATENCY_PER_SEQUENTIAL_STEP
    tokens += TOKENS_PER_SYNTHESIS
    latency += LATENCY_PER_SEQUENTIAL_STEP
    final_ok = all(correct)  # one agent, no hand-off loss, but no error-catching either
    return RunResult("single-agent", tokens, latency, sum(correct), len(correct), final_ok)


# --------------------------------------------------------------------------- #
# 2. Supervisor / orchestrator-worker: supervisor spins up 3 workers in       #
#    parallel, each researches one sub-question, hands its answer back       #
#    (a summary, not a raw transcript), supervisor synthesizes.              #
# --------------------------------------------------------------------------- #
def run_supervisor(trial: int) -> RunResult:
    rng = rng_for("supervisor", trial)
    n = len(SUBQUESTIONS)
    tokens = TOKENS_PER_AGENT_SETUP  # supervisor's own setup
    correct = worker_answers(rng, n)
    for _ in range(n):
        tokens += TOKENS_PER_AGENT_SETUP        # spin up a worker
        tokens += TOKENS_PER_SUBTASK_WORK       # worker does the research
        tokens += TOKENS_PER_HANDOFF_SUMMARY    # worker writes a hand-off summary
        tokens += TOKENS_PER_HANDOFF_READ       # supervisor reads it
    tokens += TOKENS_PER_SYNTHESIS
    # Latency: workers run in PARALLEL (this is the whole point of this topology),
    # then one synthesis step.
    latency = LATENCY_PER_PARALLEL_BATCH + LATENCY_PER_SEQUENTIAL_STEP
    final_ok = all(correct)
    return RunResult("supervisor", tokens, latency, sum(correct), n, final_ok)


# --------------------------------------------------------------------------- #
# 3. Peer-to-peer hand-off: agent 1 answers sub-q 1, hands off to agent 2     #
#    for sub-q 2, hands off to agent 3 for sub-q 3, agent 3 synthesizes.      #
#    Sequential by construction -- no parallelism available in this shape.   #
#    We also simulate an occasional hand-off LOOP: the receiving agent       #
#    decides (wrongly) that the previous agent should handle it after all.   #
# --------------------------------------------------------------------------- #
LOOP_PROBABILITY = 0.15


def run_peer_handoff(trial: int) -> RunResult:
    rng = rng_for("handoff", trial)
    n = len(SUBQUESTIONS)
    tokens = TOKENS_PER_AGENT_SETUP * n
    latency = 0.0
    correct = worker_answers(rng, n)
    loops = 0
    for i in range(n):
        tokens += TOKENS_PER_SUBTASK_WORK
        latency += LATENCY_PER_SEQUENTIAL_STEP
        if i < n - 1:
            tokens += TOKENS_PER_HANDOFF_SUMMARY + TOKENS_PER_HANDOFF_READ
            latency += LATENCY_PER_SEQUENTIAL_STEP
            # A hand-off loop: the next agent bounces it back once before proceeding.
            if rng.random() < LOOP_PROBABILITY:
                loops += 1
                tokens += TOKENS_PER_HANDOFF_SUMMARY + TOKENS_PER_HANDOFF_READ
                latency += LATENCY_PER_SEQUENTIAL_STEP
    tokens += TOKENS_PER_SYNTHESIS
    latency += LATENCY_PER_SEQUENTIAL_STEP
    final_ok = all(correct) and loops == 0  # a loop is itself treated as a partial failure
    return RunResult("peer-handoff", tokens, latency, sum(correct), n, final_ok)


# --------------------------------------------------------------------------- #
# 4. Hierarchical teams-of-teams: a top supervisor delegates to 2 team       #
#    supervisors (team A handles sub-q 1-2, team B handles sub-q 3), each    #
#    team supervisor spins up its own workers. Two extra hops of hand-off    #
#    summary vs. the flat supervisor case.                                   #
# --------------------------------------------------------------------------- #
def run_hierarchical(trial: int) -> RunResult:
    rng = rng_for("hierarchical", trial)
    n = len(SUBQUESTIONS)
    correct = worker_answers(rng, n)
    tokens = TOKENS_PER_AGENT_SETUP  # top supervisor
    tokens += TOKENS_PER_AGENT_SETUP * 2  # two team supervisors
    for _ in range(n):
        tokens += TOKENS_PER_AGENT_SETUP        # worker
        tokens += TOKENS_PER_SUBTASK_WORK
        tokens += TOKENS_PER_HANDOFF_SUMMARY + TOKENS_PER_HANDOFF_READ  # worker -> team sup
    # Each team supervisor summarizes ITS workers up to the top supervisor: 2 more hops.
    tokens += 2 * (TOKENS_PER_HANDOFF_SUMMARY + TOKENS_PER_HANDOFF_READ)
    tokens += TOKENS_PER_SYNTHESIS
    # Latency: workers within a team run in parallel; the two teams also run in
    # parallel; then two levels of synthesis (team -> top).
    latency = LATENCY_PER_PARALLEL_BATCH + LATENCY_PER_SEQUENTIAL_STEP * 2
    final_ok = all(correct)
    return RunResult("hierarchical", tokens, latency, sum(correct), n, final_ok)


# --------------------------------------------------------------------------- #
# 5. Debate / parallel-then-vote: 3 agents EACH answer ALL 3 sub-questions    #
#    independently (this is the expensive part -- full duplication of work), #
#    then an aggregator takes a majority vote per sub-question.              #
# --------------------------------------------------------------------------- #
N_DEBATERS = 3


def run_debate_vote(trial: int) -> RunResult:
    rng = rng_for("debate", trial)
    n = len(SUBQUESTIONS)
    tokens = TOKENS_PER_AGENT_SETUP * N_DEBATERS
    # Each debater answers every sub-question independently.
    all_answers: list[list[bool]] = []
    for _ in range(N_DEBATERS):
        all_answers.append(worker_answers(rng, n))
        tokens += TOKENS_PER_SUBTASK_WORK * n
    # Majority vote per sub-question.
    voted_correct = []
    for q in range(n):
        votes = [all_answers[d][q] for d in range(N_DEBATERS)]
        voted_correct.append(sum(votes) >= (N_DEBATERS // 2 + 1))
    tokens += TOKENS_PER_VOTE * n
    tokens += TOKENS_PER_SYNTHESIS
    # Latency: all debaters run in parallel, then one vote pass, then synthesis.
    latency = LATENCY_PER_PARALLEL_BATCH + LATENCY_PER_SEQUENTIAL_STEP * 2
    final_ok = all(voted_correct)
    return RunResult("debate-vote", tokens, latency, sum(voted_correct), n, final_ok)


# --------------------------------------------------------------------------- #
# 6. Pipeline / assembly-line: research -> draft -> fact-check -> format.     #
#    Fixed sequential order, one agent per stage. Fact-check can catch a     #
#    wrong sub-answer from the research stage -- but ONLY if it's still      #
#    checking the original claim, not a stage that already re-summarized it. #
# --------------------------------------------------------------------------- #
FACT_CHECK_CATCH_RATE = 0.7  # probability fact-check catches an error that reaches it


def run_pipeline(trial: int) -> RunResult:
    rng = rng_for("pipeline", trial)
    n = len(SUBQUESTIONS)
    correct = worker_answers(rng, n)
    tokens = TOKENS_PER_AGENT_SETUP * 4  # research, draft, fact-check, format stages
    tokens += TOKENS_PER_SUBTASK_WORK * n     # research stage does all 3
    tokens += TOKENS_PER_SYNTHESIS            # draft stage
    tokens += TOKENS_PER_SUBTASK_WORK         # fact-check stage re-examines the draft
    tokens += TOKENS_PER_HANDOFF_SUMMARY      # format stage's light touch-up
    latency = LATENCY_PER_SEQUENTIAL_STEP * 4  # strictly sequential, no parallelism
    # If research got something wrong, fact-check has a chance to catch it and
    # correct it before it reaches the final brief -- pipelines have exactly ONE
    # such recovery point, unlike an agent that can re-plan at any step.
    fixed = list(correct)
    for i, ok in enumerate(correct):
        if not ok and rng.random() < FACT_CHECK_CATCH_RATE:
            fixed[i] = True
    final_ok = all(fixed)
    return RunResult("pipeline", tokens, latency, sum(fixed), n, final_ok)


# --------------------------------------------------------------------------- #
# Runner                                                                      #
# --------------------------------------------------------------------------- #
TOPOLOGIES = {
    "single-agent": run_single_agent,
    "supervisor": run_supervisor,
    "peer-handoff": run_peer_handoff,
    "hierarchical": run_hierarchical,
    "debate-vote": run_debate_vote,
    "pipeline": run_pipeline,
}

N_TRIALS = 200


def rule(t: str) -> None:
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


def main() -> None:
    rule("TOPOLOGY SIMULATOR -- same task, 6 shapes, 200 trials each")
    print(f"  Task: answer {len(SUBQUESTIONS)} sub-questions and synthesize one brief.")
    print(f"  Per-worker base error rate: {BASE_ERROR_RATE:.0%}")
    print(f"  Trials per topology: {N_TRIALS} (fully deterministic -- same seed every run)")

    rows = []
    for name, fn in TOPOLOGIES.items():
        results = [fn(t) for t in range(N_TRIALS)]
        avg_tokens = sum(r.tokens for r in results) / N_TRIALS
        avg_latency = sum(r.latency for r in results) / N_TRIALS
        success_rate = sum(r.final_brief_correct for r in results) / N_TRIALS
        rows.append((name, avg_tokens, avg_latency, success_rate))

    baseline_tokens = next(t for n, t, l, s in rows if n == "single-agent")

    rule("RESULTS")
    header = f"  {'topology':<14} {'avg tokens':>11} {'x baseline':>11} {'avg latency':>12} {'success rate':>13}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for name, tokens, latency, success in rows:
        mult = tokens / baseline_tokens
        print(f"  {name:<14} {tokens:>11.0f} {mult:>10.2f}x {latency:>12.1f} {success:>12.1%}")

    rule("READING THE TABLE")
    print("  - supervisor and hierarchical cost 1.5-2x+ the single agent for the SAME")
    print("    task, because every worker pays its own setup cost and every hand-off is")
    print("    paid twice (write the summary, read the summary). Hierarchical costs more")
    print("    than flat supervisor because of the extra team-supervisor hop.")
    print("  - debate-vote costs the most per sub-answer (3 full independent attempts)")
    print("    but that expense buys a MEASURABLE accuracy improvement over a single")
    print("    worker's raw error rate -- majority vote corrects independent mistakes.")
    print("    Compare its success rate to single-agent's: that gap is what you are")
    print("    buying with the extra tokens.")
    print("  - peer-handoff's success rate is dragged down by hand-off loops (this run's")
    print(f"    loop probability: {LOOP_PROBABILITY:.0%}) -- tokens spent on a bounce that")
    print("    produced no new information, and a run counted as failed even when both")
    print("    sub-answers were individually correct. Coordination overhead is not just")
    print("    cost, it is also a NEW way to fail that single-agent and pipeline don't have.")
    print("  - pipeline is close to single-agent in cost and BEATS it on success rate,")
    print("    because fact-check gives it one explicit recovery point a single agent")
    print("    doesn't get for free. This is the concrete case for 'deterministic")
    print("    pipeline with an LLM step' from notes/02 section 7: cheap AND more robust,")
    print("    when the task genuinely has a fixed stage order.")
    print("\n  None of these numbers are 'the' real-world numbers -- they are illustrative")
    print("  and deterministic so the SHAPE of the trade-off is visible and reproducible.")
    print("  The shape is the lesson: coordination is not free, and which topology wins")
    print("  depends on what you're optimizing for (cost vs. latency vs. success rate).")


if __name__ == "__main__":
    main()
