"""Unified LLM gateway for the lead generation agent.

The application is model-agnostic: it talks to exactly one OpenAI-compatible
gateway — FreeLLM Router — configured with ``FREELLM_BASE_URL`` and
``FREELLM_API_KEY``. Every request asks for ``model="auto"`` and the router
performs automatic model selection, retries, provider rotation, fallback,
rate-limit recovery, and load balancing. The application implements no
client-side fallback chain and never names a concrete model. When the gateway
is not configured, the agent runs in Offline Mode using the deterministic
``MockProvider``.
"""

from app.llm.base import (
    BaseLLM,
    LLMError,
    LLMNetworkError,
    LLMProvider,
    LLMResponseError,
    LLMStatusError,
    LLMToolCall,
    ToolMessage,
)
from app.llm.factory import create_llm_provider
from app.llm.mock_provider import MockProvider
from app.llm.providers.freellmrouter import FreeLLMRouterProvider

__all__ = [
    "BaseLLM",
    "LLMError",
    "LLMNetworkError",
    "LLMProvider",
    "LLMResponseError",
    "LLMStatusError",
    "LLMToolCall",
    "ToolMessage",
    "create_llm_provider",
    "FreeLLMRouterProvider",
    "MockProvider",
]
