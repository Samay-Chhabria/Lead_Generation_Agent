"""Tool manager: the agent's tool coordination layer.

``ToolManager`` owns the tool registry and the shared execution context and is
the single entry point the agent uses to pick and run tools. It keeps the
registry API (register, names, has, catalog) and adds a guarded ``execute``
that always returns a ``ToolResult`` — a tool that raises is turned into a
failed result instead of killing the agent loop.

The manager also knows about the ``pipeline`` tool, so the legacy end-to-end
pipeline is selectable by the agent exactly like any other tool.
"""

from __future__ import annotations

import logging
from typing import Any

from app.config.logging_config import get_logger
from app.tools.base import Tool, ToolContext, ToolResult
from app.tools.registry import ToolRegistry

PIPELINE_TOOL_NAME = "pipeline"


class ToolManager:
    """Coordinate tool selection and execution for the agent loop."""

    def __init__(
        self,
        registry: ToolRegistry,
        context: ToolContext | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._registry = registry
        self._context = context
        self._logger = logger or get_logger("agent.tools")

    @property
    def registry(self) -> ToolRegistry:
        """Return the underlying tool registry."""
        return self._registry

    @property
    def context(self) -> ToolContext | None:
        """Return the shared tool context, if any."""
        return self._context

    def execute(self, name: str, **kwargs: Any) -> ToolResult:
        """Resolve and run a tool, returning a ToolResult unconditionally.

        Args:
            name: The name of the tool to run.
            **kwargs: Arguments forwarded to the tool.

        Returns:
            The tool's ToolResult, or a failed ToolResult when the tool is
            unknown or raises.
        """
        tool = self.get(name)
        if tool is None:
            return ToolResult.fail(f"Unknown tool '{name}'.")
        try:
            return tool.run(**kwargs)
        except Exception as exc:  # pragma: no cover - defensive
            self._logger.warning("Tool '%s' raised: %s", name, exc)
            return ToolResult.fail(f"Tool '{name}' failed: {exc}")

    def register(self, tool: Tool) -> None:
        """Register a tool with the manager's registry."""
        self._registry.register(tool)

    def get(self, name: str) -> Tool | None:
        """Return the tool registered under ``name``, or None when unknown."""
        try:
            return self._registry.get(name)
        except Exception:  # pragma: no cover - defensive
            return None

    def names(self) -> list[str]:
        """Return the sorted list of registered tool names."""
        return self._registry.names()

    def has(self, name: str) -> bool:
        """Return True when a tool is registered under ``name``."""
        return self._registry.has(name)

    def catalog(self) -> str:
        """Return a human-readable catalog of available tools."""
        return self._registry.catalog()

    def all(self) -> dict[str, Tool]:
        """Return a copy of the registered tools keyed by name."""
        return self._registry.all()

    def has_pipeline(self) -> bool:
        """Return True when the legacy pipeline is available as a tool."""
        return self._registry.has(PIPELINE_TOOL_NAME)
