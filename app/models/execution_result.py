"""Outcome model of one end-to-end lead generation run."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Summary of a complete lead generation run.

    Produced after a prompt has been parsed, businesses searched, leads
    processed and exported. The counts describe each stage of the run and
    ``success`` reflects whether the full workflow completed. On failure,
    ``excel_output_path`` stays ``None`` while the counts still report
    whatever data was collected before the failure.
    """

    search_query: str = ""
    business_type: str = ""
    location: str | None = None
    provider: str = ""
    requested_leads: int = 0
    collected_leads: int = 0
    processed_leads: int = 0
    duplicates_removed: int = 0
    excel_output_path: Path | None = None
    execution_time: float = 0.0
    success: bool = False
    summary: str = ""
