"""Summary tool.

``SummaryTool`` produces the final human-readable summary of a run. It is the
last tool the agent calls: it turns an ``ExecutionResult`` (and optionally the
leads that were exported) into a short, structured text the user can read and
the GUI can display. The summary is deterministic so it works offline with the
default mock LLM provider.
"""

from typing import Any

from app.models.execution_result import ExecutionResult
from app.models.lead import Lead
from app.tools.base import Tool, ToolResult


class SummaryTool(Tool):
    """Generate a human-readable summary of a lead generation run."""

    name = "summary"
    description = "Generate the final human-readable summary of the run."

    def run(
        self,
        result: ExecutionResult | None = None,
        leads: list[Lead] | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Build the summary text for a completed run.

        Args:
            result: The ExecutionResult describing the run.
            leads: Optional leads that were exported; used for extra detail
                such as how many carried emails or phones.

        Returns:
            A ToolResult whose ``data`` holds the ``summary`` text and a
            ``metrics`` dictionary with the key numbers.
        """
        result = result or ExecutionResult()
        leads = list(leads or [])
        lines: list[str] = []
        if result.success:
            lines.append("Lead generation completed successfully.")
        else:
            lines.append("Lead generation could not be completed.")
        if result.search_query:
            lines.append(f"Search query: {result.search_query}")
        if result.business_type:
            lines.append(f"Business type: {result.business_type}")
        if result.location:
            lines.append(f"Location: {result.location}")
        if result.provider:
            lines.append(f"Provider: {result.provider}")
        lines.append(f"Businesses found: {result.collected_leads}")
        lines.append(f"Businesses processed: {result.processed_leads}")
        lines.append(f"Duplicates removed: {result.duplicates_removed}")
        if leads:
            lines.append(f"Leads with email: {sum(1 for lead in leads if lead.has_email())}")
            lines.append(f"Leads with phone: {sum(1 for lead in leads if lead.has_phone())}")
        if result.excel_output_path is not None:
            lines.append(f"Excel workbook: {result.excel_output_path}")
        lines.append(f"Execution time: {result.execution_time:.1f} seconds")

        metrics = {
            "collected_leads": result.collected_leads,
            "processed_leads": result.processed_leads,
            "duplicates_removed": result.duplicates_removed,
            "execution_time": result.execution_time,
            "success": result.success,
        }
        self._logger.info("Summary generated.")
        return ToolResult.ok(summary="\n".join(lines), metrics=metrics)
