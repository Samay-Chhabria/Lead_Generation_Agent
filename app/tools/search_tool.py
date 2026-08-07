"""Search tool.

The agent-facing ``SearchTool`` wraps the existing provider-backed search so the
agent can request a search by business type and location. It delegates to
``GoogleMapsSearchTool``, which drives whatever provider is configured through
its lifecycle and returns the collected leads.
"""

from typing import Any

from app.tools.base import Tool, ToolContext, ToolResult
from app.tools.google_maps_tool import GoogleMapsSearchTool


class SearchTool(Tool):
    """Search a provider for businesses matching a business type and location."""

    name = "search"
    description = (
        "Search the configured provider for a business type in a location and "
        "collect the matching business leads."
    )

    def __init__(
        self,
        context: ToolContext | None = None,
        factory: Any = None,
    ) -> None:
        super().__init__(context)
        self._delegate = GoogleMapsSearchTool(context=context, factory=factory)

    def run(
        self,
        business_type: str,
        location: str,
        max_results: int = 0,
        **kwargs: Any,
    ) -> ToolResult:
        """Run the search through the underlying search tool.

        Args:
            business_type: The type of business to search for, e.g. "dentists".
            location: The target location, e.g. "Clifton, Karachi".
            max_results: Optional cap on the number of leads to collect. Zero
                means use the configured default.

        Returns:
            A ToolResult whose ``data`` holds ``leads``, ``references``,
            ``business_links``, ``provider``, and ``query``.
        """
        return self._delegate.run(
            business_type=business_type,
            location=location,
            max_results=max_results,
            **kwargs,
        )
