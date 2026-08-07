"""Offline, deterministic LLM provider.

MockProvider is the default provider: it never makes a network call and never
requires an API key, so the agent runs out of the box. It answers planning
requests with the tool catalog — the planner falls back to its deterministic
step builder when no tool call is requested, which is exactly what makes the
mock mode feel like a real agent while staying fully offline.
"""

import json
from typing import Any

from app.llm.base import LLMProvider, ToolMessage

_TOOL_NAMES = [
    "google_maps_search",
    "business_details",
    "website_crawler",
    "email_extractor",
    "phone_extractor",
    "lead_exporter",
]


class MockProvider(LLMProvider):
    """Deterministic offline provider used when no API key is configured."""

    name = "mock"

    def complete(self, messages: list[ToolMessage], **kwargs: Any) -> str:
        """Answer a planning prompt with the available tool catalog.

        Args:
            messages: The conversation so far.
            **kwargs: Ignored.

        Returns:
            A JSON object of the form
            ``{"thought": "...", "tool_calls": ["<tool>", ...]}``.
        """
        payload = {
            "thought": "I will use the available tools in order to complete the user request.",
            "tool_calls": list(_TOOL_NAMES),
        }
        return json.dumps(payload)
