"""Agent plan panel widget.

Before (and during) a run the panel shows the parsed execution plan: the
business type, location, provider, limits, and the ordered tool steps. It is
filled purely from the ``planning`` event emitted by the agent — no planning
logic lives in the GUI.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from app.execution.execution_logger import (
    EVENT_PLANNING,
    EVENT_PLANNING_FAILED,
    ExecutionEvent,
    tool_display_name,
)
from app.gui.widgets.cards import ScrollablePanel

_PLACEHOLDER = "Enter a prompt and press Search to build a plan."


class PlanPanel(ScrollablePanel):
    """Execution Plan card populated from the agent's planning event."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Agent Plan", icon="🧠", parent=parent)
        self._labels: dict[str, QLabel] = {}
        body = QWidget()
        self._layout = QVBoxLayout(body)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)

        self._goal = QLabel(_PLACEHOLDER)
        self._goal.setWordWrap(True)
        self._goal.setObjectName("muted")
        self._layout.addWidget(self._goal)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(4)
        self._add_row(grid, "Business Type", 0)
        self._add_row(grid, "Location", 1)
        self._add_row(grid, "Provider", 2)
        self._add_row(grid, "Maximum Results", 3)
        self._add_row(grid, "Website Crawling", 4)
        self._add_row(grid, "Export", 5)
        self._layout.addLayout(grid)

        self._steps = QLabel("")
        self._steps.setWordWrap(True)
        self._steps.setObjectName("muted")
        self._layout.addWidget(self._steps)
        self.add(body)

    def reset(self) -> None:
        """Reset the plan card to its idle state."""
        self._goal.setText(_PLACEHOLDER)
        for label in self._labels.values():
            label.setText("—")
        self._steps.setText("")

    def on_event(self, event: ExecutionEvent) -> None:
        """Populate the plan from a planning event."""
        if event.kind == EVENT_PLANNING:
            self._show_plan(event.data)
        elif event.kind == EVENT_PLANNING_FAILED:
            self._goal.setText(f"⚠️ Planning failed: {event.data.get('reason') or '-'}")

    # -- Internals ----------------------------------------------------------

    def _add_row(self, grid: QGridLayout, label: str, row: int) -> None:
        name = QLabel(label)
        name.setObjectName("muted")
        value = QLabel("—")
        value.setObjectName("value")
        value.setWordWrap(True)
        grid.addWidget(name, row, 0, Qt.AlignmentFlag.AlignRight)
        grid.addWidget(value, row, 1, Qt.AlignmentFlag.AlignLeft)
        grid.setColumnStretch(1, 1)
        self._labels[label] = value

    def _show_plan(self, data: dict) -> None:
        steps = data.get("steps") or []
        self._goal.setText(f"🎯 {data.get('goal') or '-'}")
        values = {
            "Business Type": data.get("business_type") or "-",
            "Location": data.get("location") or "-",
            "Provider": (data.get("provider") or "-").title(),
            "Maximum Results": str(data.get("max_results") or 0),
            "Website Crawling": "Yes" if data.get("needs_crawl") else "No",
            "Export": "Yes" if data.get("export") else "No",
        }
        for key, value in values.items():
            label = self._labels.get(key)
            if label is not None:
                label.setText(str(value))
        names = "  →  ".join(tool_display_name(step.get("tool", "")) for step in steps)
        self._steps.setText(f"Steps: {names}")
