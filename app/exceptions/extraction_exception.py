"""Extraction-specific exceptions."""

from app.exceptions import LeadGenerationError


class ExtractionException(LeadGenerationError):
    """Raised when lead data cannot be extracted from a page.

    Will be raised by the lead extractor (Milestone 5) when a page does not
    contain usable business information.
    """
