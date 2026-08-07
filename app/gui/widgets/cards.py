"""Reusable card/panel building blocks for the desktop GUI."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.gui.resources.tokens import (
    PANEL_SCROLL_CONTENT,
    PANEL_SCROLL_OBJECT,
    PANEL_SPACING,
)


def add_shadow(widget: QWidget, color: str = "#000000", blur: int = 24) -> None:
    """Attach a soft drop shadow to a widget."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, 3)
    effect.setColor(color)
    widget.setGraphicsEffect(effect)


def panel_header(title: str, icon_text: str = "") -> QLabel:
    """Return a styled panel title label (optionally with an emoji icon)."""
    label = QLabel(f"{icon_text}  {title}" if icon_text else title)
    label.setObjectName("h2")
    return label


def body_frame(object_name: str = "cardBody") -> QFrame:
    """Return a subtle inner container for structured card content."""
    frame = QFrame()
    frame.setObjectName(object_name)
    return frame


_WRAP_AFTER = ("/", "\\", ".", "_", "-", ":", " ")


def soft_wrap(text: str, chunk: int = 32) -> str:
    """Insert zero-width spaces so long URLs and paths wrap inside QLabels.

    Qt's word-wrap only breaks on spaces, so an unbroken URL or export path
    would otherwise overflow its label. The zero-width spaces are invisible and
    only give the layout safe break points; substring searches still match.
    """
    if not text:
        return text
    out: list[str] = []
    for index, char in enumerate(text):
        out.append(char)
        if char in _WRAP_AFTER or (index + 1) % chunk == 0:
            out.append("\u200b")
    return "".join(out)


class Panel(QFrame):
    """A titled, rounded card with a header and a content area.

    Typical usage::

        panel = Panel("Execution Timeline", icon="📋")
        panel.content.addWidget(some_widget)

    Pass ``scrollable=True`` to pin the header and let the content area scroll
    on its own (used so every card inside the dashboard columns can shrink
    without overlapping its neighbours).
    """

    def __init__(
        self,
        title: str,
        icon: str = "",
        parent: QWidget | None = None,
        *,
        shadow: str = "#000000",
        scrollable: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(PANEL_SPACING)

        header_row = QHBoxLayout()
        self._title = panel_header(title, icon)
        header_row.addWidget(self._title)
        header_row.addStretch(1)
        self.header_row = header_row
        layout.addLayout(header_row)

        self.content = QVBoxLayout()
        self.content.setSpacing(PANEL_SPACING)
        if scrollable:
            self._scroll = QScrollArea()
            self._scroll.setObjectName(PANEL_SCROLL_OBJECT)
            self._scroll.setWidgetResizable(True)
            self._scroll.setFrameShape(QFrame.Shape.NoFrame)
            self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            host = QWidget()
            host.setObjectName(PANEL_SCROLL_CONTENT)
            host.setLayout(self.content)
            self._scroll.setWidget(host)
            layout.addWidget(self._scroll, 1)
        else:
            layout.addLayout(self.content)
        add_shadow(self, color=shadow)

    def add(self, widget: QWidget, stretch: int = 0) -> None:
        """Add a widget to the card content area."""
        self.content.addWidget(widget, stretch)


class ScrollablePanel(Panel):
    """A panel whose content scrolls independently of the dashboard column."""

    def __init__(
        self,
        title: str,
        icon: str = "",
        parent: QWidget | None = None,
        *,
        shadow: str = "#000000",
    ) -> None:
        super().__init__(title, icon=icon, parent=parent, shadow=shadow, scrollable=True)
