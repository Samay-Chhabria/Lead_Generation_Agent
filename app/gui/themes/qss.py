"""Qt stylesheet generation for the desktop GUI.

One QSS string is generated per :class:`Theme`. Widgets opt into a style via
``objectName`` selectors (``panel``, ``card``, ``primaryButton``, ...) and the
timeline rows use a dynamic ``state`` property.
"""

from __future__ import annotations

from app.gui.resources.tokens import (
    BORDER_WIDTH,
    CARD_BODY_RADIUS,
    CARD_RADIUS,
    CONTROL_RADIUS,
    FONT_FAMILY,
    MONO_FONT,
)
from app.gui.themes.theme import Theme


def build_qss(theme: Theme) -> str:
    """Return the full application stylesheet for a theme."""
    return f"""
* {{
    font-family: "{FONT_FAMILY}";
    font-size: 14px;
    color: {theme.text};
}}
QMainWindow, QDialog {{
    background-color: {theme.window};
}}
QWidget#central {{
    background-color: {theme.window};
}}
QFrame#panel {{
    background-color: {theme.panel};
    border: {BORDER_WIDTH}px solid {theme.border};
    border-radius: {CARD_RADIUS}px;
}}
QFrame#panelAlt {{
    background-color: {theme.panel_alt};
    border: {BORDER_WIDTH}px solid {theme.border};
    border-radius: {CARD_RADIUS}px;
}}
QFrame#cardBody {{
    background-color: {theme.panel_alt};
    border: {BORDER_WIDTH}px solid {theme.border};
    border-radius: {CARD_BODY_RADIUS}px;
}}
QFrame#metricCard {{
    background-color: {theme.panel_alt};
    border: {BORDER_WIDTH}px solid {theme.border};
    border-radius: {CARD_BODY_RADIUS}px;
}}
QFrame#stepRow {{
    border-radius: 10px;
    padding: 4px 8px;
    margin: 1px 0px;
    background: transparent;
}}
QFrame#stepRow[state="current"] {{
    background: rgba(79, 140, 255, 38);
    border: 1px solid {theme.accent};
}}
QFrame#stepRow[state="done"] {{
    background: rgba(47, 206, 122, 20);
    border: 1px solid rgba(47, 206, 122, 90);
}}
QFrame#stepRow[state="failed"] {{
    background: rgba(255, 92, 104, 30);
    border: 1px solid {theme.danger};
}}
QLabel#h1 {{
    font-size: 20px;
    font-weight: 700;
}}
QLabel#h2 {{
    font-size: 15px;
    font-weight: 600;
}}
QLabel#muted {{
    color: {theme.muted};
}}
QLabel#value {{
    font-weight: 600;
}}
QLabel#metricLabel {{
    font-size: 12px;
    color: {theme.muted};
}}
QLabel#metricValue {{
    font-size: 20px;
    font-weight: 700;
    color: {theme.text};
}}
QLabel#metricHint {{
    font-size: 11px;
    color: {theme.muted};
}}
QLabel#stepIcon {{
    font-size: 15px;
}}
QLabel#stepText {{
    font-size: 13px;
    color: {theme.muted};
}}
QLabel#stepStatus {{
    font-size: 13px;
    font-weight: 700;
}}
QLabel#stepStatus[state="current"] {{
    color: {theme.accent};
}}
QLabel#stepStatus[state="done"] {{
    color: {theme.success};
}}
QLabel#stepStatus[state="failed"] {{
    color: {theme.danger};
}}
QLabel#stepStatus[state="pending"] {{
    color: {theme.muted};
}}
QLabel#chip {{
    background-color: {theme.panel_alt};
    border: {BORDER_WIDTH}px solid {theme.border};
    border-radius: {CONTROL_RADIUS}px;
    padding: 4px 10px;
    font-size: 12px;
    color: {theme.muted};
}}
QLabel#chipStrong {{
    background-color: {theme.panel_alt};
    border: {BORDER_WIDTH}px solid {theme.border};
    border-radius: {CONTROL_RADIUS}px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 600;
    color: {theme.text};
}}
QLabel#resultPath {{
    font-family: "{MONO_FONT}";
    font-size: 11px;
    color: {theme.muted};
    background-color: {theme.input_bg};
    border-radius: {CARD_BODY_RADIUS}px;
    padding: 6px 8px;
}}
QLineEdit {{
    background-color: {theme.input_bg};
    border: {BORDER_WIDTH}px solid {theme.border};
    border-radius: {CONTROL_RADIUS}px;
    padding: 9px 12px;
    selection-background-color: {theme.accent};
}}
QLineEdit:focus {{
    border-color: {theme.accent};
}}
QPushButton {{
    background-color: {theme.panel_alt};
    color: {theme.text};
    border: {BORDER_WIDTH}px solid {theme.border};
    border-radius: {CONTROL_RADIUS}px;
    padding: 8px 16px;
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: {theme.panel};
    border-color: {theme.accent};
}}
QPushButton:pressed {{
    background-color: {theme.border};
}}
QPushButton:disabled {{
    color: {theme.muted};
    background-color: {theme.panel_alt};
}}
QPushButton#primaryButton {{
    background-color: {theme.accent};
    color: {theme.accent_text};
    border: none;
    padding: 9px 22px;
}}
QPushButton#primaryButton:hover {{
    background-color: {theme.accent_hover};
}}
QPushButton#primaryButton:disabled {{
    background-color: {theme.border};
    color: {theme.muted};
}}
QPushButton#linkButton {{
    background: transparent;
    border: none;
    color: {theme.accent};
    padding: 4px 8px;
}}
QProgressBar {{
    background-color: {theme.input_bg};
    border: {BORDER_WIDTH}px solid {theme.border};
    border-radius: {CONTROL_RADIUS}px;
    text-align: center;
    color: {theme.text};
    min-height: 20px;
}}
QProgressBar::chunk {{
    background-color: {theme.accent};
    border-radius: {CONTROL_RADIUS - 1}px;
}}
QPlainTextEdit, QTextEdit {{
    background-color: {theme.input_bg};
    border: {BORDER_WIDTH}px solid {theme.border};
    border-radius: {CONTROL_RADIUS}px;
    font-family: "{MONO_FONT}";
    font-size: 12px;
    color: {theme.text};
    padding: 6px;
}}
QTextEdit#logView {{
    background-color: {theme.input_bg};
    border: {BORDER_WIDTH}px solid {theme.border};
    border-radius: {CONTROL_RADIUS}px;
    font-family: "{MONO_FONT}";
    font-size: 12px;
    color: {theme.text};
    padding: 8px;
    selection-background-color: {theme.accent};
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollArea#panelScroll {{
    background: transparent;
    border: none;
}}
QWidget#scrollContent {{
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: {theme.border};
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {theme.muted};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QSplitter::handle {{
    background: transparent;
}}
QSplitter::handle:horizontal {{
    width: 8px;
}}
QSplitter::handle:vertical {{
    height: 8px;
}}
QToolTip {{
    background-color: {theme.panel_alt};
    color: {theme.text};
    border: {BORDER_WIDTH}px solid {theme.border};
}}
"""
