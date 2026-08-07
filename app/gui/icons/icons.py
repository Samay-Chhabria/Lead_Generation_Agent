"""Code-generated icons for the desktop GUI.

Icons are painted at runtime (rounded tile + emoji glyph) so the repository
never has to ship binary assets and the icons follow the active theme.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap

#: Emoji glyphs per conceptual icon name.
GLYPHS = {
    "agent": "🤖",
    "planning": "🧠",
    "search": "🔍",
    "browser": "🌐",
    "maps": "🗺️",
    "business": "🏢",
    "website": "🕸️",
    "email": "📧",
    "excel": "📊",
    "success": "✅",
    "failure": "❌",
    "progress": "📈",
    "folder": "📂",
    "play": "🚀",
    "retry": "🔁",
    "time": "⏱️",
    "user": "👤",
    "error": "⚠️",
    "recovery": "🛠️",
}


def glyph(name: str) -> str:
    """Return the emoji glyph for an icon name (empty string when unknown)."""
    return GLYPHS.get(name, "")


def icon(name: str, color: str, size: int = 20) -> QIcon:
    """Build a QIcon from an emoji glyph on a rounded tile.

    Args:
        name: A key from :data:`GLYPHS`.
        color: Tile background colour as a CSS colour string.
        size: Icon pixel size.

    Returns:
        The generated QIcon.
    """
    tile = QPixmap(size, size)
    tile.fill(Qt.GlobalColor.transparent)
    painter = QPainter(tile)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(color))
    painter.drawRoundedRect(QRectF(0, 0, size, size), size * 0.3, size * 0.3)
    font = QFont("Segoe UI Emoji")
    font.setPixelSize(int(size * 0.62))
    painter.setFont(font)
    painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, GLYPHS.get(name, "•"))
    painter.end()
    return QIcon(tile)
