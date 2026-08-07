"""Agent memory: what the agent has seen and done during a run.

Memory keeps a lightweight, JSON-safe transcript of the conversation, the tools
that completed, and the observations gathered from their results. The transcript
is available to the planner for context in follow-up turns and is logged for
auditability — but it is never shown to the end user.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.config.logging_config import get_logger


@dataclass(slots=True)
class AgentMemory:
    """Scratchpad for a single task run."""

    logger: logging.Logger = field(default_factory=lambda: get_logger("agent.memory"), repr=False)
    current_task: str = ""
    transcript: list[dict[str, str]] = field(default_factory=list)
    completed_tools: list[str] = field(default_factory=list)
    observations: dict[str, dict[str, Any]] = field(default_factory=dict)

    def begin(self, task: str) -> None:
        """Start a fresh run for the given task."""
        self.current_task = task
        self.transcript = []
        self.completed_tools = []
        self.observations = {}
        self.add_message("user", task)

    def add_message(self, role: str, content: str) -> None:
        """Append a message to the transcript and log it."""
        entry = {"role": role, "content": content}
        self.transcript.append(entry)
        self.logger.debug("Memory[%s]: %s", role, content)

    def record_tool(self, tool_name: str, success: bool, summary: str) -> None:
        """Record a completed tool call and its outcome.

        Args:
            tool_name: The name of the tool that ran.
            success: Whether the tool succeeded.
            summary: A short human-readable summary of the result.
        """
        self.completed_tools.append(tool_name)
        self.observations[tool_name] = {
            "success": success,
            "summary": summary,
        }
        self.add_message(
            "tool",
            f"{tool_name} {'succeeded' if success else 'failed'}: {summary}",
        )

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-safe snapshot of the memory."""
        return {
            "task": self.current_task,
            "transcript": list(self.transcript),
            "completed_tools": list(self.completed_tools),
            "observations": {k: dict(v) for k, v in self.observations.items()},
        }
