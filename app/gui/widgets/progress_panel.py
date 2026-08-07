"""Progress panel widget.

The full-width progress section at the top of the dashboard. Shows the overall
run progress bar (driven by the tool step counter), the current activity
status, the live tool, the per-business counter (``Business 3 / 5``) from the
progress events, and the coarse phase the agent is in.
"""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QWidget

from app.execution.execution_logger import (
    EVENT_FINISHED,
    EVENT_PHASE,
    EVENT_PROGRESS,
    EVENT_TOOL_STARTED,
    EVENT_TOOL_SUCCEEDED,
    ExecutionEvent,
)
from app.gui.widgets.cards import Panel


class ProgressPanel(Panel):
    """Overall + per-business progress bar with live activity chips."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Progress", icon="📊", parent=parent)
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self.add(self._bar)

        meta = QWidget()
        row = QHBoxLayout(meta)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self._status = self._chip(strong=True)
        self._tool = self._chip()
        self._business = self._chip()
        self._phase = self._chip()
        row.addWidget(self._status, 2)
        row.addWidget(self._tool, 1)
        row.addWidget(self._business, 1)
        row.addWidget(self._phase, 1)
        self.add(meta)

    def reset(self) -> None:
        """Reset the progress for a new run."""
        self._bar.setValue(0)
        self._status.setText("Ready")
        self._tool.setText("Tool: —")
        self._business.setText("Business — / —")
        self._phase.setText("Phase: —")

    def on_event(self, event: ExecutionEvent) -> None:
        """Advance the progress bars from tool and business events."""
        data = event.data
        if event.kind == EVENT_TOOL_STARTED:
            step, total = data.get("step"), data.get("total")
            if step and total:
                self._bar.setValue(int((step - 1) / int(total) * 100))
            display = data.get("display") or "-"
            self._status.setText(f"Running {display}...")
            self._tool.setText(f"Tool: {display}")
        elif event.kind == EVENT_TOOL_SUCCEEDED:
            step, total = data.get("step"), data.get("total")
            if step and total:
                self._bar.setValue(int(int(step) / int(total) * 100))
            display = data.get("display") or "-"
            self._status.setText(f"Done: {display}")
            self._tool.setText(f"Tool: {display}")
        elif event.kind == EVENT_PROGRESS:
            processed, total = data.get("processed"), data.get("total")
            if processed is not None and total:
                self._business.setText(f"Business {processed} / {total}")
        elif event.kind == EVENT_PHASE:
            phase = data.get("phase") or ""
            self._phase.setText(f"Phase: {phase}")
            self._status.setText(f"{phase}...")
        elif event.kind == EVENT_FINISHED:
            self._bar.setValue(100)
            result = data.get("result")
            success = bool(getattr(result, "success", False)) if result is not None else False
            self._status.setText("Completed" if success else "Failed")

    def _chip(self, *, strong: bool = False) -> QLabel:
        label = QLabel("—")
        label.setObjectName("chipStrong" if strong else "chip")
        label.setWordWrap(True)
        return label
