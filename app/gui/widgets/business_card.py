"""Current business card widget.

While the agent processes businesses the card shows the business being worked
on and live-extracted fields (website, phone, email). Each tool announces the
business via ``business_started`` and reports the extracted value through
``business_done``; the card simply follows those events and switches to the
next business automatically.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel

from app.execution.execution_logger import (
    EVENT_BUSINESS_DONE,
    EVENT_BUSINESS_STARTED,
    ExecutionEvent,
)
from app.gui.widgets.cards import ScrollablePanel, body_frame, soft_wrap


class BusinessCard(ScrollablePanel):
    """Card rendering the business currently being processed."""

    def __init__(self, parent: object | None = None) -> None:
        super().__init__("Current Business", icon="🏢", parent=parent)
        self._current_name: str | None = None
        self._name = QLabel("—")
        self._name.setObjectName("h2")
        self._name.setWordWrap(True)
        self.content.addWidget(self._name)

        self._fields: dict[str, QLabel] = {}
        body = body_frame()
        grid = QGridLayout(body)
        grid.setContentsMargins(10, 8, 10, 8)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)
        grid.setColumnStretch(2, 1)
        self._add_field(grid, "website", "🌐", "Website", 0)
        self._add_field(grid, "phone", "📞", "Phone", 1)
        self._add_field(grid, "email", "📧", "Email", 2)
        self.content.addWidget(body)

    def reset(self) -> None:
        """Clear the card for a new run."""
        self._current_name = None
        self._name.setText("—")
        for label in self._fields.values():
            label.setText("Searching...")

    def on_event(self, event: ExecutionEvent) -> None:
        """Follow the per-business progress events."""
        data = event.data
        if event.kind == EVENT_BUSINESS_STARTED:
            business = data.get("business")
            if business != self._current_name:
                self._current_name = business
                self._name.setText(str(business or "—"))
                for label in self._fields.values():
                    label.setText("Searching...")
            tool = data.get("tool")
            if tool == "website_crawler":
                self._fields["website"].setText("Crawling...")
            elif tool == "email_extractor":
                self._fields["email"].setText("Searching...")
            elif tool == "phone_extractor":
                self._fields["phone"].setText("Searching...")
        elif event.kind == EVENT_BUSINESS_DONE:
            tool = data.get("tool")
            value = data.get("detail") or ""
            if tool == "website_crawler":
                self._fields["website"].setText("✓ Crawled")
                if value:
                    self._fields["email"].setText(soft_wrap(value))
            elif tool == "email_extractor":
                self._fields["email"].setText(soft_wrap(value) if value else "Not found")
            elif tool == "phone_extractor":
                self._fields["phone"].setText(value or "Not found")

    def _add_field(self, grid: QGridLayout, key: str, glyph: str, label: str, row: int) -> None:
        icon = QLabel(glyph)
        name = QLabel(label)
        name.setObjectName("muted")
        value = QLabel("Searching...")
        value.setObjectName("value")
        value.setWordWrap(True)
        value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        grid.addWidget(icon, row, 0)
        grid.addWidget(name, row, 1)
        grid.addWidget(value, row, 2)
        self._fields[key] = value
