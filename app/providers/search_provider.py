"""Higher-level search provider abstraction.

SearchProvider extends BaseProvider with shared behaviour for searchable
business providers. Until concrete providers exist, it also serves as the
registered placeholder: its search() and collect_results() return empty
results so the pipeline can run end-to-end without performing any searches.
Concrete providers override these methods.
"""

from typing import Any

from app.providers.base_provider import BaseProvider


class SearchProvider(BaseProvider):
    """Base implementation for searchable business providers."""

    name: str = ""

    def initialize(self) -> None:
        """Log a successful initialization. Override for real setup work."""
        self._logger.info("Provider initialized successfully.")

    def search(self) -> list[str]:
        """Return collected business page URLs.

        Placeholder: returns no results and never performs a real search.
        """
        self._logger.warning(
            "Provider '%s' is a placeholder; no search performed.",
            self._plan.provider,
        )
        return []

    def collect_results(self) -> list[Any]:
        """Return raw results gathered during the search.

        Placeholder: returns nothing because no search was performed.
        """
        return []

    def close(self) -> None:
        """Release provider resources. Placeholder: nothing to release."""
        self._logger.info("Provider closed.")
