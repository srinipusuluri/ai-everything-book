"""
Pydantic v2 as the contract between your code and a language model.

Why this file exists
--------------------
An LLM returns text. Your program needs a value. Everything between those two
sentences -- the JSON schema you send, the parse, the validation, the retry when
the model hallucinated a field -- is where LLM applications actually break.

Pydantic v2 is the standard answer in Python. Its core is written in Rust
(pydantic-core), so validation is fast enough to sit in a request path, and the
same model class gives you three things at once:

    1. a JSON Schema to hand the provider as a tool / structured-output spec
    2. runtime validation of whatever comes back
    3. a typed Python object your IDE and type checker understand

This script simulates model responses -- good ones, subtly wrong ones, and
outright broken ones -- and runs a repair loop against them. No network, no key.

    python code/pydantic_structured_output.py

Requires: pydantic>=2.  Install with:
    uv pip install pydantic
If pydantic is missing, the script degrades to a stdlib dataclasses + manual
validation walkthrough so you can still see the shape of the problem (and the
amount of code Pydantic is saving you).
"""
from __future__ import annotations

import json
import sys
from typing import Any

try:
    import pydantic
    from pydantic import BaseModel, Field, ValidationError, field_validator
    HAVE_PYDANTIC = pydantic.VERSION.startswith("2")
except ImportError:                                   # pragma: no cover
    HAVE_PYDANTIC = False


def banner(n: str, title: str) -> None:
    print()
    print("=" * 78)
    print(f"{n}. {title}")
    print("=" * 78)


# =========================================================================== #
# Simulated model responses -- what a real provider actually returns          #
# =========================================================================== #
# These are not strawmen. Every one of these is a failure mode you will see in
# the first week of running structured output against a real model.
SIMULATED_RESPONSES: list[tuple[str, str]] = [
    (
        "clean",
        '{"sentiment": "negative", "confidence": 0.91, "topics": ["billing", "refund"],'
        ' "urgency": 4, "customer_email": "dana@example.com",'
        ' "summary": "Customer was double-charged and wants a refund."}',
    ),
    (
        "fenced + preamble",          # model ignored "JSON only" -- extremely common
        'Sure! Here is the structured output you asked for:\n'
        '```json\n'
        '{"sentiment": "positive", "confidence": 0.75, "topics": ["onboarding"],\n'
        ' "urgency": 1, "customer_email": "sam@example.com",\n'
        ' "summary": "Customer is happy with setup."}\n'
        '```\n'
        'Let me know if you need anything else!',
    ),
    (
        "stringified number",        # "0.8" not 0.8 -- Pydantic coerces, json.loads does not
        '{"sentiment": "neutral", "confidence": "0.8", "topics": [],'
        ' "urgency": "2", "customer_email": "lee@example.com",'
        ' "summary": "Routine question about invoice timing."}',
    ),
    (
        "hallucinated enum + out of range",
        '{"sentiment": "furious", "confidence": 1.4, "topics": ["billing"],'
        ' "urgency": 11, "customer_email": "not-an-email",'
        ' "summary": "hi"}',
    ),
    (
        "missing required field",
        '{"sentiment": "negative", "topics": ["latency"], "urgency": 3,'
        ' "summary": "API responses are slow during peak hours."}',
    ),
    (
        "truncated -- hit max_tokens",
        '{"sentiment": "negative", "confidence": 0.6, "topics": ["billing",',
    ),
]


