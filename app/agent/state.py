"""Agent state: the plan of steps and the loop's position within it.

The executor drives the loop forward by asking the state for the next step and
marking steps complete as tools finish. All step arguments are JSON-safe so the
state can be snapshotted and logged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class AgentStep:
    """A single tool invocation planned by the planner."""

    tool: str
    description: str
    arguments: dict[str, Any] = field(default_factory=dict)
    reason: str = ""


@dataclass(slots=True)
class AgentState:
    """Mutable execution state for a single task run."""

    task: str
    steps: list[AgentStep] = field(default_factory=list)
    current_index: int = 0
    completed_tools: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def total_steps(self) -> int:
        """Return the number of planned steps."""
        return len(self.steps)

    @property
    def is_finished(self) -> bool:
        """Return True when every step has been executed."""
        return self.current_index >= len(self.steps)

    def next_step(self) -> AgentStep | None:
        """Return the next step to execute, or None when finished."""
        if self.is_finished:
            return None
        return self.steps[self.current_index]

    def mark_current_done(self) -> None:
        """Record the current step as completed and advance the cursor."""
        step = self.next_step()
        if step is None:
            return
        self.completed_tools.append(step.tool)
        self.current_index += 1

    def remaining_tools(self) -> list[str]:
        """Return the names of the tools not yet executed."""
        return [step.tool for step in self.steps[self.current_index :]]

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-safe summary of the execution state."""
        return {
            "task": self.task,
            "current_index": self.current_index,
            "total_steps": self.total_steps,
            "completed_tools": list(self.completed_tools),
            "remaining_tools": self.remaining_tools(),
            "payload_keys": sorted(self.payload),
        }
