"""Desktop GUI entry point.

Run with::

    python -m app.gui.main

Sets up the Qt application, builds the MainWindow and starts the event loop.
The theme can be selected with the ``GUI_THEME`` environment variable
(``dark`` or ``light``); every other setting comes from the usual environment
variables / ``.env`` file via :class:`app.config.settings.Settings`.
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    """Launch the desktop interface and return the Qt exit code."""
    from PySide6.QtWidgets import QApplication

    from app.config.settings import Settings
    from app.gui.main_window import MainWindow
    from app.gui.themes import LIGHT

    app = QApplication(sys.argv)
    app.setApplicationName("Lead Generation Agent")
    app.setOrganizationName("AI Season")

    settings = Settings.from_env()
    settings.prepare()
    window = MainWindow(app, settings=settings)
    if os.getenv("GUI_THEME", "dark").strip().lower() == "light":
        window.apply_theme(LIGHT)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
