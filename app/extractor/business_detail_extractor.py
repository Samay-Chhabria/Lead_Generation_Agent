"""Business detail extraction.

BusinessDetailExtractor reads contact details from an opened business listing
page and returns a structured Lead. Every field is extracted defensively: a
missing or unreadable field becomes an empty string and never raises
(Requirement 7). External websites are never visited.
"""

import logging

from playwright.sync_api import Page

from app.config.logging_config import get_logger
from app.models.business_reference import BusinessReference
from app.models.lead import Lead

BUSINESS_NAME_SELECTORS = ("h1", '[data-attrid="title"]')
PHONE_SELECTORS = (
    'a[href^="tel:"]',
    "[data-phone-number]",
    'button[data-tooltip*="phone"]',
)
WEBSITE_SELECTORS = (
    '[data-attrid="website"] a',
    'a[data-item-id="authority"]',
    'a[href^="http"]',
)
LOCATION_SELECTORS = (
    '[data-attrid="address"]',
    'button[data-item-id="address"]',
)
EMAIL_SELECTORS = ('a[href^="mailto:"]',)

_MAPS_LINK_MARKERS = ("google.com/maps", "google.com/search")


class BusinessDetailExtractor:
    """Extract a structured Lead from an opened business page.

    Args:
        logger: Optional logger; a package logger is used when omitted.
    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or get_logger("extractor")

    def extract(
        self,
        page: Page,
        reference: BusinessReference,
        search_query: str = "",
    ) -> Lead:
        """Extract a Lead from the opened business page.

        Args:
            page: The business listing page, already opened and loaded.
            reference: The reference being processed; supplies the business
                name fallback, provider name, and source URL.
            search_query: The query that discovered this business.

        Returns:
            A Lead. Missing fields are empty strings; the method never raises
            because a field is missing.
        """
        name = self._extract_name(page, reference)
        phone = self._extract_phone(page)
        website = self._extract_website(page)
        location = self._extract_location(page)
        email = self._extract_email(page)
        self._log_missing(name, phone, website, location, email)
        self._logger.info("Business extracted.")
        lead = Lead(
            business_name=name,
            phone_number=phone,
            email=email,
            website=website,
            location=location,
            provider=reference.provider,
            search_query=search_query,
            source_url=reference.listing_url or "",
        )
        self._logger.info("Extraction complete.")
        return lead

    def _extract_name(self, page: Page, reference: BusinessReference) -> str:
        for selector in BUSINESS_NAME_SELECTORS:
            value = self._first_text(page, selector)
            if value:
                return value
        return reference.business_name or ""

    def _extract_phone(self, page: Page) -> str:
        value = self._first_attribute(page, 'a[href^="tel:"]', "href", prefix="tel:")
        if value:
            return value
        value = self._first_attribute(page, "[data-phone-number]", "data-phone-number")
        if value:
            return value
        value = self._first_text(page, 'button[data-tooltip*="phone"]')
        if value:
            return value
        return ""

    def _extract_website(self, page: Page) -> str:
        for selector in WEBSITE_SELECTORS:
            value = self._first_attribute(page, selector, "href")
            if value and not self._is_maps_link(value):
                return value
        return ""

    def _extract_location(self, page: Page) -> str:
        for selector in LOCATION_SELECTORS:
            value = self._first_text(page, selector)
            if value:
                return value
        return ""

    def _extract_email(self, page: Page) -> str:
        return self._first_attribute(page, 'a[href^="mailto:"]', "href", prefix="mailto:")

    def _log_missing(
        self,
        name: str,
        phone: str,
        website: str,
        location: str,
        email: str,
    ) -> None:
        if not name:
            self._logger.warning("Missing business name.")
        if not phone:
            self._logger.warning("Missing phone.")
        if not website:
            self._logger.warning("Missing website.")
        if not location:
            self._logger.warning("Missing location.")
        if not email:
            self._logger.warning("Missing email.")

    def _first_text(self, page: Page, selector: str) -> str:
        try:
            return page.locator(selector).first.inner_text().strip()
        except Exception:
            return ""

    def _first_attribute(self, page: Page, selector: str, attribute: str, prefix: str = "") -> str:
        try:
            value = page.locator(selector).first.get_attribute(attribute)
        except Exception:
            return ""
        if not value:
            return ""
        value = value.strip()
        if prefix and value.lower().startswith(prefix.lower()):
            value = value[len(prefix) :].strip()
        return value

    @staticmethod
    def _is_maps_link(value: str) -> bool:
        """Return True when the link is a Google Maps/Search internal link."""
        lowered = value.lower()
        return any(marker in lowered for marker in _MAPS_LINK_MARKERS)