# =========================================================================== #
# PYDANTIC PATH                                                               #
# =========================================================================== #
def run_pydantic() -> int:
    print(f"pydantic {pydantic.VERSION} | Python {sys.version.split()[0]}")

    # ----------------------------------------------------------------- #
    # 1. The model IS the schema IS the validator                        #
    # ----------------------------------------------------------------- #
    from enum import Enum

    # Use an Enum, not a bare `str`. It becomes an `enum` in the JSON Schema,
    # which is the single most effective thing you can do to stop a model
    # inventing categories. Models follow schemas far better than prose.
    class Sentiment(str, Enum):
        """Overall sentiment expressed by the customer."""
        positive = "positive"
        neutral = "neutral"
        negative = "negative"

    class TicketAnalysis(BaseModel):
        """Structured analysis of one customer support ticket."""
        # The docstring above is not decoration -- Pydantic puts it in the
        # schema's `description` and the model reads it, exactly like every
        # Field(description=...) below. Your schema is prompt real-estate: it is
        # instruction the model cannot skim past, and you pay tokens for it
        # either way. Write it for the model, keep it short, keep it factual.
        #
        # model_config controls validation strictness. extra="forbid" maps to
        # additionalProperties: false, which most providers' *strict* structured
        # output mode requires -- and which catches a model inventing fields.
        model_config = {"extra": "forbid", "str_strip_whitespace": True}

        sentiment: Sentiment = Field(
            description="Overall sentiment of the customer's message."
        )
        confidence: float = Field(
            ge=0.0, le=1.0,
            description="Model confidence in the sentiment label, 0.0 to 1.0.",
        )
        topics: list[str] = Field(
            default_factory=list, max_length=5,
            description="Up to 5 short topic tags, lowercase, e.g. 'billing'.",
        )
        urgency: int = Field(
            ge=1, le=5,
            description="1 = can wait a week, 5 = page someone now.",
        )
        customer_email: str = Field(
            description="The customer's email address, exactly as written."
        )
        summary: str = Field(
            min_length=20, max_length=300,
            description="One-sentence factual summary. No advice, no apology.",
        )

        # A custom validator for rules a JSON Schema cannot express. Note it runs
        # AFTER type coercion, so `v` is already a str.
        @field_validator("customer_email")
        @classmethod
        def looks_like_email(cls, v: str) -> str:
            if "@" not in v or "." not in v.split("@")[-1]:
                raise ValueError(f"{v!r} is not an email address")
            return v.lower()

        @field_validator("topics")
        @classmethod
        def normalise_topics(cls, v: list[str]) -> list[str]:
            # Validators can repair as well as reject. Normalising here means the
            # rest of your codebase never sees "Billing " and "billing" as two things.
            return sorted({t.strip().lower() for t in v if t.strip()})

    banner("1", "One class, three jobs")
    print("  A Pydantic model gives you the JSON Schema you send to the provider,")
    print("  the validator for what comes back, and a typed object afterwards.")
    print("  Keeping those three in sync by hand is where bugs live.")

    # ----------------------------------------------------------------- #
    # 2. Schema generation -- what you actually send the provider        #
    # ----------------------------------------------------------------- #
    banner("2", "model_json_schema() -- the payload you hand the model")
    schema = TicketAnalysis.model_json_schema()
    print(json.dumps(schema, indent=2))
    print()
    print("  Ship this straight into a tool definition:")
    print("""
      tools = [{
          "name": "record_ticket_analysis",
          "description": TicketAnalysis.__doc__,
          "input_schema": TicketAnalysis.model_json_schema(),
      }]

  Then validate the tool_use block's input with TicketAnalysis.model_validate(...).
  The schema and the parser can never drift, because they are the same class.
  This is the Python half of Module 06 (tool calling) and Module 07 (agents).""")

    # ----------------------------------------------------------------- #
    # 3. Validating real (simulated) responses                          #
    # ----------------------------------------------------------------- #
    banner("3", "Validating what the model actually sent")

    def extract_json(text: str) -> str:
        """Models wrap JSON in prose and code fences no matter how firmly you ask
        them not to. Strip the fence; if that fails, take the outermost {...}.
        Boring, unglamorous, and required in every production codebase."""
        t = text.strip()
        if "```" in t:
            block = t.split("```", 2)[1]
            if block.startswith("json"):
                block = block[4:]
            t = block.strip()
        start, end = t.find("{"), t.rfind("}")
        if start != -1 and end > start:
            t = t[start:end + 1]
        return t

    def try_parse(raw: str) -> tuple[TicketAnalysis | None, str]:
        """Return (model, error_report). Error report is what we feed back to the
        model on a repair attempt."""
        try:
            payload = json.loads(extract_json(raw))
        except json.JSONDecodeError as e:
            return None, f"Response was not valid JSON: {e}"
        try:
            return TicketAnalysis.model_validate(payload), ""
        except ValidationError as e:
            # e.errors() is machine-readable: loc, type, msg, input. This is the
            # feedback that makes a repair loop work -- do NOT send str(e) alone
            # and hope. Send the field path and the constraint that was violated.
            lines = [
                f"  - field {'.'.join(str(p) for p in err['loc']) or '<root>'}: "
                f"{err['msg']} (got {err.get('input')!r})"
                for err in e.errors()
            ]
            return None, "Validation failed:\n" + "\n".join(lines)

    for label, raw in SIMULATED_RESPONSES:
        obj, err = try_parse(raw)
        print(f"\n  [{label}]")
        if obj is not None:
            print(f"    OK -> sentiment={obj.sentiment.value} urgency={obj.urgency} "
                  f"conf={obj.confidence} topics={obj.topics}")
            print(f"       email normalised to {obj.customer_email!r}")
        else:
            print("    REJECTED")
            for line in err.splitlines():
                print("    " + line)

    print()
    print("  Three things to notice:")
    print("   * 'stringified number' PASSED. Pydantic's default (lax) mode coerces")
    print("     \"0.8\" -> 0.8 and \"2\" -> 2. That is usually what you want from an")
    print("     LLM, which has no real notion of types. If you need it to fail,")
    print("     use model_config = {'strict': True} or Strict[float].")
    print("   * The fenced response parsed because we stripped the fence, not")
    print("     because Pydantic is clever. Text wrangling is still your job.")
    print("   * The hallucinated-enum response produced FIVE distinct errors in")
    print("     one pass. Pydantic does not stop at the first. That whole list is")
    print("     what you send back for repair -- one round trip, not five.")

    # ----------------------------------------------------------------- #
    # 4. The repair loop                                                #
    # ----------------------------------------------------------------- #
    banner("4", "The repair loop (what to do when validation fails)")

    class FakeModel:
        """Simulates a model that gets it wrong, is told precisely why, and
        converges. Real models genuinely do behave like this when you feed back
        structured error messages instead of 'that was wrong, try again'."""

        def __init__(self) -> None:
            self.turn = 0

        def respond(self, feedback: str | None) -> str:
            self.turn += 1
            if self.turn == 1:
                return ('{"sentiment": "furious", "confidence": 1.4, '
                        '"topics": ["Billing", "billing "], "urgency": 11, '
                        '"customer_email": "not-an-email", "summary": "hi"}')
            if self.turn == 2:
                # Fixed the enum and the ranges; summary still too short.
                return ('{"sentiment": "negative", "confidence": 0.95, '
                        '"topics": ["Billing", "billing "], "urgency": 5, '
                        '"customer_email": "dana@example.com", "summary": "angry"}')
            return ('{"sentiment": "negative", "confidence": 0.95, '
                    '"topics": ["Billing", "billing "], "urgency": 5, '
                    '"customer_email": "Dana@Example.com", '
                    '"summary": "Customer was charged twice and is demanding an '
                    'immediate refund."}')

    def call_with_repair(model: FakeModel, max_attempts: int = 3) -> TicketAnalysis | None:
        feedback: str | None = None
        for attempt in range(1, max_attempts + 1):
            raw = model.respond(feedback)
            obj, err = try_parse(raw)
            print(f"\n  attempt {attempt}:")
            print(f"    model said: {raw[:72]}...")
            if obj is not None:
                print("    -> valid")
                return obj
            print("    -> invalid; feeding these errors back verbatim:")
            for line in err.splitlines():
                print("      " + line)
            # THE IMPORTANT PART: the next user turn contains the exact field
            # paths and constraints. Vague feedback ("that was invalid") gets you
            # a differently-invalid answer. Specific feedback converges.
            feedback = (
                f"Your previous response failed schema validation.\n{err}\n"
                "Return ONLY corrected JSON matching the schema. No prose."
            )
        return None

    result = call_with_repair(FakeModel())
    print()
    if result:
        print("  Converged in 3 turns. Final object:")
        print("   ", result.model_dump_json(indent=2).replace("\n", "\n    "))
    print()
    print("  Repair-loop rules learned the hard way:")
    print("   * Cap attempts at 2-3. If a model cannot satisfy your schema in three")
    print("     tries, your schema is the problem -- usually over-constrained, or")
    print("     asking for something the input does not contain.")
    print("   * Count repairs as a metric. A rising repair rate means a prompt")
    print("     regression, a model version change, or drifting input data.")
    print("   * Prefer the provider's native structured-output / tool mode, which")
    print("     constrains decoding to the grammar. Repair is the fallback, not")
    print("     the plan. But keep the repair path: strict modes still emit")
    print("     semantically wrong values that only YOUR validators catch.")
    print("   * Log the raw text alongside the error. You cannot debug a parse")
    print("     failure from a stack trace.")

    # ----------------------------------------------------------------- #
    # 5. Schema-design rules                                            #
    # ----------------------------------------------------------------- #
    banner("5", "Designing schemas a model can actually satisfy")
    print("""
  Enum over free string        'furious' becomes impossible, not merely discouraged.
  Flat over deeply nested      Every level of nesting costs accuracy. Two is plenty.
  Optional with a default      Let the model decline a field instead of inventing one.
  Describe every field         Field(description=...) is prompt text the model reads.
  Bound every number           ge/le turns a silent 1.4 confidence into a caught error.
  Ask for evidence first       Put a `quote_from_source` field BEFORE the judgement
                               field. Field order in the schema is generation order,
                               so the model reasons before it commits. This one trick
                               is worth several points of accuracy on extraction tasks.
  Avoid unions of objects      anyOf is where both providers and models get confused.
  Do not ask for a float when  A 1-5 int is answerable. 'score between 0 and 1 to two
  an int will do               decimals' invites false precision.

  Validate twice: the schema constrains SHAPE, your validators constrain MEANING.
  A model can return a perfectly-shaped, entirely fabricated customer_id.""".rstrip())

    # ----------------------------------------------------------------- #
    # 6. Pydantic beyond LLM output                                     #
    # ----------------------------------------------------------------- #
    banner("6", "The other two places Pydantic earns its keep")
    print("""
  Config, via pydantic-settings:

      from pydantic_settings import BaseSettings, SettingsConfigDict

      class Settings(BaseSettings):
          model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")
          anthropic_api_key: str                 # no default -> required
          model: str = "claude-sonnet-4-5"
          max_concurrency: int = 8
          request_timeout_s: float = 120.0

      settings = Settings()      # raises at STARTUP if a key is missing

  That last line is the point. os.environ["API_KEY"] fails at 3am on the first
  request that needs it; Settings() fails in the first second of the process,
  in CI, in your smoke test. Typed config turns a runtime incident into a
  deploy-time error. And never put the secret in the repo -- .env is
  gitignored, production injects real environment variables, and the value
  never reaches a log line.

  API boundaries, via FastAPI: FastAPI request/response models ARE Pydantic
  models, so the same class validates the LLM's output, documents your endpoint
  in OpenAPI, and serialises the response. One definition, three uses.

  What NOT to use it for: hot inner loops over millions of rows. Validation is
  fast but not free. Validate at the EDGES of your system -- input parsing, LLM
  output, config -- and pass plain dataclasses or arrays around inside.""".rstrip())
    return 0


