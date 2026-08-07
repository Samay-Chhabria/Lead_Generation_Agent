"""LLM provider interface shared by every provider implementation."""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class LLMError(Exception):
    """Base exception for all LLM provider errors."""


class LLMNetworkError(LLMError):
    """Raised when the LLM gateway cannot be reached (network failure).

    Covers connection refused, DNS failures, and socket timeouts. These are the
    only failures the single client retries locally — with the same
    ``model="auto"`` request, never a different model.
    """


class LLMStatusError(LLMError):
    """Raised when the LLM gateway answers with an HTTP error status.

    Attributes:
        status_code: The HTTP status code returned by the gateway.
    """

    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class LLMResponseError(LLMError):
    """Raised when the LLM returns malformed or unparseable output."""


@dataclass(frozen=True, slots=True)
class LLMToolCall:
    """A tool invocation requested by the LLM.

    Attributes:
        name: Name of the tool to call.
        arguments: Stringified JSON arguments for the tool.
    """

    name: str
    arguments: str = "{}"


@dataclass(frozen=True, slots=True)
class ToolMessage:
    """A role-and-content message exchanged with the LLM."""

    role: str
    content: str


class BaseLLM(ABC):
    """Interface every LLM gateway must implement.

    The application communicates only with a single OpenAI-compatible gateway
    (:class:`app.llm.providers.freellmrouter.FreeLLMRouterProvider`); the rest
    of the codebase never knows which underlying model powers the gateway.
    Every request asks for ``model="auto"`` so the router performs automatic
    model selection, retries, provider rotation, fallback, rate-limit recovery,
    and load balancing.

    Subclasses expose the gateway as a plain text-in/text-out chat model. The
    planner parses JSON out of the completion; providers with native function
    calling may still return plain JSON because the MockProvider contract is
    plain JSON and the agent treats every model uniformly.
    """

    name: str = "unknown"

    @abstractmethod
    def complete(self, messages: list[ToolMessage], **kwargs: Any) -> str:
        """Return the model's text completion for the given messages.

        Args:
            messages: The conversation so far.
            **kwargs: Provider-specific options (model, temperature, ...).

        Returns:
            The raw completion text.
        """

    def generate(self, messages: list[ToolMessage], **kwargs: Any) -> str:
        """Return the model's text completion (public entry point).

        The application calls :meth:`generate` on every provider. The default
        implementation delegates to :meth:`complete` so every provider supports
        it.

        Args:
            messages: The conversation so far.
            **kwargs: Provider-specific options (model, temperature, ...).

        Returns:
            The raw completion text.
        """
        return self.complete(messages, **kwargs)


# Backward-compatible alias: existing code and tests import LLMProvider.
LLMProvider = BaseLLM


def parse_json_objects(text: str) -> list[dict[str, Any]]:
    """Extract JSON objects from a possibly noisy completion.

    Handles strict JSON, JSON fenced in markdown code blocks, and JSON with
    prose before or after it.

    Args:
        text: The raw completion text.

    Returns:
        A list of parsed JSON dictionaries.

    Raises:
        LLMResponseError: When no valid JSON object can be found.
    """
    candidates = []
    if "```" in text:
        candidates.extend(_extract_code_blocks(text))
    candidates.append(text)
    for candidate in candidates:
        for obj in _json_candidates(candidate):
            try:
                parsed = json.loads(obj)
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(parsed, dict):
                return [parsed]
            if (
                isinstance(parsed, list)
                and parsed
                and all(isinstance(item, dict) for item in parsed)
            ):
                return parsed
    raise LLMResponseError(f"Could not parse JSON from LLM output: {text[:200]!r}")


def _json_candidates(text: str):
    """Yield balanced JSON-looking substrings from a piece of text.

    Scans for opening ``{`` or ``[`` and walks forward to the matching close,
    so prose before or after a JSON value does not break parsing.
    """
    for index, char in enumerate(text):
        if char not in "{[":
            continue
        if char == "{":
            open_char, close_char = "{", "}"
        else:
            open_char, close_char = "[", "]"
        depth = 0
        in_string = False
        escaped = False
        for pos in range(index, len(text)):
            ch = text[pos]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == open_char:
                depth += 1
            elif ch == close_char:
                depth -= 1
                if depth == 0:
                    yield text[index : pos + 1]
                    break


def _extract_code_blocks(text: str) -> list[str]:
    """Return the contents of every fenced code block in the text."""
    blocks: list[str] = []
    parts = text.split("```")
    for index in range(1, len(parts), 2):
        block = parts[index]
        if "\n" in block:
            block = block.split("\n", 1)[1]
        blocks.append(block)
    return blocks
