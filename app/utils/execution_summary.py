"""Execution summary rendering.

ExecutionSummary turns an ExecutionResult into a professional, boxed console
summary printed at the end of every run (Requirement 11). The same component
handles both successful runs and failures so the user always sees the search
query, the counts, and the elapsed time. ``to_lines`` produces the plain lines
so the terminal timeline subscriber and the standalone pipeline can share one
formatting source.
"""

from typing import Any

from rich.console import Console

from app.models.execution_result import ExecutionResult

_PROVIDER_LABELS = {
    "google": "Google",
    "google_maps": "Google Maps",
    "bing_maps": "Bing Maps",
    "yellow_pages": "Yellow Pages",
    "yelp": "Yelp",
}


class ExecutionSummary:
    """Render the end-of-run execution summary to the console."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize the summary renderer with an optional console."""
        self._console = console or Console()

    def print(self, result: ExecutionResult) -> None:
        """Print the summary for an ExecutionResult."""
        for line in self.to_lines(result):
            self._console.print(line)

    def to_lines(self, result: ExecutionResult) -> list[str]:
        """Return the summary lines for an ExecutionResult."""
        if result.success:
            return self._success_lines(result)
        return self._failure_lines(result)

    def _success_lines(self, result: ExecutionResult) -> list[str]:
        lines = [
            "=" * 40,
            "Lead Generation Completed Successfully",
            "=" * 40,
            self._line("Search Query", result.search_query),
            self._line("Business Type", result.business_type),
            self._line("Location", result.location or "-"),
            self._line("Provider", self._provider_label(result.provider)),
            self._line("Businesses Found", result.collected_leads),
            self._line("Documents Removed", result.duplicates_removed),
            self._line("Leads Exported", result.processed_leads),
            self._line("Output File", result.excel_output_path or "-"),
            self._line("Execution Time", f"{result.execution_time:.1f} seconds"),
            self._line("Status", "SUCCESS"),
            "=" * 40,
        ]
        return lines

    def _failure_lines(self, result: ExecutionResult) -> list[str]:
        lines = [
            "=" * 40,
            "Lead Generation Failed",
            "=" * 40,
            self._line("Search Query", result.search_query),
            self._line("Businesses Found", result.collected_leads),
            self._line("Leads Exported", result.processed_leads),
            self._line("Execution Time", f"{result.execution_time:.1f} seconds"),
            self._line("Status", "FAILED"),
            "=" * 40,
        ]
        return lines

    @staticmethod
    def _line(label: str, value: Any) -> str:
        return f"{label}: {value}"

    @classmethod
    def _provider_label(cls, provider: str) -> str:
        return _PROVIDER_LABELS.get(provider, provider or "-")