# =========================================================================== #
# FALLBACK PATH -- stdlib only                                                #
# =========================================================================== #
def run_dataclasses_fallback() -> int:
    """Runs when pydantic v2 is unavailable. Same problem, done by hand, so you
    can see exactly how much code Pydantic is replacing."""
    from dataclasses import asdict, dataclass

    print()
    print("!" * 78)
    print("pydantic v2 not importable. Running the stdlib fallback.")
    print("Install it with:  uv pip install pydantic")
    print("!" * 78)

    VALID_SENTIMENTS = {"positive", "neutral", "negative"}

    @dataclass(slots=True)
    class TicketAnalysis:
        sentiment: str
        confidence: float
        urgency: int
        customer_email: str
        summary: str
        topics: list[str]

    def validate(payload: dict[str, Any]) -> TicketAnalysis:
        """Everything Pydantic did with six Field() calls. Note that dataclasses
        do NOT validate: `TicketAnalysis(sentiment=42, ...)` is perfectly legal
        Python and will fail 200 lines later. Type hints are documentation to
        the interpreter, nothing more. That is the whole reason Pydantic exists."""
        errors: list[str] = []

        def need(key: str, kind: type) -> Any:
            if key not in payload:
                errors.append(f"  - field {key}: required field missing")
                return None
            val = payload[key]
            try:
                return kind(val)                       # manual coercion
            except (TypeError, ValueError):
                errors.append(f"  - field {key}: expected {kind.__name__}, got {val!r}")
                return None

        sentiment = need("sentiment", str)
        if sentiment is not None and sentiment not in VALID_SENTIMENTS:
            errors.append(f"  - field sentiment: {sentiment!r} not in {sorted(VALID_SENTIMENTS)}")
        confidence = need("confidence", float)
        if confidence is not None and not 0.0 <= confidence <= 1.0:
            errors.append(f"  - field confidence: {confidence} not in [0.0, 1.0]")
        urgency = need("urgency", int)
        if urgency is not None and not 1 <= urgency <= 5:
            errors.append(f"  - field urgency: {urgency} not in [1, 5]")
        email = need("customer_email", str)
        if email is not None and ("@" not in email or "." not in email.split("@")[-1]):
            errors.append(f"  - field customer_email: {email!r} is not an email address")
        summary = need("summary", str)
        if summary is not None and not 20 <= len(summary) <= 300:
            errors.append(f"  - field summary: length {len(summary)} outside [20, 300]")
        topics_raw = payload.get("topics", [])
        if not isinstance(topics_raw, list):
            errors.append(f"  - field topics: expected list, got {type(topics_raw).__name__}")
            topics_raw = []
        topics = sorted({str(t).strip().lower() for t in topics_raw if str(t).strip()})

        if errors:
            raise ValueError("Validation failed:\n" + "\n".join(errors))
        return TicketAnalysis(sentiment, confidence, urgency, email.lower(), summary, topics)

    banner("1", "Hand-rolled validation (what Pydantic replaces)")
    for label, raw in SIMULATED_RESPONSES:
        t = raw.strip()
        if "```" in t:
            t = t.split("```", 2)[1].removeprefix("json").strip()
        start, end = t.find("{"), t.rfind("}")
        t = t[start:end + 1] if start != -1 and end > start else t
        print(f"\n  [{label}]")
        try:
            obj = validate(json.loads(t))
            print(f"    OK -> {asdict(obj)}")
        except json.JSONDecodeError as e:
            print(f"    REJECTED  not valid JSON: {e}")
        except ValueError as e:
            print("    REJECTED")
            for line in str(e).splitlines():
                print("    " + line)

    banner("2", "The tally")
    print("""
  That was ~45 lines of validation code for six fields, and it still does not:
    * generate a JSON Schema to send the provider
    * produce machine-readable error objects (only strings)
    * handle nested models, unions, or aliases
    * serialise back to JSON with proper enum/datetime handling
    * give your type checker anything to work with

  Pydantic does all of it from the class definition, in Rust. This is one of the
  few places in the Python ecosystem where the answer is genuinely 'just use the
  obvious library'. Install it:  uv pip install pydantic""".rstrip())
    return 0


def main() -> int:
    print()
    print("Pydantic v2 and LLM structured output -- offline demo")
    if HAVE_PYDANTIC:
        rc = run_pydantic()
    else:
        rc = run_dataclasses_fallback()
    print()
    print("Done. The rule: never let unvalidated model output past your first")
    print("function boundary. A typed object at the edge is the cheapest")
    print("reliability improvement available to an LLM application.")
    print()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
