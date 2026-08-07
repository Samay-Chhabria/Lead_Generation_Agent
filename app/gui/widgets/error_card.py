"""Error / recovery card widget.

Shown when the agent reports a failing step. It renders the current step, its
status, the reason, and the recovery attempts ("Retrying... Attempt 2/3");
when the step recovers it switches to a success state and hides itself. The
card is a compact two-column alert so it never crowds the neighbouring panels.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from app.execution.execution_logger import (
    EVENT_ERROR,
    EVENT_RECOVERED,
    EVENT_RETRYING,
    ExecutionEvent,
)
from app.gui.widgets.cards import Panel


class ErrorCard(Panel):
    """Live error reporting + recovery tracker."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("⚠️ Error Handling", icon="🛠️", parent=parent)
        body = QWidget()
        grid = QGridLayout(body)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(4)
        self._step = self._field(grid, "Current Step", 0, 0)
        self._status = self._field(grid, "Status", 0, 1)
        self._reason = self._field(grid, "Reason", 1, 0)
        self._recovery = self._field(grid, "Recovery", 1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        self.add(body)
        self.setVisible(False)

    def _field(self, grid: QGridLayout, label: str, row: int, col: int) -> QLabel:
        name = QLabel(label)
        name.setObjectName("muted")
        text = QLabel("—")
        text.setWordWrap(True)
        text.setObjectName("value")
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(name)
        layout.addWidget(text)
        grid.addWidget(box, row, col)
        return text

    def reset(self) -> None:
        """Hide the card for a new run."""
        self.setVisible(False)

    def on_event(self, event: ExecutionEvent) -> None:
        """Show or advance the error/recovery state from events."""
        data = event.data
        if event.kind == EVENT_ERROR:
            self._step.setText(str(data.get("step") or "-"))
            self._status.setText(str(data.get("status") or "FAILED"))
            self._reason.setText(str(data.get("reason") or "-"))
            self._recovery.setText("")
            self.setVisible(True)
        elif event.kind == EVENT_RETRYING:
            self._recovery.setText(
                f"Retrying... Attempt {data.get('attempt')}/{data.get('maximum')}"
            )
            self.setVisible(True)
        elif event.kind == EVENT_RECOVERED:
            self._recovery.setText("Recovered Successfully — Continuing...")
            QTimer.singleShot(2500, self.hide)
