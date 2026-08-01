"""Google Maps search provider.

GoogleMapsProvider is the first concrete search provider. It drives a real
browser session: it opens Google Maps, submits the search query derived from
the SearchPlan, discovers the business listings with the ResultCollector, and
then opens each listing to extract a structured Lead. Extraction failures for
one business never stop the remaining businesses (Requirement 7).
"""

from typing import Any

from playwright.sync_api import Locator, Page

from app.exceptions.provider_exception import (
    ProviderElementNotFoundError,
    ProviderNavigationError,
    ProviderSearchError,
)
from app.extractor.business_detail_extractor import BusinessDetailExtractor
from app.extractor.business_navigator import BusinessNavigator
from app.models.business_reference import BusinessReference
from app.models.lead import Lead
from app.providers.base_provider import BaseProvider
from app.providers.result_collector import ResultCollector

GOOGLE_MAPS_URL = "https://www.google.com/maps"
SEARCH_INPUT_SELECTORS = ("#searchboxinput", 'input[aria-label="Search Google Maps"]')
RESULTS_CONTAINER_SELECTORS = ('div[role="feed"]', '[aria-label*="Results for"]')


class GoogleMapsProvider(BaseProvider):
    """Search Google Maps for businesses described by a SearchPlan."""

    name = "google_maps"

    def __init__(
        self,
        browser,
        plan,
        settings,
        logger=None,
        navigator: BusinessNavigator | None = None,
        extractor: BusinessDetailExtractor | None = None,
    ) -> None:
        super().__init__(browser, plan, settings, logger)
        self._page: Page | None = None
        self._references: list[BusinessReference] = []
        self._leads: list[Lead] = []
        self._navigator = navigator
        self._extractor = extractor

    @property
    def page(self) -> Page | None:
        """Return the page the provider is working on, if any."""
        return self._page

    @property
    def references(self) -> list[BusinessReference]:
        """Return the business references discovered by the last search."""
        return list(self._references)

    @property
    def leads(self) -> list[Lead]:
        """Return the leads extracted from the last search's references."""
        return list(self._leads)

    def initialize(self) -> None:
        """Launch the browser (if needed) and create a configured page."""
        if not self._browser.is_running():
            self._browser.launch()
        self._page = self._browser.new_page()
        self._page.set_default_timeout(self._settings.timeout)
        self._logger.info("Provider initialized successfully.")

    def search(self) -> list[str]:
        """Open Google Maps, run the search, and extract business leads.

        Returns:
            An empty list: business page URLs are collected in a later
            milestone. The discovered references and extracted leads are
            available via the `references` and `leads` properties.

        Raises:
            ProviderNavigationError: When Google Maps cannot be opened.
            ProviderElementNotFoundError: When the search input is missing.
            ProviderSearchError: When the search cannot be submitted or the
                results never load.
        """
        page = self._require_page()
        self._logger.info("Opening Google Maps.")
        self._navigate(page)
        self._logger.info("Google Maps opened.")
        self._logger.info("Searching %s", self.query)
        self._submit_search(page)
        self._logger.info("Waiting for results...")
        self._wait_for_results(page)
        self._collect_references(page)
        self._extract_leads(page)
        self._logger.info("Search completed.")
        return []

    def collect_results(self) -> list[Any]:
        """Verify that results loaded and return the discovered references."""
        page = self._require_page()
        if any(page.locator(selector).count() > 0 for selector in RESULTS_CONTAINER_SELECTORS):
            self._logger.info("Results loaded successfully.")
            return list(self._references)
        self._logger.warning("Results container not visible; no results to collect.")
        return list(self._references)

    def close(self) -> None:
        """Release the page created by this provider.

        The browser is owned by the provider factory and is closed by the
        pipeline, so this method never touches it.
        """
        page, self._page = self._page, None
        if page is not None and not page.is_closed():
            try:
                page.close()
                self._logger.info("Provider page closed.")
            except Exception as exc:
                self._logger.warning("Failed to close provider page: %s", exc)
        self._logger.info("Provider closed.")

    def _require_page(self) -> Page:
        page = self._page
        if page is None or page.is_closed():
            raise ProviderSearchError(
                "No active page is available; call initialize() before searching."
            )
        return page

    def _navigate(self, page: Page) -> None:
        try:
            page.goto(
                GOOGLE_MAPS_URL,
                wait_until="domcontentloaded",
                timeout=self._settings.timeout,
            )
        except Exception as exc:
            raise ProviderNavigationError(f"Could not open Google Maps: {exc}") from exc

    def _submit_search(self, page: Page) -> None:
        self._logger.info("Submitting search.")
        search_input = self._find_search_input(page)
        try:
            search_input.fill(self.query)
            search_input.press("Enter")
        except Exception as exc:
            raise ProviderSearchError(f"Failed to submit search '{self.query}': {exc}") from exc

    def _find_search_input(self, page: Page) -> Locator:
        timeout = max(self._settings.timeout // len(SEARCH_INPUT_SELECTORS), 1)
        for selector in SEARCH_INPUT_SELECTORS:
            try:
                locator = page.locator(selector)
                locator.wait_for(timeout=timeout)
                return locator
            except Exception as exc:
                self._logger.debug("Search input selector '%s' not found: %s", selector, exc)
        raise ProviderElementNotFoundError(
            "Google Maps search input was not found within the timeout."
        )

    def _wait_for_results(self, page: Page) -> None:
        timeout = max(self._settings.timeout // len(RESULTS_CONTAINER_SELECTORS), 1)
        for selector in RESULTS_CONTAINER_SELECTORS:
            try:
                page.locator(selector).wait_for(timeout=timeout)
                self._logger.info("Results loaded successfully.")
                return
            except Exception as exc:
                self._logger.debug("Results selector '%s' not found: %s", selector, exc)
        raise ProviderSearchError(
            f"Search results did not load within the timeout for query '{self.query}'."
        )

    def _collect_references(self, page: Page) -> None:
        """Discover business references on the rendered results page.

        The collector stops at the plan's max_results or when scrolling stops
        producing new listings. Failures during discovery are handled inside
        the collector, which logs them and stops gracefully.
        """
        collector = ResultCollector(
            page=page,
            provider_name=self.name,
            max_results=self._plan.max_results,
            logger=self._logger,
        )
        self._references = collector.collect()
        self._logger.info("Total %d business references.", len(self._references))

    def _extract_leads(self, page: Page) -> None:
        """Open each discovered business and extract a structured Lead.

        A failure to open or extract one business is logged and skipped; the
        remaining businesses are always processed (Requirement 7).
        """
        navigator = self._navigator or BusinessNavigator(
            settings=self._settings, logger=self._logger
        )
        extractor = self._extractor or BusinessDetailExtractor(logger=self._logger)
        self._logger.info("%d businesses discovered.", len(self._references))
        self._leads = []
        for index, reference in enumerate(self._references, start=1):
            self._logger.info("Opening Business %d.", index)
            try:
                page = navigator.open(reference, page)
                lead = extractor.extract(page, reference, search_query=self.query)
            except Exception as exc:
                self._logger.warning(
                    "Failed to extract '%s': %s; skipping.",
                    reference.business_name,
                    exc,
                )
                continue
            self._leads.append(lead)
            self._logger.info("Business extracted successfully.")
        self._logger.info("%d businesses processed.", len(self._references))
