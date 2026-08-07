"""PySide6 desktop GUI for the Lead Generation Agent.

The GUI is a pure presentation layer: it subscribes to the
``AgentExecutionLogger`` event bus, runs the agent on a worker thread, and
renders every event live (timeline, logs, progress, statistics, results). It
never contains planning, search, extraction, or export logic — the exact same
backend the CLI uses is reused unchanged.

Launch with ``python -m app.gui.main``.
"""

from __future__ import annotations

from app.gui.main_window import MainWindow

__all__ = ["MainWindow"]
