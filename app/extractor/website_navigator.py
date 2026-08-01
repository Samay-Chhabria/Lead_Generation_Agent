"""Website navigation.

WebsiteNavigator opens a lead's website in an existing browser page and waits
for it to finish loading before returning the page for email discovery.
Redirects are followed automatically by the browser; navigation failures raise
ExtractionException so the enrichment pipeline can skip the affected lead and
continue processing the rest (Requirement 7).
"""

import logging
from urllib.parse import urlparse

from playwright.sync_api import Page

from app.config.logging_config import get_logger
from app.config.settings import Settings
from app.exceptions import ExtractionException
from app.models.lead import Lead

SUPPORTED_SCHEMES = ("http", "https")
DEFAULT_SCHEME = "https://"


class WebsiteNavigator:
    """Open a lead's website and wait for it to finish loading.

    Args:
        settings: Application settings; the navigation timeout comes from
            ``settings.timeout``.
        logger: Optional logger; a package logger is used when omitted.
    """

    def __init__(self, settings: Settings, logger: logging.Logger | None = None) -> None:
        self._settings = settings
        self._logger = logger or get_logger("navigator")

    def open(self, lead: Lead, page: Page) -> Page:
        """Open the lead's website on the given page.

        Args:
            lead: The lead whose website should be opened. Leads without a
                website are skipped by the caller.
            page: The browser page to navigate.

        Returns:
            The page once the website has fully loaded.

        Raises:
            ExtractionException: When the website URL is missing or invalid,
                navigation fails, redirects never settle, or the page times
                out.
        """
        url = self.normalize_url(lead.website)
        if not url:
            raise ExtractionException(
                f"Cannot open website for '{lead.business_name}': invalid URL " f"'{lead.website}'."
            )
        return self.open_url(url, page)

    def open_url(self, url: str, page: Page) -> Page:
        """Open an arbitrary http(s) URL and wait for it to finish loading.

        Args:
            url: The website URL to navigate to.
            page: The browser page to navigate.

        Returns:
            The page once the website has fully loaded.

        Raises:
            ExtractionException: When the URL is invalid, navigation fails,
                redirects never settle, or the page times out.
        """
        normalized = self.normalize_url(url)
        if not normalized:
            raise ExtractionException(f"Cannot open website: invalid URL '{url}'.")
        self._logger.info("Opening website %s.", normalized)
        try:
            page.goto(normalized, wait_until="load", timeout=self._settings.timeout)
        except Exception as exc:
            raise ExtractionException(f"Failed to open website at {normalized}: {exc}") from exc
        self._logger.info("Website %s loaded.", normalized)
        return page

    def normalize_url(self, url: str) -> str:
        """Return a navigable http(s) URL or an empty string when invalid."""
        candidate = (url or "").strip()
        if not candidate:
            return ""
        if "://" not in candidate:
            candidate = f"{DEFAULT_SCHEME}{candidate}"
        parsed = urlparse(candidate)
        if parsed.scheme.lower() not in SUPPORTED_SCHEMES or not parsed.netloc:
            return ""
        return candidate
