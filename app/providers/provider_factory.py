"""Provider factory.

Reads the provider name from a SearchPlan, resolves the provider class through
the registry, and instantiates it with its dependencies injected (browser
manager, settings, and logger). Unknown providers produce a meaningful
exception instead of a silent fallback.
"""

import logging

from app.browser.browser_manager import BrowserManager
from app.config.logging_config import get_logger
from app.config.settings import Settings, get_settings
from app.models.search_plan import SearchPlan
from app.providers.base_provider import BaseProvider
from app.providers.provider_registry import ProviderRegistry, provider_registry


class ProviderFactory:
    """Creates provider instances from a SearchPlan."""

    def __init__(
        self,
        registry: ProviderRegistry | None = None,
        settings: Settings | None = None,
        logger: logging.Logger | None = None,
        browser: BrowserManager | None = None,
    ) -> None:
        self._registry = registry or provider_registry
        self._settings = settings or get_settings()
        self._logger = logger or get_logger("provider")
        if browser is None:
            self._browser = BrowserManager(settings=self._settings, logger=self._logger)
            self._logger.info("Browser initialized.")
        else:
            self._browser = browser
        self._logger.info("ProviderFactory created.")

    @property
    def browser(self) -> BrowserManager:
        """Return the browser manager injected into created providers."""
        return self._browser

    @property
    def settings(self) -> Settings:
        """Return the settings used to configure created providers."""
        return self._settings

    def close(self) -> None:
        """Release the browser manager. Safe to call repeatedly."""
        self._browser.close()

    def create(self, plan: SearchPlan) -> BaseProvider:
        """Instantiate the provider selected by a search plan.

        Args:
            plan: The search plan whose provider field selects the provider.

        Returns:
            A configured provider instance with its dependencies injected.

        Raises:
            UnknownProviderError: When the plan's provider is not registered.
        """
        provider_class = self._registry.get(plan.provider)
        provider = provider_class(
            browser=self._browser,
            plan=plan,
            settings=self._settings,
            logger=self._logger,
        )
        self._logger.info("%s provider selected.", plan.provider)
        return provider
