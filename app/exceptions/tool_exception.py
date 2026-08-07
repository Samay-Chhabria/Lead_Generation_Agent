"""Tool registry and tool execution exceptions."""

from app.exceptions import LeadGenerationError


class ToolError(LeadGenerationError):
    """Base exception for all tool errors."""


class UnknownToolError(ToolError):
    """Raised when a requested tool is not registered in the registry."""


class DuplicateToolError(ToolError):
    """Raised when a tool name is registered more than once."""
