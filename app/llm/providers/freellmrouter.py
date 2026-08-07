"""Canonical OpenAI-compatible client for the FreeLLM Router gateway.

The whole application talks to a single OpenAI-compatible endpoint exposed by a
FreeLLM Router instance. Every request asks for ``model="auto"``: the router
performs all model selection, retries, provider rotation, fallback, rate-limit
recovery, and load balancing. The client never names a concrete model and
implements no fallback chain of its own.

Only transient network failures (connection refused, DNS failure, socket
timeouts) are retried locally — with the same ``model="auto"`` request, never a
different model. HTTP error responses are forwarded untouched so the router can
decide how to handle them.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from app.config.constants import (
    DEFAULT_LLM_MAX_TOKENS,
    DEFAULT_LLM_NETWORK_MAX_RETRIES,
    DEFAULT_LLM_NETWORK_RETRY_BACKOFF,
    DEFAULT_LLM_REQUEST_TIMEOUT,
    DEFAULT_LLM_TEMPERATURE,
    FREELLM_PROVIDER_NAME,
)
from app.llm._http import post_json
from app.llm.base import LLMError, LLMNetworkError, LLMProvider, ToolMessage

ModelSink = Callable[[str, str], None]

_AUTO_ROUTER_REASON = "Auto (Router Selected)"


class FreeLLMRouterProvider(LLMProvider):
    """OpenAI-compatible client for the FreeLLM Router gateway.

    Args:
        api_key: The FreeLLM Router API key (``FREELLM_API_KEY``).
        base_url: The router's OpenAI-compatible endpoint (``FREELLM_BASE_URL``),
            e.g. ``http://localhost:3001/v1``.
        model: The model id sent on every request. Defaults to ``"auto"`` so
            the router performs automatic model selection.
        timeout: Per-request timeout in seconds.
        max_retries: Extra attempts after a network failure.
        backoff: Sleep schedule between network retries.
        sleep: Sleep function (injectable for tests).
        event_sink: Optional ``(model, reason)`` callback fired after each
            successful completion with the model actually used (the model the
            router reports, or ``"auto"`` when the router reports none).

    Raises:
        LLMError: When no API key or base URL is supplied.
    """

    name = FREELLM_PROVIDER_NAME

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = "auto",
        base_url: str | None = None,
        timeout: int = DEFAULT_LLM_REQUEST_TIMEOUT,
        max_retries: int = DEFAULT_LLM_NETWORK_MAX_RETRIES,
        backoff: tuple[int, ...] = DEFAULT_LLM_NETWORK_RETRY_BACKOFF,
        sleep: Callable[[float], None] = time.sleep,
        event_sink: ModelSink | None = None,
    ) -> None:
        if not api_key:
            raise LLMError("FreeLLM Router API key is required (FREELLM_API_KEY).")
        if not base_url:
            raise LLMError("FreeLLM Router base URL is required (FREELLM_BASE_URL).")
        self._api_key = api_key
        self._model = model or "auto"
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff = backoff
        self._sleep = sleep
        self._event_sink = event_sink
        self._last_model = self._model

    @property
    def model(self) -> str:
        """Return the model id this provider requests on every call."""
        return self._model

    @property
    def base_url(self) -> str:
        """Return the gateway endpoint URL."""
        return self._base_url

    @property
    def timeout(self) -> int:
        """Return the per-request timeout in seconds."""
        return self._timeout

    @property
    def last_model(self) -> str:
        """Return the model used by the most recent successful call."""
        return self._last_model

    def complete(self, messages: list[ToolMessage], **kwargs: Any) -> str:
        """Send a chat-completions request and return the completion text.

        The request uses the standard OpenAI chat-completions shape so any
        OpenAI-compatible gateway (FreeLLM Router included) can serve it. The
        request always names ``model="auto"`` (unless overridden via kwargs).

        Transient network failures are retried with the same request up to
        ``max_retries`` times. HTTP error responses and malformed replies are
        raised immediately without retry.

        Raises:
            LLMStatusError: When the gateway answers with an HTTP error status.
            LLMNetworkError: When the gateway cannot be reached and retries are
                exhausted.
            LLMError: When the gateway returns bad data.
        """
        payload = {
            "model": kwargs.get("model", self._model),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": kwargs.get("temperature", DEFAULT_LLM_TEMPERATURE),
            "max_tokens": kwargs.get("max_tokens", DEFAULT_LLM_MAX_TOKENS),
        }
        attempt = 0
        while True:
            try:
                data = post_json(
                    f"{self._base_url}/chat/completions",
                    payload,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    timeout=kwargs.get("timeout", self._timeout),
                )
                return self._handle_success(data)
            except LLMNetworkError:
                attempt += 1
                if attempt > self._max_retries:
                    raise
                delay = self._backoff[min(attempt - 1, len(self._backoff) - 1)]
                self._sleep(delay)

    def _handle_success(self, data: dict[str, Any]) -> str:
        """Extract the completion and publish the model actually used."""
        try:
            content = str(data["choices"][0]["message"].get("content") or "").strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected LLM gateway response shape: {data}") from exc
        reported = _reported_model(data)
        self._last_model = reported if reported is not None else self._model
        if self._event_sink is not None:
            self._event_sink(self._last_model, _AUTO_ROUTER_REASON)
        return content


def _reported_model(data: dict[str, Any]) -> str | None:
    """Return the model name the router reports, when it reports one.

    OpenAI-compatible responses may carry the resolved model id at the top
    level (``{"model": "gpt-oss-120b-groq", ...}``). The client never guesses:
    it shows the reported name only when it is present, and otherwise falls
    back to the ``model="auto"`` label.
    """
    model = data.get("model")
    if isinstance(model, str) and model.strip():
        return model.strip()
    return None
