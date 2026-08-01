"""Browser lifecycle manager.

Coordinates the browser factory, session, and page manager behind a small
public API used by the rest of the application: launch(), new_page(),
active_page(), navigate_to(), close(), and is_running(). It tracks the
session state and prevents duplicate launches and duplicate closes.
"""

import logging

from playwright.sync_api import Page

from app.browser.browser_factory import BrowserFactory
from app.browser.browser_session import BrowserSession
from app.browser.page_manager import PageManager
from app.config.logging_config import get_logger
from app.config.settings import Settings, get_settings
from app.exceptions.browser_exception import BrowserException


class BrowserManager:
    """Public facade for the browser lifecycle."""

    def __init__(
        self,
        settings: Settings | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._logger = logger or get_logger("browser")
        self._session = BrowserSession(
            BrowserFactory(self._settings, logger=self._logger),
            logger=self._logger,
        )
        self._pages = PageManager(self._session, self._settings, logger=self._logger)

    def launch(self) -> Page:
        """Launch the browser and open the first page.

        Returns:
            The first page of the session.

        Raises:
            BrowserException: When the browser is already running.
        """
        if self.is_running():
            raise BrowserException("Browser is already running; close it before launching again.")
        return self._session.open()

    def new_page(self) -> Page:
        """Create a new page in the current session.

        Raises:
            BrowserException: When the browser is not running.
        """
        if not self.is_running():
            raise BrowserException("Browser is not running; call launch() first.")
        return self._session.new_page()

    def active_page(self) -> Page:
        """Return the active page of the current session.

        Raises:
            BrowserException: When there is no usable active page.
        """
        return self._pages.active_page()

    def navigate_to(self, url: str) -> None:
        """Navigate the active page to a URL.

        Raises:
            BrowserException: When the browser is not running or navigation fails.
        """
        if not self.is_running():
            raise BrowserException("Browser is not running; call launch() first.")
        self._pages.navigate(url)

    def close(self) -> None:
        """Close the browser and release all resources. Safe to call repeatedly."""
        if not self.is_running():
            self._logger.debug("Browser is not running; nothing to close.")
            return
        self._session.close()

    def is_running(self) -> bool:
        """Return True while the browser session is open."""
        return self._session.is_open
