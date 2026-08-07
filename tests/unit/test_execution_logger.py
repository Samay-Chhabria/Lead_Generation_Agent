"""Tests for the AgentExecutionLogger event bus."""

import threading

import pytest

from app.execution.execution_logger import (
    EVENT_AGENT_STARTED,
    EVENT_HISTORY,
    EVENT_LLM_MODEL_SELECTED,
    EVENT_PLANNING,
    EVENT_TOOL_STARTED,
    ExecutionEvent,
    business_action,
    get_execution_logger,
    reset_execution_logger,
    tool_display_name,
)


@pytest.fixture(autouse=True)
def _fresh_logger() -> None:
    reset_execution_logger()
    yield
    reset_execution_logger()


def _recorded():
    """Return a subscriber that appends every event it receives."""

    def listener(event: ExecutionEvent) -> None:
        listener.events.append(event)

    listener.events = []
    return listener


def test_logger_is_a_singleton() -> None:
    assert get_execution_logger() is get_execution_logger()


def test_reset_replaces_the_singleton() -> None:
    original = get_execution_logger()
    fresh = reset_execution_logger()

    assert fresh is not original
    assert get_execution_logger() is fresh


def test_events_are_delivered_in_order() -> None:
    log = get_execution_logger()
    listener = _recorded()
    log.subscribe(listener)

    log.agent_started("coffee shops in Karachi")
    log.selecting_provider("google")
    log.phase("Searching")

    assert [event.kind for event in listener.events] == [
        EVENT_AGENT_STARTED,
        "selecting_provider",
        "phase",
    ]
    assert listener.events[0].data["prompt"] == "coffee shops in Karachi"
    assert listener.events[1].message == "Selecting Provider: google"
    assert listener.events[2].data["phase"] == "Searching"


def test_llm_model_selected_event_carries_model_and_reason() -> None:
    log = get_execution_logger()
    listener = _recorded()
    log.subscribe(listener)

    log.llm_model_selected("auto", "Auto (Router Selected)")
    log.llm_model_selected("gpt-oss-120b-groq", "Auto (Router Selected)")

    assert [event.kind for event in listener.events] == [
        EVENT_LLM_MODEL_SELECTED,
        EVENT_LLM_MODEL_SELECTED,
    ]
    assert listener.events[0].data["model"] == "auto"
    assert "Auto (Router Selected)" in listener.events[0].data["reason"]
    assert listener.events[0].message == "Trying model: auto"
    assert listener.events[1].data["model"] == "gpt-oss-120b-groq"


def test_unsubscribe_stops_delivery() -> None:
    log = get_execution_logger()
    listener = _recorded()
    log.subscribe(listener)
    log.unsubscribe(listener)

    log.agent_started("ignored")

    assert listener.events == []


def test_failing_subscriber_is_isolated() -> None:
    log = get_execution_logger()
    healthy = _recorded()

    def broken(_event: ExecutionEvent) -> None:
        raise RuntimeError("boom")

    log.subscribe(broken)
    log.subscribe(healthy)

    log.agent_started("isolation check")

    assert len(healthy.events) == 1


def test_tool_history_is_recorded_and_published() -> None:
    log = get_execution_logger()
    listener = _recorded()
    log.subscribe(listener)

    log.tool_started("google_maps_search", step=1, total=2, description="Search")
    log.tool_succeeded("google_maps_search", "1 leads collected", seconds=1.5)
    log.tool_failed("email_extractor", "no email found", seconds=0.2)

    history_kinds = [event.kind for event in listener.events]
    assert history_kinds.count(EVENT_HISTORY) == 2
    history_events = [event for event in listener.events if event.kind == EVENT_HISTORY]
    assert history_events[0].data["entry"]["display"] == "Google Maps Search"
    assert history_events[0].data["entry"]["status"] == "success"
    assert history_events[1].data["entry"]["status"] == "failed"

    recorded = log.history
    assert [entry["status"] for entry in recorded] == ["success", "failed"]
    assert recorded[0]["seconds"] == 1.5


def test_tool_events_carry_step_information() -> None:
    log = get_execution_logger()
    listener = _recorded()
    log.subscribe(listener)

    log.tool_started("business_details", step=2, total=3, description="Extract details")

    event = listener.events[0]
    assert event.kind == EVENT_TOOL_STARTED
    assert event.data["step"] == 2
    assert event.data["total"] == 3
    assert event.data["display"] == "Business Details"
    assert event.data["description"] == "Extract details"


def test_timing_is_recorded_and_published() -> None:
    log = get_execution_logger()
    listener = _recorded()
    log.subscribe(listener)

    log.timing("total", 3.25)

    assert log.timings["total"] == 3.25
    assert listener.events[0].kind == "timing"
    assert listener.events[0].data["seconds"] == 3.25


def test_summary_and_snapshot() -> None:
    log = get_execution_logger()
    marker = object()
    log.summary(marker, successful_leads=2, missing_emails=1, missing_websites=0)

    snapshot = log.snapshot()
    assert snapshot["summary"]["result"] is marker
    assert snapshot["summary"]["successful_leads"] == 2
    assert "elapsed" in snapshot


def test_planning_event_contains_plan_data() -> None:
    log = get_execution_logger()
    listener = _recorded()
    log.subscribe(listener)

    log.planning(
        goal="Find dentists in Karachi and export their leads.",
        steps=[{"tool": "google_maps_search", "description": "Run the search"}],
        expected_leads=5,
        provider="google",
        business_type="dentists",
        location="Karachi",
        max_results=5,
        needs_crawl=True,
        export=True,
        estimated_runtime="30-60 seconds",
    )

    event = listener.events[0]
    assert event.kind == EVENT_PLANNING
    assert event.data["goal"].startswith("Find dentists")
    assert event.data["steps"][0]["tool"] == "google_maps_search"
    assert event.data["needs_crawl"] is True
    assert event.data["max_results"] == 5


def test_clear_resets_state_but_keeps_subscribers() -> None:
    log = get_execution_logger()
    listener = _recorded()
    log.subscribe(listener)
    log.tool_succeeded("search", "ok")

    log.clear()
    log.agent_started("after clear")

    assert log.history == []
    assert len(listener.events) == 3


def test_publish_is_thread_safe() -> None:
    log = get_execution_logger()
    listener = _recorded()
    log.subscribe(listener)
    barrier = threading.Barrier(5)

    def emit() -> None:
        barrier.wait()
        for index in range(20):
            log.tool_succeeded(f"tool_{index}", f"detail {index}")

    threads = [threading.Thread(target=emit) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(listener.events) == 5 * 20 * 2
    assert len(log.history) == 5 * 20


def test_display_helpers() -> None:
    assert tool_display_name("google_maps_search") == "Google Maps Search"
    assert tool_display_name("lead_exporter") == "Excel Exporter"
    assert tool_display_name("mystery_tool") == "Mystery Tool"
    assert business_action("business_details") == "Extracting details"
    assert business_action("website_crawler") == "Crawling website"
    assert business_action("unknown") == "Processing"
