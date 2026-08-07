"""Build the application's LLM gateway from application settings.

The application uses a single OpenAI-compatible gateway — FreeLLM Router — or
falls back to deterministic Offline Mode. :func:`create_llm_provider` returns
either the canonical :class:`~app.llm.providers.freellmrouter.FreeLLMRouterProvider`
(which asks for ``model="auto"`` on every request and lets the router perform
automatic model selection, retries, provider rotation, fallback, rate-limit
recovery, and load balancing) or, when the gateway is not configured, the
deterministic :class:`~app.llm.mock_provider.MockProvider`. The application
implements no client-side fallback chain and never names a concrete model.
"""

from app.config.constants import DEFAULT_LLM_REQUEST_TIMEOUT
from app.config.settings import Settings
from app.execution.execution_logger import get_execution_logger
from app.llm.base import LLMProvider
from app.llm.mock_provider import MockProvider
from app.llm.providers.freellmrouter import FreeLLMRouterProvider


def create_llm_provider(settings: Settings) -> LLMProvider:
    """Resolve the application's LLM gateway with automatic mode switching.

    Mode resolution:

    * **Offline Mode** — when ``ENABLE_LLM=false`` or the router API key is
      empty, returns the deterministic :class:`MockProvider`. The agent keeps
      using the parser, browser automation, and Excel export with no network
      calls and no runtime errors.
    * **AI Agent Mode** — otherwise returns a single
      :class:`~app.llm.providers.freellmrouter.FreeLLMRouterProvider` that
      sends ``model="auto"`` on every request. The router performs all model
      selection, retries, provider rotation, fallback, rate-limit recovery,
      and load balancing; the application never names a concrete model.

    Args:
        settings: Application configuration.

    Returns:
        The FreeLLM Router gateway or the offline deterministic provider.
    """
    if not settings.llm_enabled:
        return MockProvider()
    execution_logger = get_execution_logger()

    def publish_model(model_id: str, reason: str) -> None:
        execution_logger.llm_model_selected(model_id, reason)

    return FreeLLMRouterProvider(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        timeout=DEFAULT_LLM_REQUEST_TIMEOUT,
        event_sink=publish_model,
    )
