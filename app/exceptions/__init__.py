"""Application exception hierarchy.

LeadGenerationError is the common base for every custom exception so callers
can catch the whole application error family in one place.
"""


class LeadGenerationError(Exception):
    """Base exception for all application errors."""


from app.exceptions.browser_exception import BrowserException  # noqa: E402
from app.exceptions.export_exception import ExportException  # noqa: E402
from app.exceptions.extraction_exception import ExtractionException  # noqa: E402
from app.exceptions.llm_exception import (  # noqa: E402
    LLMConfigurationError,
    LLMConnectionError,
    LLMError,
    LLMResponseError,
    PlanningError,
)
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
from app.exceptions.tool_exception import (  # noqa: E402
    DuplicateToolError,
    ToolError,
    UnknownToolError,
)

__all__ = [
    "LeadGenerationError",
    "BrowserException",
    "ExportException",
    "ExtractionException",
    "LLMError",
    "LLMConnectionError",
    "LLMConfigurationError",
    "LLMResponseError",
    "PlanningError",
    "ParserException",
    "ToolError",
    "UnknownToolError",
    "DuplicateToolError",
    "ProviderException",
    "UnknownProviderError",
    "DuplicateProviderError",
    "ProviderInitializationError",
    "ProviderSearchError",
    "ProviderNavigationError",
    "ProviderElementNotFoundError",
]
