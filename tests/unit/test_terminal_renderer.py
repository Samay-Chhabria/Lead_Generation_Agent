"""Tests for the terminal timeline renderer.

These drive the TerminalRenderer through the AgentExecutionLogger exactly the
way the agent does and assert the human-readable output. They also pin the
legacy end-of-run summary strings that downstream tests rely on.
"""

import pytest

from app.execution.execution_logger import get_execution_logger, reset_execution_logger
from app.execution.terminal_renderer import TerminalRenderer
from app.models.execution_result import ExecutionResult


@pytest.fixture(autouse=True)
def _fresh_logger() -> None:
    reset_execution_logger()
    yield
    reset_execution_logger()


def _render(capsys: pytest.CaptureFixture[str]) -> str:
    output = capsys.readouterr().out
    return output


def test_renderer_shows_full_successful_timeline(
    capsys: pytest.CaptureFixture[str],
) -> None:
    log = get_execution_logger()
    renderer = TerminalRenderer()
    log.subscribe(renderer.on_event)

    log.agent_started("dentists near Clifton Karachi")
    log.understanding("dentists", "Clifton Karachi")
    log.planning(
        goal="Find dentists in Clifton Karachi and export their leads.",
        steps=[
            {"tool": "google_maps_search", "description": "Run the Maps search"},
            {"tool": "business_details", "description": "Extract details for each lead"},
        ],
        expected_leads=5,
        provider="google",
        business_type="dentists",
        location="Clifton Karachi",
        max_results=5,
        needs_crawl=True,
        export=True,
        estimated_runtime="30-60 seconds",
    )
    log.selecting_provider("google")
    log.launching_browser()
    log.phase("Searching")
    log.tool_started("google_maps_search", step=1, total=2, description="Run the Maps search")
    log.tool_succeeded("google_maps_search", "1 leads collected", seconds=1.5)
    log.tool_started("business_details", step=2, total=2, description="Extract details")
    log.business_started("business_details", "Alpha Clinic", 1, 1)
    log.progress(1, 1)
    log.business_done("business_details", "Alpha Clinic")
    log.tool_succeeded("business_details", "1 business", seconds=2.0)
    log.timing("total", 4.0)

    result = ExecutionResult(
        search_query="dentists near Clifton Karachi",
        business_type="dentists",
        location="Clifton Karachi",
        provider="google",
        collected_leads=1,
        processed_leads=1,
        excel_output_path="outputs/leads.xlsx",
        execution_time=4.0,
        success=True,
    )
    log.summary(result, successful_leads=1, missing_emails=0, missing_websites=0)
    log.finished(result)
    log.unsubscribe(renderer.on_event)

    out = _render(capsys)

    assert "🤖 Lead Generation Agent" in out
    assert "User Request: dentists near Clifton Karachi" in out
    assert "🧠 Understanding Request..." in out
    assert "✓ Business Type: dentists" in out
    assert "✓ Location: Clifton Karachi" in out
    assert "🧠 Planning..." in out
    assert "Goal: Find dentists in Clifton Karachi and export their leads." in out
    assert "1. Google Maps Search → Run the Maps search" in out
    assert "Estimated Leads: 5" in out
    assert "Selected Provider: google" in out
    assert "🛠️ Execution Plan" in out
    assert "Provider:         Google Maps" in out
    assert "Business Type:    dentists" in out
    assert "Location:         Clifton Karachi" in out
    assert "Maximum Results:  5" in out
    assert "Website Crawling: Yes" in out
    assert "Export:           Yes" in out
    assert "Estimated Runtime: 30-60 seconds" in out
    assert "Selecting Provider: google" in out
    assert "Launching Browser..." in out
    assert "Searching..." in out
    assert "🔧 Tool Execution [1/2]" in out
    assert "Running Google Maps Search..." in out
    assert "✓ Google Maps Search completed: 1 leads collected" in out
    assert "Opening Business: Alpha Clinic" in out
    assert "📈 Progress: Businesses Processed 1/1" in out
    assert "✓ Details extracted for Alpha Clinic" in out
    assert "⏱️ Timing:" in out
    assert "Total Execution Time: 4.0 seconds" in out
    assert "📋 Execution History:" in out
    assert "[✓] Google Maps Search — 1 leads collected (1.5s)" in out
    assert "Lead Generation Completed Successfully" in out
    assert "Successful Leads: 1" in out
    assert "Missing Emails: 0" in out
    assert "Missing Websites: 0" in out
    assert "Status: SUCCESS" in out


