"""Export-specific exceptions."""

from app.exceptions import LeadGenerationError


class ExportException(LeadGenerationError):
    """Raised when collected leads cannot be exported to an Excel workbook.

    Wraps output-directory, permission, filename, and save failures so callers
    only need to catch one exception family for the whole export step
    (Requirement 8).
    """
