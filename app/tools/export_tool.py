"""Export tool.

``ExportTool`` is the agent-facing alias for the final deliverable stage: it
writes the collected, processed leads to an Excel workbook using the existing
``LeadExporterTool``. Its result path feeds the execution summary and the GUI
download button.
"""

from typing import Any

from app.models.lead import Lead
from app.tools.base import Tool, ToolContext, ToolResult
from app.tools.exporter_tool import LeadExporterTool


class ExportTool(Tool):
    """Export collected leads to an Excel workbook."""

    name = "export"
    description = "Export the collected leads to an Excel workbook file."

    def __init__(self, context: ToolContext | None = None) -> None:
        super().__init__(context)
        self._delegate = LeadExporterTool(context=context)

    def run(
        self,
        leads: list[Lead] | None = None,
        business_type: str = "businesses",
        location: str | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Export the given leads to a workbook.

        Args:
            leads: The processed leads to write.
            business_type: Business category used for the filename.
            location: Optional location used for the filename.

        Returns:
            A ToolResult whose ``data`` holds the output ``path`` and the
            ``exported_count``.
        """
        return self._delegate.run(
            leads=leads,
            business_type=business_type,
            location=location,
            **kwargs,
        )
