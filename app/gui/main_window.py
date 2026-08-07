"""Main application window for the desktop GUI.

Assembles the header, prompt bar, progress bar and the two-column panel layout
(timeline/plan/statistics on the left; business card, live logs and results on
the right), then wires the AgentController signals to every panel. The window
itself is presentation only — all backend work happens on the controller's
worker thread and arrives here as marshalled Qt signals.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.config.settings import Settings
from app.gui.controllers import AgentController
from app.gui.resources.tokens import (
    LAYOUT_MARGIN,
    PANEL_SPACING,
    WINDOW_DEFAULT_HEIGHT,
    WINDOW_DEFAULT_WIDTH,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
)
from app.gui.themes import DARK, LIGHT
from app.gui.themes.qss import build_qss
from app.gui.widgets import (
    BusinessCard,
    ErrorCard,
    LiveLogsPanel,
    PlanPanel,
    ProgressPanel,
    ResultsPanel,
    StatsPanel,
    TimelinePanel,
)

_PROMPT_PLACEHOLDER = (
    "e.g. 'Coffee shops in America', 'Software companies in Karachi', " "'Dentists near me'"
)


class MainWindow(QMainWindow):
    """Lead Generation Agent desktop interface."""

    def __init__(
        self,
        app: object,
        settings: Settings | None = None,
        agent_builder: Callable[[], object] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._app = app
        self._settings = settings or Settings.from_env()
        self._builder = agent_builder or self._default_builder
        self._theme = DARK
        self._last_prompt = ""
        self._run_started_at = 0.0

        self.setWindowTitle("Lead Generation Agent")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)

        self.controller = AgentController(self)
        self._build_ui()
        self._wire_signals()
        self.apply_theme(self._theme)

    # -- UI construction ----------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(LAYOUT_MARGIN, LAYOUT_MARGIN, LAYOUT_MARGIN, LAYOUT_MARGIN)
        root.setSpacing(PANEL_SPACING)

        root.addWidget(self._build_header())
        root.addWidget(self._build_prompt_bar())
        self.progress = ProgressPanel()
        root.addWidget(self.progress)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(10)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(PANEL_SPACING)
        self.plan = PlanPanel()
        self.timeline = TimelinePanel()
        self.stats = StatsPanel()
        left_layout.addWidget(self.plan, 1)
        left_layout.addWidget(self.timeline, 2)
        left_layout.addWidget(self.stats, 1)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(PANEL_SPACING)
        self.business = BusinessCard()
        self.error_card = ErrorCard()
        self.logs = LiveLogsPanel()
        self.results = ResultsPanel()
        self.business.setMinimumHeight(96)
        self.error_card.setMinimumHeight(0)
        self.results.setMinimumHeight(140)
        self.logs.setMinimumHeight(180)
        right_layout.addWidget(self.business, 1)
        right_layout.addWidget(self.error_card, 0)
        right_layout.addWidget(self.logs, 3)
        right_layout.addWidget(self.results, 1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([480, 720])
        root.addWidget(splitter, 1)

    def _build_header(self) -> QWidget:
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("🤖  Lead Generation Agent")
        title.setObjectName("h1")
        subtitle = QLabel("Live execution of your lead generation run")
        subtitle.setObjectName("muted")
        self.theme_button = QPushButton("🌙  Dark")
        self.theme_button.clicked.connect(self._toggle_theme)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch(1)
        layout.addWidget(self.theme_button)
        return header

    def _build_prompt_bar(self) -> QWidget:
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(PANEL_SPACING)
        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText(_PROMPT_PLACEHOLDER)
        self.prompt_input.setClearButtonEnabled(True)
        self.search_button = QPushButton("🚀  Search")
        self.search_button.setObjectName("primaryButton")
        layout.addWidget(self.prompt_input, 1)
        layout.addWidget(self.search_button)
        return bar

    def _wire_signals(self) -> None:
        self.search_button.clicked.connect(self._start_run)
        self.prompt_input.returnPressed.connect(self._start_run)
        self.controller.event_received.connect(self._on_event)
        self.controller.run_finished.connect(self._on_run_finished)
        self.controller.run_failed.connect(self._on_run_failed)
        self.controller.busy_changed.connect(self._on_busy_changed)
        self.results.run_again.connect(self._run_again)

        self._runtime_timer = QTimer(self)
        self._runtime_timer.setInterval(1000)
        self._runtime_timer.timeout.connect(self._tick_runtime)

        shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        shortcut.activated.connect(self._start_run)

    # -- Theme --------------------------------------------------------------

    def apply_theme(self, theme: object) -> None:
        """Apply a theme to the whole application."""
        self._theme = theme
        self._app.setStyleSheet(build_qss(theme))
        self.logs.apply_theme(theme)
        self.results.apply_theme(theme)
        self.theme_button.setText("☀️  Light" if theme is DARK else "🌙  Dark")

    def _toggle_theme(self) -> None:
        self.apply_theme(LIGHT if self._theme is DARK else DARK)

    # -- Run lifecycle ------------------------------------------------------

    def _start_run(self) -> None:
        if self.controller.busy:
            return
        prompt = self.prompt_input.text().strip()
        if not prompt:
            return
        self._last_prompt = prompt
        self._reset_run()
        self._run_started_at = time.perf_counter()
        self._runtime_timer.start()
        self._stats_tick()
        self.controller.start(prompt, self._builder)

    def _run_again(self) -> None:
        if self._last_prompt:
            self.prompt_input.setText(self._last_prompt)
        self._start_run()

    def _reset_run(self) -> None:
        for panel in (self.plan, self.timeline, self.stats, self.business):
            panel.reset()
        self.logs.reset()
        self.progress.reset()
        self.results.reset()
        self.error_card.reset()

    def _on_busy_changed(self, busy: bool) -> None:
        self.search_button.setEnabled(not busy)
        if not busy:
            self._runtime_timer.stop()

    def _tick_runtime(self) -> None:
        self._stats_tick()

    def _stats_tick(self) -> None:
        elapsed = time.perf_counter() - self._run_started_at
        self.stats.set_runtime(elapsed)

    def _on_event(self, event: object) -> None:
        for panel in (self.plan, self.timeline, self.stats, self.business):
            panel.on_event(event)
        self.logs.append_event(event)
        self.progress.on_event(event)
        self.error_card.on_event(event)

    def _on_run_finished(self, result: object) -> None:
        elapsed = time.perf_counter() - self._run_started_at
        self.stats.set_runtime(elapsed)
        self.results.show_result(result)

    def _on_run_failed(self, message: str) -> None:
        elapsed = time.perf_counter() - self._run_started_at
        self.stats.set_runtime(elapsed)
        self.results.show_error(message)

    # -- Backend construction -----------------------------------------------

    def _default_builder(self) -> object:
        """Build the shared backend agent (runs on the worker thread)."""
        from app.agent.lead_generation_agent import LeadGenerationAgent
        from app.gui.controllers.agent_controller import build_worker_logger

        return LeadGenerationAgent(settings=self._settings, logger=build_worker_logger())

    # -- Lifecycle ----------------------------------------------------------

    def closeEvent(self, event: object) -> None:  # noqa: N802
        """Clean up the execution-logger subscription on close."""
        self.controller.shutdown()
        super().closeEvent(event)
