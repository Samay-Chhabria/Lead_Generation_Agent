"""Provider-specific exceptions."""

from app.exceptions import LeadGenerationError


class ProviderException(LeadGenerationError):
    """Base exception for all provider errors."""


class UnknownProviderError(ProviderException):
    """Raised when a provider name is not registered."""


class DuplicateProviderError(ProviderException):
    """Raised when a provider name is registered more than once."""


class ProviderInitializationError(ProviderException):
    """Raised when a provider cannot be initialized."""


class ProviderSearchError(ProviderException):
    """Raised when a provider cannot complete a search."""


class ProviderNavigationError(ProviderSearchError):
    """Raised when the provider's site cannot be opened or navigated."""


class ProviderElementNotFoundError(ProviderSearchError):
    """Raised when a required page element is missing within the timeout."""
