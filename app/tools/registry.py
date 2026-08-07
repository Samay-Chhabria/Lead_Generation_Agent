"""Tool registry: name-based lookup and duplicate protection."""

import logging
from typing import Any

from app.config.logging_config import get_logger
from app.exceptions.tool_exception import DuplicateToolError, UnknownToolError
from app.tools.base import Tool, ToolContext


class ToolRegistry:
    """Hold and resolve tools by name.

    Registration is strict: registering the same name twice raises
    ``DuplicateToolError`` so a misconfigured tool set is caught at startup
    instead of silently shadowing a tool.
    """

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        self._logger = logger or get_logger("tools")

    def register(self, tool: Tool) -> None:
        """Register a tool under its name.

        Args:
            tool: The tool instance to register.

        Raises:
            DuplicateToolError: When a tool with the same name is registered.
        """
        if tool.name in self._tools:
            raise DuplicateToolError(f"Tool '{tool.name}' is already registered.")
        self._tools[tool.name] = tool
        self._logger.debug("Registered tool '%s'.", tool.name)

    def unregister(self, name: str) -> None:
        """Remove a tool from the registry by name."""
        self._tools.pop(name, None)

    def get(self, name: str) -> Tool:
        """Return the tool registered under ``name``.

        Args:
            name: The tool name.

        Raises:
            UnknownToolError: When no tool is registered under that name.
        """
        tool = self._tools.get(name)
        if tool is None:
            raise UnknownToolError(f"Unknown tool '{name}'. Registered tools: {self.names()}")
        return tool

    def names(self) -> list[str]:
        """Return the sorted list of registered tool names."""
        return sorted(self._tools)

    def has(self, name: str) -> bool:
        """Return True when a tool is registered under ``name``."""
        return name in self._tools

    def all(self) -> dict[str, Tool]:
        """Return a copy of the registered tools keyed by name."""
        return dict(self._tools)

    def catalog(self) -> str:
        """Return a human-readable catalog of available tools."""
        lines = [f"{name}: {self._tools[name].description}" for name in self.names()]
        return "\n".join(lines)


def build_default_registry(
    context: ToolContext | None = None,
    factory: Any = None,
) -> ToolRegistry:
    """Build a registry containing every built-in tool.

    Args:
        context: Shared tool context; a fresh one is created when omitted.
        factory: Optional ProviderFactory injected into the search tool so it
            honors a caller's custom provider registry.

    Returns:
        A ToolRegistry with all built-in tools registered.
    """
    from app.tools.business_collection_tool import BusinessCollectionTool
    from app.tools.business_details_tool import BusinessDetailsTool
    from app.tools.business_extraction_tool import BusinessExtractionTool
    from app.tools.email_tool import EmailExtractorTool
    from app.tools.export_tool import ExportTool
    from app.tools.exporter_tool import LeadExporterTool
    from app.tools.google_maps_tool import GoogleMapsSearchTool
    from app.tools.navigation_tool import NavigationTool
    from app.tools.phone_tool import PhoneExtractorTool
    from app.tools.pipeline_tool import PipelineTool
    from app.tools.search_tool import SearchTool
    from app.tools.summary_tool import SummaryTool
    from app.tools.website_tool import WebsiteCrawlerTool

    context = context or ToolContext()
    registry = ToolRegistry(logger=context.logger)
    registry.register(GoogleMapsSearchTool(context, factory=factory))
    registry.register(SearchTool(context, factory=factory))
    registry.register(BusinessCollectionTool(context, factory=factory))
    registry.register(WebsiteCrawlerTool(context))
    registry.register(EmailExtractorTool(context))
    registry.register(PhoneExtractorTool(context))
    registry.register(BusinessDetailsTool(context))
    registry.register(BusinessExtractionTool(context))
    registry.register(NavigationTool(context))
    registry.register(ExportTool(context))
    registry.register(LeadExporterTool(context))
    registry.register(PipelineTool(context, factory=factory))
    registry.register(SummaryTool(context))
    return registry
