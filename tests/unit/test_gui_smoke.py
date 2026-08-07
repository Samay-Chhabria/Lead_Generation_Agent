"""Offscreen smoke tests for the desktop GUI (PySide6).

The GUI is presentation-only: these tests verify that a real MainWindow
constructs, that every panel reacts to AgentExecutionLogger events, that the
theme can be toggled, and that a full agent run started from the window
updates the timeline/logs/stats/results without touching the UI thread. All
rendering happens on Qt's offscreen platform so no display is required.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import pytest
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from app.config.settings import Settings
from app.execution.execution_logger import (
    EVENT_AGENT_STARTED,
    EVENT_BUSINESS_DONE,
    EVENT_BUSINESS_STARTED,
    EVENT_ERROR,
    EVENT_FINISHED,
    EVENT_LAUNCHING_BROWSER,
    EVENT_PHASE,
    EVENT_PLANNING,
    EVENT_PROGRESS,
    EVENT_RECOVERED,
    EVENT_RETRYING,
    EVENT_TOOL_STARTED,
    EVENT_TOOL_SUCCEEDED,
    ExecutionEvent,
)
from app.gui.main_window import MainWindow
from app.gui.resources.tokens import (
    STEP_CURRENT_PROPERTY,
    STEP_CURRENT_VALUE,
    STEP_DONE_VALUE,
    STEP_PENDING_VALUE,
)
from app.gui.themes import DARK, LIGHT
from app.models.execution_result import ExecutionResult
from app.models.lead import Lead
from tests.fakes import FakeBrowser, build_fixed_factory


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    """A single QApplication for the whole module."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        headless=True,
        timeout=2_000,
        max_leads=10,
        search_provider="fixed",
        browser_type="chromium",
        output_dir=tmp_path / "outputs",
        log_dir=tmp_path / "logs",
        log_level="WARNING",
    )


def _make_window(qapp: QApplication, tmp_path: Path, builder=None) -> MainWindow:
    window = MainWindow(qapp, settings=_settings(tmp_path), agent_builder=builder)
    return window


def _event(kind: str, message: str = "", **data) -> ExecutionEvent:
    return ExecutionEvent(kind=kind, message=message, data=data)


# --- Construction & theme -----------------------------------------------------


def test_window_constructs_with_all_panels(qapp: QApplication, tmp_path: Path) -> None:
    window = _make_window(qapp, tmp_path)
    try:
        assert window.windowTitle() == "Lead Generation Agent"
        for attr in (
            "plan",
            "timeline",
            "stats",
            "business",
            "logs",
            "progress",
            "results",
            "error_card",
        ):
            assert getattr(window, attr) is not None, attr
        assert window.prompt_input.placeholderText()
        assert window.search_button.isEnabled()
    finally:
        window.controller.shutdown()


def test_theme_toggle_changes_stylesheet(qapp: QApplication, tmp_path: Path) -> None:
    window = _make_window(qapp, tmp_path)
    try:
        dark = qapp.styleSheet()
        window.apply_theme(LIGHT)
        assert qapp.styleSheet() != dark
        assert window.theme_button.text().startswith("🌙")
        window.apply_theme(DARK)
        assert qapp.styleSheet() == dark
    finally:
        window.controller.shutdown()


# --- Panel reactions to events --------------------------------------------------


def test_plan_panel_populates_from_planning_event(qapp: QApplication, tmp_path: Path) -> None:
    window = _make_window(qapp, tmp_path)
    try:
        window._on_event(
            _event(
                EVENT_PLANNING,
                "Plan ready",
                goal="software companies in Karachi",
                business_type="software companies",
                location="Karachi",
                provider="fixed",
                max_results=10,
                needs_crawl=True,
                export=True,
                steps=[{"tool": "google_maps_search"}, {"tool": "lead_exporter"}],
            )
        )
        assert "software companies in Karachi" in window.plan._goal.text()
        assert "Fixed" in window.plan._labels["Provider"].text()
        assert "Yes" in window.plan._labels["Website Crawling"].text()
        assert "Google Maps Search" in window.plan._steps.text()
    finally:
        window.controller.shutdown()


