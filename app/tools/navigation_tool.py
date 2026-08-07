"""Navigation tool.

``NavigationTool`` gives the agent a generic way to move the shared browser
page to a URL. It goes through ``BrowserManager.navigate_to`` so it reuses the
existing page manager, including its load-waiting and (retry) behaviour. The
tool is deliberately thin: it carries no search or extraction logic.
"""

from typing import Any

from app.tools.base import Tool, ToolResult


class NavigationTool(Tool):
    """Navigate the shared browser page to a URL."""

    name = "navigation"
    description = "Navigate the browser to a given URL and wait for it to load."

    def run(self, url: str, **kwargs: Any) -> ToolResult:
        """Open the given URL in the shared browser page.

        Args:
            url: The absolute URL to navigate to.

        Returns:
            A ToolResult whose ``data`` holds the ``url`` that was opened.
        """
        if not url or not str(url).strip():
            return ToolResult.fail("A url argument is required.")
        url = str(url).strip()
        browser = self.context.browser
        if browser is None:
            return ToolResult.fail("No browser is available for navigation.")
        page = self.context.get_page()
        if page is None:
            return ToolResult.fail("No browser page is available for navigation.")
        try:
            if hasattr(browser, "navigate_to"):
                browser.navigate_to(url)
            else:
                page.goto(url, wait_until="load", timeout=self.settings.timeout)
        except Exception as exc:  # pragma: no cover - defensive catch-all
            return ToolResult.fail(f"Navigation to '{url}' failed: {exc}")
        self._logger.info("Navigation complete: %s", url)
        return ToolResult.ok(url=url)
