"""Page-level navigation helpers.

The page manager operates on the active page of a browser session: it returns
the page, navigates to URLs, waits for page loads, and closes pages safely. No
search or extraction logic belongs here.

Navigation is failure-recovery friendly: a failed navigation is retried once,
and after a successful load common consent dialogs are dismissed so a cookie
or GDPR banner never blocks the rest of the workflow.
"""

import logging

from playwright.sync_api import Page

from app.browser.browser_session import BrowserSession
from app.config.logging_config import get_logger
from app.config.settings import Settings
from app.exceptions.browser_exception import BrowserException

NAVIGATION_ATTEMPTS = 2
CONSENT_BUTTON_TEXTS = ("Accept all", "Accept", "I agree", "Agree", "Accept cookies")
CLICK_TIMEOUT_MS = 3_000


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

        The navigation is retried once before failing, and any consent dialog
        that appears after the load is dismissed.

        Raises:
            BrowserException: When navigation times out or otherwise fails.
        """
        page = self.active_page()
        last_error: Exception | None = None
        for attempt in range(1, NAVIGATION_ATTEMPTS + 1):
            try:
                page.goto(url, wait_until="load", timeout=self._settings.timeout)
                self.dismiss_consent_popups(page)
                self._logger.info("Navigated to %s", url)
                return
            except Exception as exc:
                last_error = exc
                self._logger.warning(
                    "Navigation attempt %d/%d to '%s' failed: %s",
                    attempt,
                    NAVIGATION_ATTEMPTS,
                    url,
                    exc,
                )
        raise BrowserException(f"Navigation to '{url}' failed: {last_error}")

    def dismiss_consent_popups(self, page: Page | None = None) -> bool:
        """Click the first matching consent button, if any dialog is present.

        A missing dialog is not an error: the method returns False and the
        caller continues. Each known label is tried with semantic and CSS
        locators so consent handling survives selector changes.

        Args:
            page: The page to scan; the active page is used when omitted.

        Returns:
            True when a consent dialog was accepted, False otherwise.
        """
        page = page or self.active_page()
        for text in CONSENT_BUTTON_TEXTS:
            if self._click_button_with_text(page, text):
                self._logger.info("Consent dialog accepted via '%s'.", text)
                return True
        self._logger.debug("No consent dialog detected; continuing.")
        return False

    def _click_button_with_text(self, page: Page, text: str) -> bool:
        """Try to click a button matching the given text; return whether it worked.

        The locator is checked for presence first so a page without a consent
        dialog is scanned quickly instead of waiting on each click timeout.
        """
        candidates = (
            page.get_by_role("button", name=text, exact=True),
            page.get_by_role("button", name=text),
            page.locator(f'button:has-text("{text}")'),
            page.locator(f'[role="button"]:has-text("{text}")'),
        )
        for locator in candidates:
            try:
                if locator.first.count() == 0:
                    continue
            except Exception:
                continue
            try:
                locator.first.click(timeout=CLICK_TIMEOUT_MS)
                return True
            except Exception as exc:
                self._logger.debug("Consent locator for '%s' not clickable: %s", text, exc)
        return False

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
