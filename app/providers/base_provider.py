"""Search provider contract.

BaseProvider defines the interface every search provider implements. Concrete
providers (Google Maps, Bing Maps, Yelp, ...) inherit from SearchProvider,
which extends this contract with shared behaviour. No search logic lives here.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from app.browser.browser_manager import BrowserManager
from app.config.logging_config import get_logger
from app.config.settings import Settings
from app.models.search_plan import SearchPlan


class BaseProvider(ABC):
    """Abstract contract implemented by every search provider."""

    name: str = ""

    def __init__(
        self,
        browser: BrowserManager,
        plan: SearchPlan,
        settings: Settings,
        logger: logging.Logger | None = None,
    ) -> None:
        self._browser = browser
        self._plan = plan
        self._settings = settings
        self._logger = logger or get_logger("provider")

    @property
    def browser(self) -> BrowserManager:
        """Return the injected browser manager."""
        return self._browser

    @property
    def plan(self) -> SearchPlan:
        """Return the search plan the provider is executing."""
        return self._plan

    @property
    def settings(self) -> Settings:
        """Return the injected application settings."""
        return self._settings

    @property
    def logger(self) -> logging.Logger:
        """Return the injected logger."""
        return self._logger

    @property
    def query(self) -> str:
        """Return the search query text derived from the plan.

        The query is built from the business type and location so it is never
        hardcoded. For example, a plan with business type "software companies"
        and location "Karachi" produces "software companies in Karachi".
        """
        business_type = self._plan.business_type.strip()
        location = self._plan.location.strip() if self._plan.location else ""
        if location:
            return f"{business_type} in {location}"
        return business_type

    @abstractmethod
    def initialize(self) -> None:
        """Prepare the provider for searching."""

    @abstractmethod
    def search(self) -> list[str]:
        """Execute the search and return collected business page URLs."""

    @abstractmethod
    def collect_results(self) -> list[Any]:
        """Return the raw results gathered during the search."""

    @abstractmethod
    def close(self) -> None:
        """Release any resources held by the provider."""