def test_renderer_shows_error_and_recovery(
    capsys: pytest.CaptureFixture[str],
) -> None:
    log = get_execution_logger()
    renderer = TerminalRenderer()
    log.subscribe(renderer.on_event)

    log.agent_started("coffee shops in Karachi")
    log.tool_started("business_details", step=1, total=1, description="Extract details")
    log.error("Business Details", "page timed out")
    log.retrying("Business Details", 1, 2)
    log.recovered("Business Details")
    log.tool_succeeded("business_details", "1 business", seconds=3.0)

    result = ExecutionResult(
        search_query="coffee shops in Karachi",
        execution_time=3.0,
        success=True,
    )
    log.finished(result)
    log.unsubscribe(renderer.on_event)

    out = _render(capsys)

    assert "⚠️ Error Encountered" in out
    assert "Current Step: Business Details" in out
    assert "Reason: page timed out" in out
    assert "Recovery: Retrying... Attempt 1/2" in out
    assert "Recovered Successfully" in out


def test_renderer_shows_planning_failure(
    capsys: pytest.CaptureFixture[str],
) -> None:
    log = get_execution_logger()
    renderer = TerminalRenderer()
    log.subscribe(renderer.on_event)

    log.agent_started("garbage without location")
    log.planning_failed("Could not understand task 'garbage without location'.")
    result = ExecutionResult(
        search_query="garbage without location",
        success=False,
    )
    log.finished(result)
    log.unsubscribe(renderer.on_event)

    out = _render(capsys)

    assert "⚠️ Planning Failed" in out
    assert "Lead Generation Failed" in out
    assert "Status: FAILED" in out


def test_renderer_shows_model_selected_with_reason(
    capsys: pytest.CaptureFixture[str],
) -> None:
    log = get_execution_logger()
    renderer = TerminalRenderer()
    log.subscribe(renderer.on_event)

    log.agent_started("coffee shops in Karachi")
    log.llm_model_selected("auto", "Auto (Router Selected)")
    log.llm_model_selected("gpt-oss-120b-groq", "Auto (Router Selected)")
    log.unsubscribe(renderer.on_event)

    out = _render(capsys)

    assert "Trying model: auto (Auto (Router Selected))" in out
    assert "Trying model: gpt-oss-120b-groq (Auto (Router Selected))" in out


def test_renderer_keeps_legacy_summary_labels(
    capsys: pytest.CaptureFixture[str],
) -> None:
    log = get_execution_logger()
    renderer = TerminalRenderer()
    log.subscribe(renderer.on_event)

    log.agent_started("software companies in Karachi")
    result = ExecutionResult(
        search_query="software companies in Karachi",
        business_type="software companies",
        location="Karachi",
        provider="google",
        collected_leads=2,
        processed_leads=2,
        excel_output_path="outputs/leads_software.xlsx",
        execution_time=12.5,
        success=True,
    )
    log.finished(result)
    log.unsubscribe(renderer.on_event)

    out = _render(capsys)

    assert "Lead Generation Completed Successfully" in out
    assert "Search Query: software companies in Karachi" in out
    assert "Business Type: software companies" in out
    assert "Location: Karachi" in out
    assert "Businesses Found: 2" in out
    assert "Leads Exported: 2" in out
    assert "Execution Time: 12.5 seconds" in out
    assert "Status: SUCCESS" in out
