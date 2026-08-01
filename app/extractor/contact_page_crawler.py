"""Contact and about page crawling.

ContactPageCrawler enriches the email discovery of a website. When the
homepage holds no email, it follows navigation links whose text mentions
contact, about, support, or reach topics (e.g. "Contact Us", "About", "Get in
Touch") and repeats the discovery on each opened page. The crawl is bounded by
a maximum depth and a maximum number of visited pages per website so a single
site can never stall enrichment.
"""

import logging
from collections.abc import Iterator
from urllib.parse import urljoin

from playwright.sync_api import Page

from app.config.logging_config import get_logger
from app.config.settings import Settings
from app.extractor.email_discovery_engine import EmailDiscoveryEngine
from app.extractor.website_navigator import WebsiteNavigator
from app.models.lead import Lead

LINK_SELECTOR = "a[href]"
LINK_KEYWORDS = (
    "contact us",
    "contact",
    "about us",
    "about",
    "support",
    "get in touch",
    "reach us",
)
MAX_DEPTH = 2
MAX_PAGES = 5


class ContactPageCrawler:
    """Discover an email by crawling a website's contact and about pages.

    Args:
        settings: Application settings passed to the WebsiteNavigator.
        navigator: Optional WebsiteNavigator; one is created when omitted.
        engine: Optional EmailDiscoveryEngine; one is created when omitted.
        logger: Optional logger; a package logger is used when omitted.
    """

    def __init__(
        self,
        settings: Settings,
        navigator: WebsiteNavigator | None = None,
        engine: EmailDiscoveryEngine | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._settings = settings
        self._navigator = navigator or WebsiteNavigator(settings, logger=logger)
        self._engine = engine or EmailDiscoveryEngine(logger=logger)
        self._logger = logger or get_logger("crawler")

    def enrich(self, lead: Lead, page: Page) -> str:
        """Open the lead's website and discover an email on it.

        Combines the initial website navigation with the contact-page crawl so
        callers can enrich a lead in a single step.

        Args:
            lead: The lead whose website should be scanned.
            page: The browser page to navigate.

        Returns:
            The first valid email found, or an empty string when none exists.

        Raises:
            ExtractionException: When the lead's website cannot be opened.
        """
        self._navigator.open(lead, page)
        return self.crawl(lead, page)

    def crawl(self, lead: Lead, page: Page) -> str:
        """Discover an email on the lead's website, starting from its homepage.

        Args:
            lead: The lead whose website is being scanned. The page must
                already show the lead's website.
            page: The browser page, currently holding the lead's homepage.

        Returns:
            The first valid email found, or an empty string when the homepage
            and its contact/about pages hold none.
        """
        self._logger.info("Homepage scanned for '%s'.", lead.business_name)
        email = self._engine.discover(page)
        if email:
            self._logger.info("Email discovered for '%s'.", lead.business_name)
            return email

        visited: set[str] = set()
        current_url = self._page_url(page)
        if current_url:
            visited.add(current_url)
        pages_visited = 1
        queue: list[Page] = [page]

        for _depth in range(1, MAX_DEPTH + 1):
            expanded = [(current, list(self._candidate_urls(current))) for current in queue]
            queue = []
            for current, links in expanded:
                for url in links:
                    if url in visited:
                        continue
                    if pages_visited >= MAX_PAGES:
                        break
                    visited.add(url)
                    pages_visited += 1
                    self._logger.info("Contact page found: %s.", url)
                    try:
                        self._navigator.open_url(url, current)
                    except Exception as exc:
                        self._logger.warning("Website failed: %s (%s).", url, exc)
                        continue
                    email = self._engine.discover(current)
                    if email:
                        self._logger.info("Email discovered for '%s'.", lead.business_name)
                        return email
                    queue.append(current)
            if not queue:
                break

        self._logger.info("No email found for '%s'.", lead.business_name)
        return ""

    def _candidate_urls(self, page: Page) -> Iterator[str]:
        """Yield absolute, unique URLs of candidate navigation links."""
        seen: set[str] = set()
        for link in page.locator(LINK_SELECTOR).all():
            href = link.get_attribute("href")
            if not href:
                continue
            text = ""
            try:
                text = link.inner_text()
            except Exception:
                pass
            if not self._is_candidate_link(text, href):
                continue
            url = self._absolute_url(page, href)
            if url and url not in seen:
                seen.add(url)
                yield url

    def _is_candidate_link(self, text: str, href: str) -> bool:
        haystack = f"{text} {href}".lower()
        return any(keyword in haystack for keyword in LINK_KEYWORDS)

    def _absolute_url(self, page: Page, href: str) -> str:
        href = href.strip()
        if href.startswith(("http://", "https://")):
            return href
        base = self._page_url(page)
        if not base:
            return href
        return urljoin(base, href)

    def _page_url(self, page: Page) -> str:
        try:
            url = page.url
        except Exception:
            return ""
        return url or ""
