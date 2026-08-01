"""Parser-specific exceptions."""

from app.exceptions import LeadGenerationError


class ParserException(LeadGenerationError):
    """Raised when a prompt cannot be parsed into a SearchPlan.

    Raised for empty or whitespace-only prompts, prompts that do not contain a
    location separator, or prompts missing a business type or location.
    """
