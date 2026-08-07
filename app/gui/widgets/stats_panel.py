"""Statistics panel widget.

A responsive grid of metric cards: businesses found/processed, emails,
websites and phone numbers discovered, the current run time (ticked every
second by the main window), and the live model choice. Every card word-wraps
so long values can never overflow the grid.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.execution.execution_logger import (
    EVENT_BUSINESS_DONE,
    EVENT_FINISHED,
    EVENT_LLM_MODEL_SELECTED,
    EVENT_PROGRESS,
    EVENT_TOOL_SUCCEEDED,
    ExecutionEvent,
)
from app.gui.widgets.cards import ScrollablePanel

_KEYS = (
    "businesses_found",
    "businesses_processed",
    "emails_found",
    "websites_found",
    "phones_found",
    "runtime",
    "current_model",
    "model_reason",
)

_GLYPHS = {
    "businesses_found": "👥",
    "businesses_processed": "⚙️",
    "emails_found": "📧",
    "websites_found": "🌐",
    "phones_found": "📞",
    "runtime": "⏱️",
    "current_model": "🤖",
    "model_reason": "🧭",
}


class StatsPanel(ScrollablePanel):
    """Live execution statistics as a word-wrapping metric-card grid."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Statistics", icon="📈", parent=parent)
        self._values: dict[str, QLabel] = {}
        body = QWidget()
        grid = QGridLayout(body)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        for index, key in enumerate(_KEYS):
            row, col = divmod(index, 2)
            grid.addWidget(self._build_card(key), row, col)
        self.add(body)

    def reset(self) -> None:
        """Zero every counter for a new run."""
        for key, label in self._values.items():
            label.setText("0" if key != "runtime" else "0s")
        model = self._values.get("current_model")
        if model is not None:
            model.setText("-")
        reason = self._values.get("model_reason")
        if reason is not None:
            reason.setText("-")

    def on_event(self, event: ExecutionEvent) -> None:
        """Update the counters from the relevant execution events."""
        data = event.data
        if event.kind == EVENT_LLM_MODEL_SELECTED:
            self._set_text("current_model", data.get("model") or "-")
            self._set_text("model_reason", data.get("reason") or "-")
        elif event.kind == EVENT_PROGRESS:
            self._bump("businesses_processed", data.get("processed"))
            self._bump("businesses_found", data.get("total"))
        elif event.kind == EVENT_BUSINESS_DONE:
            tool = data.get("tool")
            if tool == "email_extractor" and data.get("success"):
                self._increment("emails_found")
            elif tool == "website_crawler" and data.get("success"):
                self._increment("websites_found")
            elif tool == "phone_extractor" and data.get("success"):
                self._increment("phones_found")
        elif event.kind == EVENT_TOOL_SUCCEEDED:
            if data.get("tool") == "google_maps_search":
                detail = data.get("detail") or ""
                self._bump("businesses_found", self._extract_count(detail))
        elif event.kind == EVENT_FINISHED:
            result = data.get("result")
            if result is not None:
                self._bump("businesses_found", getattr(result, "collected_leads", None))

    def set_runtime(self, seconds: float) -> None:
        """Update the current runtime counter."""
        label = self._values.get("runtime")
        if label is not None:
            label.setText(f"{seconds:.0f}s")

    # -- Internals ----------------------------------------------------------

    def _build_card(self, key: str) -> QFrame:
        card = QFrame()
        card.setObjectName("metricCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        head = QHBoxLayout()
        head.setSpacing(6)
        icon = QLabel(_GLYPHS.get(key, "•"))
        icon.setObjectName("stepIcon")
        title = QLabel(self._title_for(key))
        title.setObjectName("metricLabel")
        title.setWordWrap(True)
        head.addWidget(icon)
        head.addWidget(title, 1)
        layout.addLayout(head)

        value = QLabel("0")
        value.setWordWrap(True)
        if key == "model_reason":
            value.setObjectName("metricHint")
        else:
            value.setObjectName("metricValue")
        layout.addWidget(value)
        self._values[key] = value
        return card

    def _increment(self, key: str) -> None:
        label = self._values.get(key)
        if label is not None:
            label.setText(str(int(label.text() or 0) + 1))

    def _set_text(self, key: str, value: str) -> None:
        label = self._values.get(key)
        if label is not None:
            label.setText(value)

    def _bump(self, key: str, value: int | None) -> None:
        if value is None:
            return
        label = self._values.get(key)
        if label is not None:
            current = int(label.text() or 0)
            label.setText(str(max(current, int(value))))

    @staticmethod
    def _extract_count(detail: str) -> int | None:
        for token in detail.replace(",", " ").split():
            if token.isdigit():
                return int(token)
        return None

    @staticmethod
    def _title_for(key: str) -> str:
        return {
            "businesses_found": "Businesses Found",
            "businesses_processed": "Businesses Processed",
            "emails_found": "Emails Found",
            "websites_found": "Websites Found",
            "phones_found": "Phone Numbers",
            "runtime": "Current Runtime",
            "current_model": "Current Model",
            "model_reason": "Model Reason",
        }[key]