def test_new_search_clears_stale_plan_before_repopulating(
    qapp: QApplication, tmp_path: Path
) -> None:
    window = _make_window(qapp, tmp_path)
    try:

        def plan_event(business_type: str, location: str) -> ExecutionEvent:
            return _event(
                EVENT_PLANNING,
                "Plan ready",
                goal=f"{business_type} in {location}",
                business_type=business_type,
                location=location,
                provider="fixed",
                max_results=10,
                needs_crawl=False,
                export=True,
                steps=[{"tool": "google_maps_search"}, {"tool": "lead_exporter"}],
            )

        window._on_event(plan_event("dentists", "Clifton"))
        assert "dentists" in window.plan._labels["Business Type"].text()
        assert "Clifton" in window.plan._labels["Location"].text()

        window.prompt_input.setText("find me best skin specialist in karachi")
        window._reset_run()
        assert window.plan._labels["Business Type"].text() == "—"
        assert "dentists" not in window.plan._labels["Business Type"].text()

        window._on_event(plan_event("skin specialist", "Karachi"))
        assert window.plan._labels["Business Type"].text() == "skin specialist"
        assert window.plan._labels["Location"].text() == "Karachi"
        assert "dentists" not in window.plan._goal.text()
        assert "Clifton" not in window.plan._goal.text()
    finally:
        window.controller.shutdown()


def test_timeline_steps_transition_through_run(qapp: QApplication, tmp_path: Path) -> None:
    window = _make_window(qapp, tmp_path)
    try:
        timeline = window.timeline

        def state(key: str) -> str:
            return timeline._rows[key].property(STEP_CURRENT_PROPERTY)

        assert state("understanding") == STEP_PENDING_VALUE
        window._on_event(_event(EVENT_AGENT_STARTED, "Agent started"))
        assert state("understanding") == STEP_CURRENT_VALUE
        window._on_event(_event(EVENT_PLANNING, "Plan ready", steps=[]))
        assert state("planning") == STEP_DONE_VALUE
        assert state("launch") == STEP_CURRENT_VALUE
        window._on_event(_event(EVENT_LAUNCHING_BROWSER, "Launching"))
        assert state("launch") == STEP_DONE_VALUE
        window._on_event(_event(EVENT_TOOL_STARTED, "", tool="google_maps_search", display="x"))
        assert state("search") == STEP_CURRENT_VALUE
        window._on_event(_event(EVENT_TOOL_SUCCEEDED, "", tool="google_maps_search", display="x"))
        assert state("search") == STEP_DONE_VALUE

        result = ExecutionResult(success=True)
        window._on_event(_event(EVENT_FINISHED, "Finished", result=result))
        assert state("finished") == STEP_DONE_VALUE
    finally:
        window.controller.shutdown()


def test_stats_business_and_progress_update_from_events(qapp: QApplication, tmp_path: Path) -> None:
    window = _make_window(qapp, tmp_path)
    try:
        window._on_event(_event(EVENT_PHASE, "", phase="Searching"))
        window._on_event(
            _event(
                EVENT_TOOL_STARTED,
                "",
                tool="business_details",
                display="Business Details",
                step=2,
                total=5,
            )
        )
        assert window.progress._status.text() == "Running Business Details..."
        window._on_event(
            _event(
                EVENT_PROGRESS,
                "Businesses Processed 2/5",
                processed=2,
                total=5,
            )
        )
        assert window.progress._business.text() == "Business 2 / 5"

        window._on_event(
            _event(
                EVENT_BUSINESS_STARTED,
                "Opening Business Alpha Corp",
                business="Alpha Corp",
                tool="business_details",
            )
        )
        assert "Alpha Corp" in window.business._name.text()

        window._on_event(
            _event(
                EVENT_BUSINESS_DONE,
                "",
                business="Alpha Corp",
                tool="website_crawler",
                detail="https://alpha.example",
                success=True,
            )
        )
        assert window.business._fields["website"].text() == "✓ Crawled"
        assert window.stats._values["websites_found"].text() == "1"
        window.stats.set_runtime(12.0)
        assert window.stats._values["runtime"].text() == "12s"
    finally:
        window.controller.shutdown()


