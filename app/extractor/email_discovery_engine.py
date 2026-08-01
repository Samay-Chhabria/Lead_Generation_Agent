"""Email discovery from a loaded website.

EmailDiscoveryEngine scans a fully loaded page for an email address using a
fixed priority order: mailto links, visible page text, the footer, the header,
contact sections, and finally structured data (JSON-LD). Each strategy yields
candidate strings that are normalized by EmailValidator; the first valid
address wins. When nothing is found an empty string is returned so callers can
skip enrichment without failing (Requirement 7).
"""

import json
import logging
import re
from collections.abc import Iterator
from urllib.parse import unquote

from playwright.sync_api import Page

from app.config.logging_config import get_logger
from app.extractor.email_validator import EmailValidator

MAILTO_SELECTOR = 'a[href^="mailto:"]'
FOOTER_SELECTOR = "footer"
HEADER_SELECTOR = "header"
CONTACT_SELECTORS = (
    "#contact",
    ".contact",
    '[id*="contact" i]',
    '[class*="contact" i]',
)
STRUCTURED_DATA_SELECTOR = 'script[type="application/ld+json"]'

EMAIL_IN_TEXT_PATTERN = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
EMAIL_PATTERN = re.compile(EMAIL_IN_TEXT_PATTERN)


def _walk_email_values(node: object) -> Iterator[str]:
    """Yield string values found under any ``email`` key in JSON data."""
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(key, str) and key.lower() == "email":
                if isinstance(value, str):
                    yield value
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            yield item
            yield from _walk_email_values(value)
    elif isinstance(node, list):
        for item in node:
            yield from _walk_email_values(item)


class EmailDiscoveryEngine:
    """Discover an email address on a fully loaded page.

    Args:
        validator: Optional EmailValidator; a fresh one is created when
            omitted.
        logger: Optional logger; a package logger is used when omitted.
    """

    def __init__(
        self,
        validator: EmailValidator | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._validator = validator or EmailValidator()
        self._logger = logger or get_logger("discovery")

    def discover(self, page: Page) -> str:
        """Return the first valid email found on the page, or an empty string.

        Strategies run in priority order and each one may produce several
        candidates; the first address that passes validation wins.
        """
        strategies = (
            self._emails_from_mailto_links,
            self._emails_from_page_text,
            self._emails_from_footer,
            self._emails_from_header,
            self._emails_from_contact_sections,
            self._emails_from_structured_data,
        )
        for strategy in strategies:
            for candidate in strategy(page):
                email = self._validator.normalize(candidate)
                if email:
                    return email
        return ""

    def _emails_from_mailto_links(self, page: Page) -> Iterator[str]:
        for link in page.locator(MAILTO_SELECTOR).all():
            href = link.get_attribute("href")
            if not href:
                continue
            if not href.lower().startswith("mailto:"):
                continue
            address = href[7:].split("?", 1)[0].strip()
            if address:
                yield unquote(address)

    def _emails_from_page_text(self, page: Page) -> Iterator[str]:
        try:
            text = page.content()
        except Exception:
            return
        if not text:
            return
        yield from EMAIL_PATTERN.findall(text)

    def _emails_from_footer(self, page: Page) -> Iterator[str]:
        yield from self._emails_from_section(page, FOOTER_SELECTOR)

    def _emails_from_header(self, page: Page) -> Iterator[str]:
        yield from self._emails_from_section(page, HEADER_SELECTOR)

    def _emails_from_contact_sections(self, page: Page) -> Iterator[str]:
        for selector in CONTACT_SELECTORS:
            yield from self._emails_from_section(page, selector)

    def _emails_from_structured_data(self, page: Page) -> Iterator[str]:
        for script in page.locator(STRUCTURED_DATA_SELECTOR).all():
            try:
                text = script.inner_text()
            except Exception:
                continue
            try:
                payload = json.loads(text)
            except (TypeError, ValueError):
                continue
            yield from _walk_email_values(payload)

    def _emails_from_section(self, page: Page, selector: str) -> Iterator[str]:
        locator = page.locator(selector)
        try:
            present = locator.count() > 0
        except Exception:
            return
        if not present:
            return
        try:
            text = locator.first.inner_text()
        except Exception:
            return
        yield from EMAIL_PATTERN.findall(text or "")
