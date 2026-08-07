"""Business listing navigation.

BusinessNavigator opens a BusinessReference's listing page in an existing
browser page and waits for the business details to render before returning the
page for extraction. Navigation failures raise ExtractionException so callers
can skip the affected business and continue processing the rest.
"""

import logging

from playwright.sync_api import Page

from app.config.logging_config import get_logger
from app.config.settings import Settings
from app.exceptions import ExtractionException
from app.models.business_reference import BusinessReference

DETAIL_CONTAINER_SELECTORS = (
    '[role="main"]',
    'h1[dir="ltr"]',
    '[data-attrid="title"]',
)

OPEN_ATTEMPTS = 2


class BusinessNavigator:
    """Navigate to a business listing and wait for it to be ready.

    Args:
        settings: Application settings; the navigation and detail wait
            timeouts come from ``settings.timeout``.
        logger: Optional logger; a package logger is used when omitted.
    """

    def __init__(self, settings: Settings, logger: logging.Logger | None = None) -> None:
        self._settings = settings
        self._logger = logger or get_logger("navigator")

    def open(self, reference: BusinessReference, page: Page) -> Page:
        """Open the reference's listing on the given page.

        A failed navigation or a detail container that never renders is
        retried once before raising, so a slow page load does not drop a
        business.

        Args:
            reference: The business listing to open.
            page: The browser page to navigate.

        Returns:
            The page, ready for extraction once the business details load.

        Raises:
            ExtractionException: When the listing URL is missing, navigation
                fails, or the business details never render (for example a
                removed listing).
        """
        url = reference.listing_url
        if not url:
            raise ExtractionException(f"Cannot open '{reference.business_name}': no listing URL.")
        last_error: Exception | None = None
        for attempt in range(1, OPEN_ATTEMPTS + 1):
            try:
                page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self._settings.timeout,
                )
                self._wait_for_details(page, reference)
                self._logger.info("Business opened.")
                return page
            except Exception as exc:
                last_error = exc
                self._logger.warning(
                    "Open attempt %d/%d failed for '%s': %s",
                    attempt,
                    OPEN_ATTEMPTS,
                    reference.business_name,
                    exc,
                )
        raise ExtractionException(
            f"Failed to open '{reference.business_name}' at {url}: {last_error}"
        )

    def _wait_for_details(self, page: Page, reference: BusinessReference) -> None:
        """Wait for any configured business detail container to render."""
        timeout = max(self._settings.timeout // len(DETAIL_CONTAINER_SELECTORS), 1)
        for selector in DETAIL_CONTAINER_SELECTORS:
            try:
                page.locator(selector).wait_for(timeout=timeout)
                return
            except Exception as exc:
                self._logger.debug(
                    "Detail container '%s' not found for '%s': %s",
                    selector,
                    reference.business_name,
                    exc,
                )
        raise ExtractionException(
            f"Business page for '{reference.business_name}' did not load its details."
        )
