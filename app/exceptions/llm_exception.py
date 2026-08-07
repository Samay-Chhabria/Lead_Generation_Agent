"""LLM provider and planning exceptions."""

from app.exceptions import LeadGenerationError


class LLMError(LeadGenerationError):
    """Base exception for all LLM provider errors."""


class LLMConnectionError(LLMError):
    """Raised when the LLM provider cannot be reached."""


class LLMConfigurationError(LLMError):
    """Raised when an LLM provider is missing required configuration."""


class LLMResponseError(LLMError):
    """Raised when the LLM returns malformed or unparseable output."""


class PlanningError(LLMError):
    """Raised when the planner cannot turn a task into an executable plan."""
