"""Yelp search provider (extension point).

``YelpProvider`` is the clean extension point for the Yelp backend. It inherits
all shared provider behaviour from ``SearchProvider`` and currently only
provides the provider-specific contract: the search is a no-op that logs a
clear message until a real implementation replaces it.

To implement this provider, override the provider-specific parts only:

- ``search()``: drive the browser session through the Yelp workflow
  (navigation, search, results, pagination) and fill ``self._references`` and
  ``self._leads`` exactly like ``GoogleMapsProvider`` does. Everything else —
  plan handling, browser injection, page management, extraction reuse, and
  lifecycle — is already provided by ``BaseProvider``/``SearchProvider``.
"""

from typing import Any

from app.providers.search_provider import SearchProvider


class YelpProvider(SearchProvider):
    """Search Yelp for businesses described by a SearchPlan.

    Placeholder implementation: the class is registered so the rest of the
    application can select it by name, and a search logs a warning and returns
    no results instead of raising. Override ``search()`` to make it real.
    """

    name = "yelp"

    def search(self) -> list[str]:
        """Execute the search.

        Placeholder: logs that the provider is not implemented yet and returns
        no business page URLs so the pipeline can still run end-to-end.

        Returns:
            An empty list; no real search is performed.
        """
        self._logger.warning(
            "Provider '%s' is not implemented yet; no search performed.",
            self.name,
        )
        return []

    def collect_results(self) -> list[Any]:
        """Return raw results gathered during the search.

        Placeholder: returns nothing because no search was performed.
        """
        return []
