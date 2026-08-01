"""Page-level navigation helpers.

The page manager operates on the active page of a browser session: it returns
the page, navigates to URLs, waits for page loads, and closes pages safely. No
search or extraction logic belongs here.
"""

import logging

from playwright.sync_api import Page

from app.browser.browser_session import BrowserSession
from app.config.logging_config import get_logger
from app.config.settings import Settings
from app.exceptions.browser_exception import BrowserException


class PageManager:
    """Navigates and manages the active page of a browser session."""

    def __init__(
        self,
        session: BrowserSession,
        settings: Settings,
        logger: logging.Logger | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._logger = logger or get_logger("browser")

    def active_page(self) -> Page:
        """Return the active page.

        Raises:
            BrowserException: When the session has no usable active page.
        """
        page = self._session.page
        if page is None or page.is_closed():
            raise BrowserException("No active page is available.")
        return page

    def navigate(self, url: str) -> None:
        """Navigate the active page to a URL and wait for it to load.

        Raises:
            BrowserException: When navigation times out or otherwise fails.
        """
        page = self.active_page()
        try:
            page.goto(url, wait_until="load", timeout=self._settings.timeout)
        except Exception as exc:
            raise BrowserException(f"Navigation to '{url}' failed: {exc}") from exc
        self._logger.info("Navigated to %s", url)

    def wait_for_load(self) -> None:
        """Wait for the active page to reach the 'load' state.

        Raises:
            BrowserException: When the page load times out.
        """
        page = self.active_page()
        try:
            page.wait_for_load_state("load", timeout=self._settings.timeout)
        except Exception as exc:
            raise BrowserException(f"Waiting for page load failed: {exc}") from exc
        self._logger.info("Page load reached.")

    def close_page(self) -> None:
        """Close the active page. Safe to call when no page exists."""
        self._session.close_page()
