"""Business extraction tool.

``BusinessExtractionTool`` opens each collected business listing and extracts
the full detail set — name, phone, email, website, location, rating — using
the existing ``BusinessDetailsTool``. It is the agent-facing alias for the
detail extraction stage of the pipeline.
"""

from typing import Any

from app.models.lead import Lead
from app.tools.base import Tool, ToolContext, ToolResult
from app.tools.business_details_tool import BusinessDetailsTool


class BusinessExtractionTool(Tool):
    """Extract detailed information from every collected business."""

    name = "business_extraction"
    description = (
        "Open each business listing and extract detailed information "
        "including phone, email, website, location, and rating."
    )

    def __init__(self, context: ToolContext | None = None) -> None:
        super().__init__(context)
        self._delegate = BusinessDetailsTool(context=context)

    def run(
        self,
        references: list[Any] | None = None,
        leads: list[Lead] | None = None,
        search_query: str = "",
        **kwargs: Any,
    ) -> ToolResult:
        """Extract detailed information for every business.

        Args:
            references: The business references to open. When omitted and
                ``leads`` are provided, references are rebuilt from each
                lead's source URL.
            leads: Optional leads; provided to rebuild references and to
                preserve already-collected data.
            search_query: The query that discovered the businesses.

        Returns:
            A ToolResult whose ``data`` holds the extracted ``leads`` and a
            ``details`` list with per-business supplemental information.
        """
        return self._delegate.run(
            references=references,
            leads=leads,
            search_query=search_query,
            **kwargs,
        )
