"""Browser-specific exceptions."""

from app.exceptions import LeadGenerationError


class BrowserException(LeadGenerationError):
    """Raised when the browser cannot be started or used correctly.

    Will be raised by the browser manager (Milestone 3) for launch failures,
    navigation timeouts, and other Playwright-related errors.
    """
