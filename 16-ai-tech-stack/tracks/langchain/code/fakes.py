"""
fakes.py -- deterministic, offline test doubles for LangChain.

Every example in this track runs with NO network and NO API key. That is not a
gimmick: a chat model you can script is the single most useful thing you can own
when you are learning (or debugging) a framework, because it removes the two
variables that make LLM bugs unreproducible -- nondeterminism and latency.

langchain-core ships its own fakes (`langchain_core.language_models.fake_chat_models`:
`FakeListChatModel`, `GenericFakeChatModel`, `ParrotFakeChatModel`). They are fine
for unit tests but they are opaque -- they just replay a list. We hand-roll ours so
you can *see* the contract a chat model has to satisfy:

    _generate(messages, stop, run_manager, **kwargs) -> ChatResult
    _stream(messages, ...)                           -> Iterator[ChatGenerationChunk]
    _llm_type                                        -> str
    bind_tools(tools, **kwargs)                      -> Runnable   (optional)

Implement those four and *everything* else in langchain-core works on your object:
`|` composition, `.batch()`, `.astream()`, `.with_retry()`, `.with_fallbacks()`,
`.with_structured_output()`, callbacks, LangSmith tracing. That is the actual value
of the Runnable abstraction, and it is much easier to believe once you have written
a 40-line model that gets all of it for free.

Verified against langchain-core 1.6.3 / langchain 1.4.0 (Python 3.14).
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Iterator, Sequence
from typing import Any

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool

# ---------------------------------------------------------------------------
# 1. A rule-based chat model: deterministic, input-sensitive, streamable.
# ---------------------------------------------------------------------------


class FakeChatModel(BaseChatModel):
    """Answers by first-matching substring rule. Deterministic for a given input.

    `rules` is an ordered list of (needle, reply) pairs matched case-insensitively
    against the concatenated content of the incoming messages. First hit wins.
    """

    rules: list[tuple[str, str]] = []
    default: str = "I do not have enough context to answer that."
    # Public counter so examples can prove how many times the model was actually hit
    # (useful for demonstrating caching and batching).
    call_count: int = 0

    @property
    def _llm_type(self) -> str:
        return "fake-rule-chat-model"

    def _reply(self, messages: list[BaseMessage]) -> str:
        blob = " ".join(str(m.content) for m in messages).lower()
        for needle, reply in self.rules:
            if needle.lower() in blob:
                return reply
        return self.default

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.call_count += 1
        body = self._reply(messages)
        # Real providers report token usage here; we fake it with a word count so the
        # token-accounting example has something honest-looking to add up.
        prompt_words = sum(len(str(m.content).split()) for m in messages)
        out_words = len(body.split())
        message = AIMessage(
            content=body,
            usage_metadata={
                "input_tokens": prompt_words,
                "output_tokens": out_words,
                "total_tokens": prompt_words + out_words,
            },
            response_metadata={"model_name": self._llm_type},
        )
        return ChatResult(generations=[ChatGeneration(message=message)])

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        # Token-by-token streaming, word-sized. Note the on_llm_new_token callback --
        # forget it and your callback handlers / LangSmith traces go silent.
        self.call_count += 1
        for word in self._reply(messages).split(" "):
            chunk = ChatGenerationChunk(message=AIMessageChunk(content=word + " "))
            if run_manager:
                run_manager.on_llm_new_token(word, chunk=chunk)
            yield chunk


# ---------------------------------------------------------------------------
# 2. A scripted chat model: replays a fixed transcript, one AIMessage per call.
# ---------------------------------------------------------------------------


class ScriptedChatModel(BaseChatModel):
    """Returns `script[i]` on the i-th call, then repeats the last entry forever.

    This is how you test an agent loop: you decide exactly when the model emits a
    tool call and when it emits a final answer, so the loop's control flow -- not
    the model's mood -- is what your test exercises.
    """

    script: list[AIMessage] = []
    cursor: int = 0
    # Tool schemas handed to us by bind_tools. A real provider serialises these to
    # JSON Schema and puts them on the wire; we just record them so you can inspect.
    bound_tool_names: list[str] = []

    @property
    def _llm_type(self) -> str:
        return "scripted-chat-model"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        if not self.script:
            msg = "ScriptedChatModel needs a non-empty script"
            raise ValueError(msg)
        index = min(self.cursor, len(self.script) - 1)
        self.cursor += 1
        return ChatResult(generations=[ChatGeneration(message=self.script[index])])

    def bind_tools(
        self,
        tools: Sequence[dict[str, Any] | type | Any],
        **kwargs: Any,
    ) -> Runnable:
        """Attach tools to the model.

        `bind_tools` is NOT magic: it returns a `RunnableBinding` -- the same model
        with extra kwargs glued to every future call. Real providers convert each
        tool to JSON Schema via `convert_to_openai_tool` and send it as part of the
        request payload. We record the names and return a bound copy.
        """
        names = [getattr(t, "name", None) or getattr(t, "__name__", str(t)) for t in tools]
        self.bound_tool_names = names
        return self.bind(tools=names, **kwargs)


# ---------------------------------------------------------------------------
# 3. A model that fails on purpose -- for with_retry / with_fallbacks demos.
# ---------------------------------------------------------------------------


class FlakyChatModel(BaseChatModel):
    """Raises `ConnectionError` for the first `fail_times` calls, then succeeds."""

    fail_times: int = 2
    reply: str = "finally succeeded"
    attempts: int = 0

    @property
    def _llm_type(self) -> str:
        return "flaky-chat-model"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.attempts += 1
        if self.attempts <= self.fail_times:
            msg = f"simulated 503 from provider (attempt {self.attempts})"
            raise ConnectionError(msg)
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=self.reply))]
        )


# ---------------------------------------------------------------------------
# 4. A deterministic embedding model with real (lexical) similarity structure.
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class HashingEmbeddings(Embeddings):
    """The hashing trick: a bag-of-words vector with signed hash buckets.

    Each token is hashed to a bucket index and a +/-1 sign; the vector is then
    L2-normalised so cosine similarity is a dot product. No vocabulary, no training,
    no network -- and unlike a random fake embedding, documents that *share words*
    actually land near each other, so retrieval demos retrieve the right thing.

    This is a real technique (see `sklearn.feature_extraction.text.HashingVectorizer`),
    not a toy. It is also a good mental model for what a learned embedding does:
    text -> fixed-length vector, similar text -> nearby vectors. The difference is
    that a learned model puts *synonyms* near each other and this one does not.
    """

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in _TOKEN_RE.findall(text.lower()):
            digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
            h = int.from_bytes(digest, "big")
            sign = 1.0 if (h >> 8) & 1 else -1.0
            vec[h % self.dim] += sign
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def rule(title: str) -> None:
    """Section header, because unlabelled console output teaches nothing."""
    print(f"\n{'=' * 74}\n{title}\n{'=' * 74}")
