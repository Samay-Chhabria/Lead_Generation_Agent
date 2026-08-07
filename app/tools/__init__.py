"""Tool abstraction layer for the lead generation agent.

Tools are the agent's hands: every capability — searching Google Maps,
crawling websites, extracting emails and phones, and exporting leads — is a
``Tool`` with a ``run`` method. The registry maps tool names to instances so
the planner can select tools by name.
"""

from app.tools.base import Tool, ToolContext, ToolResult
from app.tools.business_details_tool import BusinessDetailsTool
from app.tools.email_tool import EmailExtractorTool
from app.tools.exporter_tool import LeadExporterTool
from app.tools.google_maps_tool import GoogleMapsSearchTool
from app.tools.phone_tool import PhoneExtractorTool
from app.tools.registry import ToolRegistry, build_default_registry
from app.tools.website_tool import WebsiteCrawlerTool

__all__ = [
    "Tool",
    "ToolContext",
    "ToolResult",
    "ToolRegistry",
    "build_default_registry",
    "GoogleMapsSearchTool",
    "WebsiteCrawlerTool",
    "EmailExtractorTool",
    "PhoneExtractorTool",
    "BusinessDetailsTool",
    "LeadExporterTool",
]
