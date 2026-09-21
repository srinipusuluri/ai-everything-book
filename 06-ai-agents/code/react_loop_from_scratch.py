"""
The ReAct loop, built by hand -- no LangChain, no LangGraph, no API key.

This is the mechanism underneath every "agent" you will ever use: a control loop that
alternates THOUGHT (the model reasons about what to do), ACTION (the model emits a tool
call in some structured format), and OBSERVATION (the tool runs and its output is fed
back in) until the model emits a final answer or a guard rail stops it.

The one thing a real LLM would normally supply -- "which token comes next" -- is stubbed
out here with a FakeLLM that plays back a fixed script. This is not a simplification of
the interesting part; the interesting part is everything AROUND that token stream: how
raw text becomes a parsed action, how a bad tool name or bad JSON gets turned into an
observation the model can recover from, and when the loop gives up. All of that code
is exactly what a production agent runs, whether the tokens come from a script (here)
or from sampling logits (everywhere else). See notes/01-core-concepts.md section 2 for
why "the model decides to call a tool" is really "next-token prediction over a format
the prompt taught it to produce."

    python code/react_loop_from_scratch.py

Requires: nothing outside the standard library.
"""
from __future__ import annotations

import ast
import json
import operator
from dataclasses import dataclass
from typing import Any, Callable

# --------------------------------------------------------------------------------- #
# Real tools. Three of them, on purpose: enough to chain, not so many the demo        #
# drowns in plumbing. Each tool is just a Python function with a name and a          #
# docstring-shaped description -- that description is literally what gets sent to    #
# the model as part of its prompt in a real system (see notes/02, tool design).      #
# --------------------------------------------------------------------------------- #

_SAFE_OPS: dict[type, Callable[[float, float], float]] = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Pow: operator.pow, ast.Mod: operator.mod,
}


