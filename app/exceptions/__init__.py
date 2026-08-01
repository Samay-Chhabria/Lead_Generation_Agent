"""Application exception hierarchy.

LeadGenerationError is the common base for every custom exception so callers
can catch the whole application error family in one place.
"""


class LeadGenerationError(Exception):
    """Base exception for all application errors."""


from app.exceptions.browser_exception import BrowserException  # noqa: E402
from app.exceptions.extraction_exception import ExtractionException  # noqa: E402
from app.exceptions.parser_exception import ParserException  # noqa: E402
from app.exceptions.provider_exception import (  # noqa: E402
    DuplicateProviderError,
    ProviderElementNotFoundError,
    ProviderException,
    ProviderInitializationError,
    ProviderNavigationError,
    ProviderSearchError,
    UnknownProviderError,
)

__all__ = [
    "LeadGenerationError",
    "BrowserException",
    "ExtractionException",
    "ParserException",
    "ProviderException",
    "UnknownProviderError",
    "DuplicateProviderError",
    "ProviderInitializationError",
    "ProviderSearchError",
    "ProviderNavigationError",
    "ProviderElementNotFoundError",
]