def test_error_card_shows_and_recovers(qapp: QApplication, tmp_path: Path) -> None:
    window = _make_window(qapp, tmp_path)
    try:
        assert window.error_card.isHidden()
        window._on_event(_event(EVENT_ERROR, "", step="Business Details", reason="Timeout"))
        assert not window.error_card.isHidden()
        assert window.error_card._reason.text() == "Timeout"
        window._on_event(_event(EVENT_RETRYING, "", step="Business Details", attempt=2, maximum=3))
        assert window.error_card._recovery.text() == "Retrying... Attempt 2/3"
        window._on_event(_event(EVENT_RECOVERED, "", step="Business Details"))
        assert window.error_card._recovery.text() == "Recovered Successfully — Continuing..."
    finally:
        window.controller.shutdown()


def test_results_panel_renders_completion(qapp: QApplication, tmp_path: Path) -> None:
    window = _make_window(qapp, tmp_path)
    try:
        output = tmp_path / "outputs" / "leads.xlsx"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.touch()
        result = ExecutionResult(
            search_query="software companies in Karachi",
            collected_leads=5,
            processed_leads=4,
            execution_time=42.7,
            excel_output_path=output,
            success=True,
        )
        window.results.show_result(result)
        assert "Task Completed Successfully" in window.results._status.text()
        assert "Businesses Found: 5" in window.results._rows["businesses"].text()
        assert "Leads Saved: 4" in window.results._rows["leads"].text()
        assert "leads.xlsx" in window.results._rows["output"].text()
        assert window.results._open_excel.isEnabled()
    finally:
        window.controller.shutdown()


# --- Full run through the controller ---------------------------------------------


def test_full_run_updates_every_panel(qapp: QApplication, tmp_path: Path) -> None:
    window = None
    loop = QEventLoop()
    outcome: list[str] = []
    try:
        window = _make_window(qapp, tmp_path)

        leads = [
            Lead(
                business_name="Alpha Corp",
                website="https://alpha.example",
                provider="fixed",
                search_query="software companies in Karachi",
            ),
            Lead(
                business_name="Beta Ltd",
                website="https://beta.example",
                provider="fixed",
                search_query="software companies in Karachi",
            ),
        ]
        factory = build_fixed_factory(window._settings, FakeBrowser(), leads)

        def build() -> object:
            from app.agent.lead_generation_agent import LeadGenerationAgent
            from app.gui.controllers.agent_controller import build_worker_logger

            return LeadGenerationAgent(
                settings=window._settings,
                logger=build_worker_logger(),
                factory=factory,
            )

        window.controller.start("software companies in Karachi", build)
        window.controller.run_finished.connect(lambda _r: outcome.append("ok"))
        window.controller.run_finished.connect(loop.quit)
        window.controller.run_failed.connect(lambda m: outcome.append(f"fail:{m}"))
        window.controller.run_failed.connect(loop.quit)
        QTimer.singleShot(30_000, loop.quit)
        loop.exec()

        assert outcome and outcome[0] == "ok", outcome
        assert window.results._rows["businesses"].text() == "Businesses Found: 2"
        assert window.results._status.text() == "✅ Task Completed Successfully"
        assert window.timeline._rows["finished"].property(STEP_CURRENT_PROPERTY) == STEP_DONE_VALUE
        assert window.logs._view.toPlainText()
        for _ in range(50):
            qapp.processEvents()
            if window.search_button.isEnabled():
                break
        assert window.search_button.isEnabled()
        assert not window.controller.busy
        assert window.progress._bar.value() == 100
    finally:
        if window is not None:
            window.controller.shutdown()