def _safe_eval(node: ast.AST) -> float:
    """Evaluate an arithmetic-only AST. No names, no calls, no imports -- unlike
    plain eval(), a hostile or hallucinated expression can't do anything but arithmetic."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_safe_eval(node.operand)
    raise ValueError(f"unsupported expression element: {ast.dump(node)}")


def calculator(expression: str) -> float:
    """Evaluate a basic arithmetic expression, e.g. '240 * 0.15'."""
    tree = ast.parse(expression, mode="eval")
    return round(_safe_eval(tree.body), 6)


_KB = {
    "eiffel tower height": "330 meters (with antennas), completed 1889.",
    "capital of france": "Paris.",
    "population of france": "approximately 68 million (2024 estimate).",
    "tallest mountain": "Mount Everest, 8,849 meters.",
    "speed of light": "299,792,458 meters per second.",
}


def search_kb(query: str) -> str:
    """Search a small local knowledge base by keyword overlap and return the best match."""
    q_words = set(query.lower().split())
    best_key, best_score = None, 0
    for key in _KB:
        score = len(q_words & set(key.split()))
        if score > best_score:
            best_key, best_score = key, score
    if best_key is None:
        raise ValueError(f"no knowledge-base entry matches query: {query!r}")
    return _KB[best_key]


_WEATHER = {"boston": "58F, cloudy", "paris": "72F, sunny", "tokyo": "80F, humid"}


def get_weather(city: str) -> str:
    """Look up current weather for a known city."""
    key = city.strip().lower()
    if key not in _WEATHER:
        raise ValueError(f"unknown city {city!r}. known cities: {sorted(_WEATHER)}")
    return _WEATHER[key]


TOOLS: dict[str, Callable[..., Any]] = {
    "calculator": calculator,
    "search_kb": search_kb,
    "get_weather": get_weather,
}

TOOL_DESCRIPTIONS = "\n".join(
    f"  - {name}({', '.join(fn.__code__.co_varnames[:fn.__code__.co_argcount])}): {fn.__doc__}"
    for name, fn in TOOLS.items()
)


# --------------------------------------------------------------------------------- #
# The FakeLLM. A real model turns (system prompt + transcript) into logits, samples #
# a token, and repeats until it has produced a THOUGHT/ACTION block or a FINAL      #
# ANSWER. Here we replace "sample from logits" with "read the next line of a        #
# script" -- everything downstream (parsing, dispatch, error handling) is identical #
# to what happens with a real model's output.                                       #
# --------------------------------------------------------------------------------- #

@dataclass
class ScriptedStep:
    thought: str
    action: str | None = None          # None means this step is a final answer
    action_input: str | None = None    # raw text, exactly as an LLM would emit it --
                                        # deliberately malformed in one scenario below
    final_answer: str | None = None


class FakeLLM:
    """Plays back a fixed list of steps. A real LLM's 'policy' is billions of learned
    weights; this one's policy is a list. The loop code below cannot tell the difference,
    which is the point: the loop only ever sees text and dispatches on it."""

    def __init__(self, script: list[ScriptedStep]):
        self._script = script
        self._i = 0

    def next_step(self) -> ScriptedStep | None:
        if self._i >= len(self._script):
            return None
        step = self._script[self._i]
        self._i += 1
        return step


# --------------------------------------------------------------------------------- #
# The ReAct loop itself.                                                            #
# --------------------------------------------------------------------------------- #

MAX_ITERATIONS = 4


def run_agent(llm: FakeLLM, max_iterations: int = MAX_ITERATIONS) -> str:
    """observe -> think -> act -> observe, until a final answer or the guard fires.

    This is the whole of an agent's control loop. Frameworks add persistence,
    streaming, and parallel tool calls around this; they do not add a fifth verb."""
    for turn in range(1, max_iterations + 1):
        step = llm.next_step()
        if step is None:
            return "[loop ended: script exhausted with no final answer]"

        print(f"\n  Thought ({turn}): {step.thought}")

        if step.final_answer is not None:
            print(f"  Final Answer: {step.final_answer}")
            return step.final_answer

        print(f"  Action: {step.action}[{step.action_input}]")

        # --- Step 1: parse the action input. A real model emits this as a JSON ---
        # object because that's the format the tool-calling API enforces (see
        # notes/01, section on JSON schema + the tool-call round trip). Malformed
        # JSON here is not hypothetical -- it happens whenever the model gets cut
        # off, nests quotes wrong, or the sampling temperature is too high.
        try:
            args = json.loads(step.action_input)
        except json.JSONDecodeError as e:
            observation = (
                f"ERROR: could not parse action input as JSON ({e.msg} at char {e.pos}). "
                f"Re-emit the action with valid JSON, e.g. {{\"expression\": \"1 + 1\"}}."
            )
            print(f"  Observation: {observation}")
            continue

        # --- Step 2: dispatch to the tool, or explain that it doesn't exist. A ---
        # hallucinated tool name is not an exception in a well-built agent -- it's
        # an expected input class that must produce a *recoverable* observation,
        # not a stack trace the model has never seen and cannot act on.
        if step.action not in TOOLS:
            observation = (
                f"ERROR: unknown tool '{step.action}'. Available tools: {sorted(TOOLS)}. "
                f"Pick one of these and retry."
            )
            print(f"  Observation: {observation}")
            continue

        # --- Step 3: run the tool. Any exception becomes text, not a crash. ---
        try:
            result = TOOLS[step.action](**args)
            observation = str(result)
        except TypeError as e:
            observation = f"ERROR: bad arguments for '{step.action}' ({e}). Check the schema and retry."
        except Exception as e:  # noqa: BLE001 -- deliberately broad: tool failures are data, not crashes
            observation = f"ERROR: tool '{step.action}' failed: {e}"

        print(f"  Observation: {observation}")

    explanation = (
        f"[max-iteration guard fired after {max_iterations} steps without a final answer. "
        f"This almost always means one of: (1) a tool is failing repeatedly and the model "
        f"isn't changing strategy, (2) the task is unsolvable with the given tools, or "
        f"(3) the model is stuck in a loop re-trying the same action. Aborting here is "
        f"correct -- an unbounded loop against a paid API is a cost incident, not a bug fix.]"
    )
    print(f"\n  {explanation}")
    return explanation


# --------------------------------------------------------------------------------- #
# Four scenarios exercising the loop.                                               #
# --------------------------------------------------------------------------------- #

def rule(title: str) -> None:
    print("\n" + "=" * 78 + f"\n{title}\n" + "=" * 78)


def scenario_happy_path() -> None:
    rule("1. HAPPY PATH -- two tools chained toward one answer")
    print("  Q: What is 15% of 240, and what's the weather in Paris?")
    script = [
        ScriptedStep(
            thought="I need two independent facts. Start with the math.",
            action="calculator", action_input='{"expression": "240 * 0.15"}',
        ),
        ScriptedStep(
            thought="Got 36.0. Now the weather.",
            action="get_weather", action_input='{"city": "Paris"}',
        ),
        ScriptedStep(
            thought="I have both pieces. Time to answer.",
            final_answer="15% of 240 is 36, and Paris is 72F and sunny.",
        ),
    ]
    run_agent(FakeLLM(script))


def scenario_hallucinated_tool() -> None:
    rule("2. HALLUCINATED TOOL NAME -- the model reaches for a tool that doesn't exist")
    print("  Q: Look up the height of the Eiffel Tower.")
    print(f"  (registered tools: {sorted(TOOLS)})")
    script = [
        ScriptedStep(
            thought="I'll use the wiki lookup tool for this.",
            action="lookup_wiki", action_input='{"query": "Eiffel Tower height"}',
        ),
        ScriptedStep(
            thought="That tool doesn't exist. The observation told me what does. Retry with search_kb.",
            action="search_kb", action_input='{"query": "eiffel tower height"}',
        ),
        ScriptedStep(
            thought="Got a clean answer.",
            final_answer="The Eiffel Tower is 330 meters tall, including antennas.",
        ),
    ]
    run_agent(FakeLLM(script))


def scenario_malformed_arguments() -> None:
    rule("3. MALFORMED ARGUMENTS -- the JSON the model emitted doesn't parse")
    print("  Q: Calculate 12 * (3 + 4).")
    script = [
        ScriptedStep(
            thought="Let me compute that.",
            # Missing closing brace -- exactly the kind of truncation that happens
            # when a model's output gets cut off or it miscounts nesting.
            action="calculator", action_input='{"expression": "12 * (3 + 4)"',
        ),
        ScriptedStep(
            thought="The observation told me the JSON was invalid. Fixing the syntax.",
            action="calculator", action_input='{"expression": "12 * (3 + 4)"}',
        ),
        ScriptedStep(
            thought="84. Done.",
            final_answer="12 * (3 + 4) = 84.",
        ),
    ]
    run_agent(FakeLLM(script))


def scenario_max_iterations() -> None:
    rule("4. MAX-ITERATION GUARD -- an unsolvable task, and the loop refuses to spin forever")
    print("  Q: Keep checking the weather in Atlantis until it's sunny.")
    print("  (Atlantis is not a known city -- every call will fail identically.)")
    script = [
        ScriptedStep(thought="Checking Atlantis.", action="get_weather",
                     action_input='{"city": "Atlantis"}'),
        ScriptedStep(thought="Not sunny yet, or errored. Try again.", action="get_weather",
                     action_input='{"city": "Atlantis"}'),
        ScriptedStep(thought="Still nothing. Try again.", action="get_weather",
                     action_input='{"city": "Atlantis"}'),
        ScriptedStep(thought="One more time.", action="get_weather",
                     action_input='{"city": "Atlantis"}'),
        ScriptedStep(thought="Surely this time.", action="get_weather",  # never reached
                     action_input='{"city": "Atlantis"}'),
    ]
    run_agent(FakeLLM(script), max_iterations=4)


def main() -> None:
    print("Registered tools:")
    print(TOOL_DESCRIPTIONS)
    scenario_happy_path()
    scenario_hallucinated_tool()
    scenario_malformed_arguments()
    scenario_max_iterations()
    print("\nDone. Every 'Thought/Action/Observation' line above is the literal text a")
    print("real ReAct prompt would contain -- see notes/01-core-concepts.md section 3")
    print("for the exact prompt template this loop is standing in for.")


if __name__ == "__main__":
    main()
