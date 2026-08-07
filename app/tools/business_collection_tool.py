"""Business collection tool.

``BusinessCollectionTool`` is the agent-facing alias for the collection stage
of a search: it collects the candidate business leads for a business type and
location. It delegates to the existing provider-backed search tool so the
collected leads, references, and business links match the deterministic
pipeline exactly.
"""

from typing import Any

from app.tools.base import Tool, ToolContext, ToolResult
from app.tools.google_maps_tool import GoogleMapsSearchTool


class BusinessCollectionTool(Tool):
    """Collect candidate businesses for a business type in a location."""

    name = "business_collection"
    description = (
        "Collect the candidate business leads for a business type in a "
        "location using the configured provider."
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
        """Collect candidate businesses.

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
