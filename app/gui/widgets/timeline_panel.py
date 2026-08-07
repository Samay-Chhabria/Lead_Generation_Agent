"""Execution timeline widget.

The timeline shows the canonical run steps the user watches (understanding,
planning, launching the browser, searching, extracting, crawling, exporting,
finished). Every AgentExecutionLogger event moves the matching step between
the four states: pending (gray), current (highlighted), done (green) and
failed (red). A step that raised a recoverable error turns red, returns to
"current" once the recovery succeeds, and only stays red when the tool itself
fails permanently.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.execution.execution_logger import (
    EVENT_AGENT_STARTED,
    EVENT_ERROR,
    EVENT_FINISHED,
    EVENT_LAUNCHING_BROWSER,
    EVENT_PHASE,
    EVENT_PLANNING,
    EVENT_PLANNING_FAILED,
    EVENT_RECOVERED,
    EVENT_TOOL_FAILED,
    EVENT_TOOL_STARTED,
    EVENT_TOOL_SUCCEEDED,
    EVENT_UNDERSTANDING,
    ExecutionEvent,
)
from app.gui.resources.tokens import (
    STEP_CURRENT_PROPERTY,
    STEP_CURRENT_VALUE,
    STEP_DONE_VALUE,
    STEP_FAILED_VALUE,
    STEP_PENDING_VALUE,
)
from app.gui.widgets.cards import ScrollablePanel

#: Trailing status glyph shown per timeline row state.
_STATUS_GLYPHS = {
    STEP_PENDING_VALUE: "·",
    STEP_CURRENT_VALUE: "●",
    STEP_DONE_VALUE: "✓",
    STEP_FAILED_VALUE: "✗",
}

#: (key, human label, emoji) for the canonical timeline steps.
_STEPS = (
    ("understanding", "Understanding Request", "🧠"),
    ("planning", "Planning", "🗺️"),
    ("launch", "Launch Browser", "🌐"),
    ("maps", "Open Google Maps", "🗺️"),
    ("search", "Search Businesses", "🔍"),
    ("results", "Results Loaded", "📄"),
    ("collect", "Collect Businesses", "📋"),
    ("extract", "Extract Details", "📝"),
    ("crawl", "Crawl Website", "🕸️"),
    ("export", "Export Excel", "📊"),
    ("finished", "Finished", "✅"),
)

_TOOL_STEP = {
    "google_maps_search": "search",
    "business_details": "extract",
    "website_crawler": "crawl",
    "lead_exporter": "export",
}


class _StepRow(QFrame):
    """One timeline row whose look follows its ``state`` property."""

    def __init__(self, text: str, glyph: str) -> None:
        super().__init__()
        self.setObjectName("stepRow")
        self.setProperty(STEP_CURRENT_PROPERTY, STEP_PENDING_VALUE)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)
        self.icon = QLabel(glyph)
        self.icon.setObjectName("stepIcon")
        self.text = QLabel(text)
        self.text.setObjectName("stepText")
        self.text.setWordWrap(True)
        self.status = QLabel("")
        self.status.setObjectName("stepStatus")
        self.status.setProperty(STEP_CURRENT_PROPERTY, STEP_PENDING_VALUE)
        self.status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.icon)
        layout.addWidget(self.text, 1)
        layout.addWidget(self.status)
        self._restyle(STEP_PENDING_VALUE)

    def set_state(self, state: str) -> None:
        """Update the row state and re-apply the stylesheet lookup."""
        self._restyle(state)

    def _restyle(self, state: str) -> None:
        self.setProperty(STEP_CURRENT_PROPERTY, state)
        self.status.setProperty(STEP_CURRENT_PROPERTY, state)
        self.status.setText(_STATUS_GLYPHS[state])
        self.setStyleSheet("")
        self.status.setStyleSheet("")
        self.style().unpolish(self)
        self.style().polish(self)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        self.update()


class TimelinePanel(ScrollablePanel):
    """Rendered Execution Timeline (steps coloured by their state)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Execution Timeline", icon="📋", parent=parent)
        self._rows: dict[str, _StepRow] = {}
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        for key, text, glyph in _STEPS:
            row = _StepRow(text, glyph)
            layout.addWidget(row)
            self._rows[key] = row
        layout.addStretch(1)
        self.add(body)

    # -- Public API ---------------------------------------------------------

    def reset(self) -> None:
        """Return every step to the pending state."""
        for row in self._rows.values():
            row.set_state(STEP_PENDING_VALUE)

    def on_event(self, event: ExecutionEvent) -> None:
        """Advance the timeline from one execution event."""
        kind = event.kind
        data = event.data
        if kind == EVENT_AGENT_STARTED:
            self._set_state("understanding", STEP_CURRENT_VALUE)
        elif kind == EVENT_UNDERSTANDING:
            self._set_state("understanding", STEP_DONE_VALUE)
        elif kind == EVENT_PLANNING:
            self._set_state("planning", STEP_DONE_VALUE)
            self._set_state("launch", STEP_CURRENT_VALUE)
        elif kind == EVENT_PLANNING_FAILED:
            self._set_state("planning", STEP_FAILED_VALUE)
        elif kind == EVENT_LAUNCHING_BROWSER:
            self._set_state("launch", STEP_DONE_VALUE)
            self._set_state("maps", STEP_CURRENT_VALUE)
        elif kind == EVENT_PHASE:
            self._handle_phase(data.get("phase"))
        elif kind == EVENT_TOOL_STARTED:
            step = _TOOL_STEP.get(data.get("tool"))
            if step is not None:
                self._set_state(step, STEP_CURRENT_VALUE)
        elif kind == EVENT_TOOL_SUCCEEDED:
            step = _TOOL_STEP.get(data.get("tool"))
            if step is not None:
                self._set_state(step, STEP_DONE_VALUE)
        elif kind == EVENT_TOOL_FAILED:
            step = _TOOL_STEP.get(data.get("tool"))
            if step is not None:
                self._set_state(step, STEP_FAILED_VALUE)
        elif kind == EVENT_ERROR:
            self._error_key = self._current_key()
        elif kind == EVENT_RECOVERED:
            if getattr(self, "_error_key", None):
                self._set_state(self._error_key, STEP_CURRENT_VALUE)
                self._error_key = None
        elif kind == EVENT_FINISHED:
            result = data.get("result")
            success = bool(getattr(result, "success", False)) if result is not None else False
            self._set_state("finished", STEP_DONE_VALUE if success else STEP_FAILED_VALUE)

    # -- Internals ----------------------------------------------------------

    def _handle_phase(self, phase: str | None) -> None:
        mapping = {
            "Navigating": ("maps", "search"),
            "Searching": ("search", None),
            "Waiting For Results": ("search", "results"),
            "Collecting Businesses": ("results", "collect"),
            "Extracting Details": ("extract", None),
            "Crawling Website": ("crawl", None),
            "Saving Excel": ("export", None),
        }
        done, current = mapping.get(phase, (None, None))
        if done is not None:
            self._set_state(done, STEP_DONE_VALUE)
        if current is not None:
            self._set_state(current, STEP_CURRENT_VALUE)

    def _current_key(self) -> str | None:
        for key, row in self._rows.items():
            if row.property(STEP_CURRENT_PROPERTY) == STEP_CURRENT_VALUE:
                return key
        return None

    def _set_state(self, key: str, state: str) -> None:
        row = self._rows.get(key)
        if row is not None:
            row.set_state(state)
