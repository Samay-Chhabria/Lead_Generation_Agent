"""Tool interface, result envelope, and shared execution context."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.config.logging_config import get_logger
from app.config.settings import Settings, get_settings


@dataclass(slots=True)
class ToolContext:
    """Shared resources handed to tools at construction time.

    Tools stay stateless about the browser lifecycle: they ask the context for
    a usable page, and the context launches or reuses the browser as needed.
    """

    browser: Any = None
    settings: Settings | None = None
    logger: logging.Logger | None = None
    _owns_page: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        if self.settings is None:
            self.settings = get_settings()
        if self.logger is None:
            self.logger = get_logger("tool")
        if self.browser is not None:
            self.browser = self.browser

    def get_page(self) -> Any:
        """Return a usable browser page, launching the browser if needed.

        The browser is launched lazily on first use: tools that never need a
        page (for example a placeholder search provider) never launch it.

        Returns:
            A Playwright page (or a test fake).
        """
        if self.browser is None:
            return None
        if hasattr(self.browser, "is_running") and not self.browser.is_running():
            if hasattr(self.browser, "launch"):
                self.browser.launch()
        if hasattr(self.browser, "active_page"):
            try:
                return self.browser.active_page()
            except Exception:
                pass
        try:
            return self.browser.new_page()
        except Exception as exc:
            raise RuntimeError(f"Could not obtain a browser page: {exc}") from exc


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Outcome of a single tool execution.

    Attributes:
        success: Whether the tool completed its job.
        data: Structured output produced by the tool (leads, paths, counts...).
        error: Human-readable failure detail when ``success`` is False.
    """

    success: bool = True
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""

    @classmethod
    def ok(cls, **data: Any) -> ToolResult:
        """Build a successful result."""
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, error: str) -> ToolResult:
        """Build a failed result."""
        return cls(success=False, error=str(error))


class Tool(ABC):
    """Base class for every agent tool.

    Subclasses declare a ``name`` and a ``description`` and implement
    ``run(**kwargs)``. ``run`` must never raise: it catches its own errors and
    returns a ``ToolResult`` so the agent loop can keep going.
    """

    name: str = "tool"
    description: str = ""

    def __init__(
        self,
        context: ToolContext | None = None,
        settings: Settings | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.context = context or ToolContext(settings=settings, logger=logger)
        self.settings = self.context.settings
        self._logger = self.context.logger

    def __repr__(self) -> str:
        return f"<{type(self).__name__} name='{self.name}'>"

    @abstractmethod
    def run(self, **kwargs: Any) -> ToolResult:
        """Execute the tool and return a ToolResult."""
