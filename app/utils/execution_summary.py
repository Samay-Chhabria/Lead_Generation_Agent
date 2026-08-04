"""Execution summary rendering.

ExecutionSummary turns an ExecutionResult into a professional, boxed console
summary printed at the end of every run (Requirement 11). The same component
handles both successful runs and failures so the user always sees the search
query, the counts, and the elapsed time.
"""

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
        if result.success:
            self._print_success(result)
        else:
            self._print_failure(result)

    def _print_success(self, result: ExecutionResult) -> None:
        self._console.print()
        self._console.print("=" * 40, style="bold green")
        self._console.print("Lead Generation Completed Successfully", style="bold green")
        self._console.print("=" * 40, style="bold green")
        self._line("Search Query", result.search_query)
        self._line("Business Type", result.business_type)
        self._line("Location", result.location or "-")
        self._line("Provider", self._provider_label(result.provider))
        self._line("Businesses Found", result.collected_leads)
        self._line("Documents Removed", result.duplicates_removed)
        self._line("Leads Exported", result.processed_leads)
        self._line("Output File", result.excel_output_path or "-")
        self._line("Execution Time", f"{result.execution_time:.1f} seconds")
        self._console.print("=" * 40, style="bold green")

    def _print_failure(self, result: ExecutionResult) -> None:
        self._console.print()
        self._console.print("=" * 40, style="bold red")
        self._console.print("Lead Generation Failed", style="bold red")
        self._console.print("=" * 40, style="bold red")
        self._line("Search Query", result.search_query)
        self._line("Businesses Found", result.collected_leads)
        self._line("Leads Exported", result.processed_leads)
        self._line("Execution Time", f"{result.execution_time:.1f} seconds")
        self._console.print("=" * 40, style="bold red")

    def _line(self, label: str, value: object) -> None:
        self._console.print(f"{label}: {value}")

    @classmethod
    def _provider_label(cls, provider: str) -> str:
        return _PROVIDER_LABELS.get(provider, provider or "-")
