"""Theme definitions (colors) for the desktop GUI.

A Theme is a plain value object describing the colour palette. The QSS in
``themes.qss`` is generated from one of these, and the widgets read the palette
for programmatic colours (log lines, status text).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Theme:
    """Colour palette used to build the application stylesheet."""

    name: str
    window: str
    panel: str
    panel_alt: str
    border: str
    text: str
    muted: str
    accent: str
    accent_hover: str
    accent_text: str
    success: str
    danger: str
    warning: str
    input_bg: str
    shadow: str


DARK = Theme(
    name="dark",
    window="#0f1115",
    panel="#161a21",
    panel_alt="#1c212b",
    border="#262c38",
    text="#e6e9ef",
    muted="#8b95a6",
    accent="#4f8cff",
    accent_hover="#6b9dff",
    accent_text="#ffffff",
    success="#2fce7a",
    danger="#ff5c68",
    warning="#ffb454",
    input_bg="#0c0e12",
    shadow="#000000",
)

LIGHT = Theme(
    name="light",
    window="#eef1f6",
    panel="#ffffff",
    panel_alt="#f4f6fa",
    border="#e1e6ef",
    text="#1b2333",
    muted="#5f6b82",
    accent="#2f6fed",
    accent_hover="#245bd0",
    accent_text="#ffffff",
    success="#149e5e",
    danger="#d63447",
    warning="#c77d00",
    input_bg="#ffffff",
    shadow="#9aa4b6",
)
