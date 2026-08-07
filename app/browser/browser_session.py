"""Encapsulates the resources of one browser session.

A session owns the Playwright runtime, the launched browser, a browser
context, and an active page. It is the single place responsible for creating
and tearing down those resources so the rest of the application never touches
raw Playwright lifecycle calls. Closing is idempotent and each resource is
released independently so one failure cannot leak the others.
"""

import logging

from playwright.sync_api import Browser, BrowserContext, Page

from app.browser.browser_factory import BrowserFactory, LaunchResult
from app.config.logging_config import get_logger
from app.exceptions.browser_exception import BrowserException


class BrowserSession:
    """Owns the Playwright resources for a single browser session."""

    def __init__(self, factory: BrowserFactory, logger: logging.Logger | None = None) -> None:
        self._factory = factory
        self._logger = logger or get_logger("browser")
        self._result: LaunchResult | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._closed = False

    @property
    def browser(self) -> Browser | None:
        """Return the launched browser, or None when not open."""
        return self._result.browser if self._result is not None else None

    @property
    def context(self) -> BrowserContext | None:
        """Return the active context, or None when not open."""
        return self._context

    @property
    def page(self) -> Page | None:
        """Return the active page, or None when not open."""
        return self._page

    @property
    def is_open(self) -> bool:
        """Return True while the session owns live browser resources."""
        return not self._closed and self._result is not None

    def open(self) -> Page:
        """Launch the browser, create a context, and open the first page.

        Returns:
            The first page of the session.

        Raises:
            BrowserException: When the session is already open.
        """
        if self.is_open:
            raise BrowserException("Browser session is already open.")
        self._closed = False
        self._result = self._factory.launch()
        try:
            self._context = self._create_context()
            self._page = self.new_page()
        except Exception:
            self.close()
            raise
        return self._page

    def new_page(self) -> Page:
        """Create a new page and make it the active page.

        Raises:
            BrowserException: When the session has no context yet.
        """
        if self._context is None:
            raise BrowserException("No browser context is available; open the session first.")
        self._page = self._context.new_page()
        self._logger.info("New page created.")
        return self._page

    def close_page(self) -> None:
        """Close the active page and clear the reference."""
        page = self._page
        self._page = None
        if page is not None and not page.is_closed():
            try:
                page.close()
                self._logger.info("Page closed.")
            except Exception as exc:
                self._logger.warning("Failed to close page: %s", exc)

    def close(self) -> None:
        """Release all session resources. Safe to call multiple times."""
        if self._closed:
            return
        self._closed = True
        self.close_page()
        self._close_context()
        self._close_browser()
        self._logger.info("Browser closed.")

    def _create_context(self) -> BrowserContext:
        context = self._result.browser.new_context(locale="en-US")
        self._logger.info("Context created.")
        return context

    def _close_context(self) -> None:
        context = self._context
        self._context = None
        if context is not None:
            try:
                context.close()
            except Exception as exc:
                self._logger.warning("Failed to close context: %s", exc)

    def _close_browser(self) -> None:
        result = self._result
        self._result = None
        if result is not None:
            try:
                result.browser.close()
            except Exception as exc:
                self._logger.warning("Failed to close browser: %s", exc)
            try:
                result.playwright.stop()
            except Exception as exc:
                self._logger.warning("Failed to stop Playwright runtime: %s", exc)
