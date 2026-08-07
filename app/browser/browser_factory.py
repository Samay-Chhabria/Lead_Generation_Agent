"""Browser creation based on application settings.

The factory reads the application settings and returns a launched Playwright
browser of the configured type. Chromium is the default and the only engine
exercised in tests; Firefox and WebKit are supported by design for future
milestones. No search logic belongs here.
"""

import logging
from dataclasses import dataclass

from playwright.sync_api import Browser, BrowserType, Playwright, sync_playwright

from app.config.logging_config import get_logger
from app.config.settings import Settings
from app.exceptions.browser_exception import BrowserException


@dataclass(frozen=True, slots=True)
class LaunchResult:
    """A started Playwright runtime and the browser it launched."""

    playwright: Playwright
    browser: Browser


class BrowserFactory:
    """Launches a Playwright browser for the configured browser type."""

    def __init__(self, settings: Settings, logger: logging.Logger | None = None) -> None:
        self._settings = settings
        self._logger = logger or get_logger("browser")

    def launch(self) -> LaunchResult:
        """Start the Playwright runtime and launch the configured browser.

        Returns:
            The started Playwright runtime and launched browser.

        Raises:
            BrowserException: When the configured browser cannot be launched.
        """
        self._logger.info("Launching %s...", self._settings.browser_type)
        playwright = sync_playwright().start()
        try:
            browser_type = self._select_browser(playwright)
            slow_mo = self._settings.slow_mo
            if not self._settings.headless:
                slow_mo = slow_mo or 300
            browser = browser_type.launch(
                headless=self._settings.headless,
                timeout=self._settings.timeout,
                slow_mo=slow_mo,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-first-run",
                    "--disable-infobars",
                ],
            )
        except BrowserException:
            playwright.stop()
            raise
        except Exception as exc:
            playwright.stop()
            raise BrowserException(
                f"Failed to launch {self._settings.browser_type} browser: {exc}"
            ) from exc
        self._logger.info("Browser launched.")
        return LaunchResult(playwright=playwright, browser=browser)

    def _select_browser(self, playwright: Playwright) -> BrowserType:
        """Map the configured browser type to a Playwright browser engine."""
        browser_type = self._settings.browser_type
        if browser_type == "chromium":
            return playwright.chromium
        if browser_type == "firefox":
            return playwright.firefox
        if browser_type == "webkit":
            return playwright.webkit
        raise BrowserException(f"Unsupported browser type: '{browser_type}'.")
