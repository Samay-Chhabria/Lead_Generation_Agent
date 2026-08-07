"""Event-driven execution logger for the agent's activity timeline.

Every working component — planner, executor, tools, providers, extractors and
the exporter — reports what it is about to do, what it completed, and what went
wrong by publishing :class:`ExecutionEvent` objects through the shared
:class:`AgentExecutionLogger`. The logger is a plain publisher-subscriber bus:
it owns the timeline state (plan, tool history, timings, progress) and forwards
every event to its subscribers in order.

Subscribers are presentation layers and nothing else. The terminal subscriber
renders the human-readable timeline, the desktop GUI re-emits the same events
into its live view. The logger deliberately carries no formatting and no
business logic, and it never exposes the LLM's chain-of-thought: only the
safe, structured activity events described below.

The single process-wide logger is obtained through :func:`get_execution_logger`.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# Event kinds ---------------------------------------------------------------

EVENT_AGENT_STARTED = "agent_started"
EVENT_UNDERSTANDING = "understanding"
EVENT_PLANNING = "planning"
EVENT_PLANNING_FAILED = "planning_failed"
EVENT_LLM_MODEL_SELECTED = "llm_model_selected"
EVENT_SELECTING_PROVIDER = "selecting_provider"
EVENT_LAUNCHING_BROWSER = "launching_browser"
EVENT_PHASE = "phase"
EVENT_TOOL_STARTED = "tool_started"
EVENT_TOOL_SUCCEEDED = "tool_succeeded"
EVENT_TOOL_FAILED = "tool_failed"
EVENT_BUSINESS_STARTED = "business_started"
EVENT_BUSINESS_DONE = "business_done"
EVENT_PROGRESS = "progress"
EVENT_ERROR = "error"
EVENT_RETRYING = "retrying"
EVENT_RECOVERED = "recovered"
EVENT_TIMING = "timing"
EVENT_HISTORY = "history"
EVENT_SUMMARY = "summary"
EVENT_FINISHED = "finished"

# The phases the user watches for are published as ``EVENT_PHASE`` events with
# the human phase name in ``event.data["phase"]``, so subscribers can render
# them without parsing log text.

_TOOL_DISPLAY_NAMES = {
    "google_maps_search": "Google Maps Search",
    "search": "Google Maps Search",
    "business_collection": "Business Collection",
    "business_details": "Business Details",
    "business_extraction": "Business Extraction",
    "website_crawler": "Website Crawler",
    "email_extractor": "Email Extractor",
    "phone_extractor": "Phone Extractor",
    "lead_exporter": "Excel Exporter",
    "export": "Excel Exporter",
    "navigation": "Navigation",
    "pipeline": "Pipeline",
    "summary": "Summary",
}

# The per-business action phrase used while a tool works on one business.
_BUSINESS_ACTIONS = {
    "business_details": "Extracting details",
    "website_crawler": "Crawling website",
    "email_extractor": "Extracting email",
    "phone_extractor": "Extracting phone",
}

Listener = Callable[["ExecutionEvent"], None]


def tool_display_name(name: str) -> str:
    """Return the user-facing display name of a tool."""
    return _TOOL_DISPLAY_NAMES.get(name, name.replace("_", " ").title())


def business_action(tool: str) -> str:
    """Return the human phrase describing a tool working on one business."""
    return _BUSINESS_ACTIONS.get(tool, "Processing")


@dataclass(frozen=True, slots=True)
class ExecutionEvent:
    """One structured activity record published to every subscriber."""

    kind: str
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: time.perf_counter())


class AgentExecutionLogger:
    """Thread-safe publisher-subscriber bus owning the timeline state.

    Emitters are the components that do the work; they call the ``*_started``,
    ``*_done``, ``*_succeeded`` and similar methods below. Subscribers receive
    every published event in the order it was emitted. Subscribers must never
    raise; a failing subscriber is skipped so it cannot break the run.
    """

    def __init__(self) -> None:
        self._subscribers: list[Listener] = []
        self._lock = threading.Lock()
        self._history: list[dict[str, Any]] = []
        self._timings: dict[str, float] = {}
        self._summary: dict[str, Any] = {}
        self._started_at = time.perf_counter()

    # -- Subscriber management ---------------------------------------------

    def subscribe(self, listener: Listener) -> None:
        """Register a listener to receive every future event."""
        with self._lock:
            if listener not in self._subscribers:
                self._subscribers.append(listener)

    def unsubscribe(self, listener: Listener) -> None:
        """Remove a previously registered listener."""
        with self._lock:
            if listener in self._subscribers:
                self._subscribers.remove(listener)

    def clear(self) -> None:
        """Reset the timeline state for a new run (subscribers are kept)."""
        with self._lock:
            self._history = []
            self._timings = {}
            self._summary = {}
            self._started_at = time.perf_counter()

    # -- Publishing ---------------------------------------------------------

    def _publish(self, kind: str, message: str = "", data: dict[str, Any] | None = None) -> None:
        event = ExecutionEvent(kind=kind, message=message, data=data or {})
        with self._lock:
            for listener in list(self._subscribers):
                try:
                    listener(event)
                except Exception:  # pragma: no cover - subscriber isolation
                    continue

    # -- Agent lifecycle ----------------------------------------------------

    def agent_started(self, prompt: str) -> None:
        """Publish the start of a run with the user's request."""
        self._publish(
            EVENT_AGENT_STARTED,
            message=f"User Request: {prompt}",
            data={"prompt": prompt},
        )

    def understanding(
        self,
        business_type: str,
        location: str,
        *,
        wants_emails: bool = False,
        wants_websites: bool = False,
        wants_phones: bool = False,
        min_rating: float | None = None,
    ) -> None:
        """Publish the parsed understanding of the user's request."""
        self._publish(
            EVENT_UNDERSTANDING,
            message=f"Understanding request: {business_type} in {location}",
            data={
                "business_type": business_type,
                "location": location,
                "wants_emails": wants_emails,
                "wants_websites": wants_websites,
                "wants_phones": wants_phones,
                "min_rating": min_rating,
            },
        )

    def planning(
        self,
        *,
        goal: str,
        steps: list[dict[str, str]],
        expected_leads: int,
        provider: str,
        business_type: str,
        location: str,
        max_results: int,
        needs_crawl: bool,
        export: bool,
        estimated_runtime: str,
    ) -> None:
        """Publish the execution plan before any tool runs."""
        names = [step["tool"] for step in steps]
        self._publish(
            EVENT_PLANNING,
            message=f"Plan created: {' -> '.join(names)}",
            data={
                "goal": goal,
                "steps": list(steps),
                "expected_leads": expected_leads,
                "provider": provider,
                "business_type": business_type,
                "location": location,
                "max_results": max_results,
                "needs_crawl": needs_crawl,
                "export": export,
                "estimated_runtime": estimated_runtime,
            },
        )

    def planning_failed(self, reason: str) -> None:
        """Publish a failure to build a plan for the request."""
        self._publish(EVENT_PLANNING_FAILED, message=reason, data={"reason": reason})

    def llm_model_selected(self, model: str, reason: str = "") -> None:
        """Publish the model actually used by the most recent LLM call.

        The model is the one the FreeLLM Router reports in its response, or
        ``"auto"`` when the router reports none (the router selects the model
        automatically; the application never names one).
        """
        self._publish(
            EVENT_LLM_MODEL_SELECTED,
            message=f"Trying model: {model}",
            data={"model": model, "reason": reason},
        )

    def selecting_provider(self, provider: str) -> None:
        """Publish the provider chosen for the search."""
        self._publish(
            EVENT_SELECTING_PROVIDER,
            message=f"Selecting Provider: {provider}",
            data={"provider": provider},
        )

    def launching_browser(self) -> None:
        """Publish that the shared browser is being launched."""
        self._publish(EVENT_LAUNCHING_BROWSER, message="Launching Browser...")

    def phase(self, name: str, message: str | None = None) -> None:
        """Publish a coarse workflow phase (Navigating, Searching, ...)."""
        self._publish(
            EVENT_PHASE,
            message=message or f"{name}...",
            data={"phase": name},
        )

    # -- Tool lifecycle -----------------------------------------------------

    def tool_started(
        self,
        tool: str,
        *,
        step: int,
        total: int,
        description: str = "",
    ) -> None:
        """Publish that a tool is about to run."""
        self._publish(
            EVENT_TOOL_STARTED,
            message=f"Executing tool: {tool}",
            data={
                "tool": tool,
                "display": tool_display_name(tool),
                "step": step,
                "total": total,
                "description": description,
            },
        )

    def tool_succeeded(self, tool: str, detail: str = "", seconds: float | None = None) -> None:
        """Publish a successful tool run and record it in the history."""
        self._publish(
            EVENT_TOOL_SUCCEEDED,
            message=f"Tool finished: {tool}",
            data={"tool": tool, "display": tool_display_name(tool), "detail": detail},
        )
        self._record_history(tool, "success", detail, seconds)

    def tool_failed(self, tool: str, reason: str, seconds: float | None = None) -> None:
        """Publish a failed tool run and record it in the history."""
        self._publish(
            EVENT_TOOL_FAILED,
            message=f"Tool failed: {tool}",
            data={"tool": tool, "display": tool_display_name(tool), "reason": reason},
        )
        self._record_history(tool, "failed", reason, seconds)

    # -- Per-business progress ----------------------------------------------

    def business_started(self, tool: str, business_name: str, index: int, total: int) -> None:
        """Publish that a tool started working on one business."""
        action = business_action(tool)
        self._publish(
            EVENT_BUSINESS_STARTED,
            message=f"{action} for '{business_name}'.",
            data={
                "tool": tool,
                "display": tool_display_name(tool),
                "business": business_name,
                "index": index,
                "total": total,
            },
        )

    def business_done(
        self, tool: str, business_name: str, success: bool = True, detail: str = ""
    ) -> None:
        """Publish that a tool finished working on one business."""
        self._publish(
            EVENT_BUSINESS_DONE,
            message=f"Business processed: {business_name}",
            data={
                "tool": tool,
                "business": business_name,
                "success": success,
                "detail": detail,
            },
        )

    def progress(self, processed: int, total: int) -> None:
        """Publish the current business progress count."""
        self._publish(
            EVENT_PROGRESS,
            message=f"Progress: Businesses Processed {processed}/{total}",
            data={"processed": processed, "total": total},
        )

    # -- Error reporting and recovery ---------------------------------------

    def error(self, current_step: str, reason: str) -> None:
        """Publish an error encountered at a workflow step."""
        self._publish(
            EVENT_ERROR,
            message=f"Error encountered: {current_step}",
            data={"step": current_step, "status": "FAILED", "reason": reason},
        )

    def retrying(self, step: str, attempt: int, maximum: int) -> None:
        """Publish that a failed step is being retried."""
        self._publish(
            EVENT_RETRYING,
            message=f"Recovery: Retrying {step}... Attempt {attempt}/{maximum}",
            data={"step": step, "attempt": attempt, "maximum": maximum},
        )

    def recovered(self, step: str) -> None:
        """Publish that a retried step succeeded."""
        self._publish(
            EVENT_RECOVERED,
            message=f"Recovered Successfully: {step}",
            data={"step": step},
        )

    # -- Metrics and finalization -------------------------------------------

    def timing(self, label: str, seconds: float) -> None:
        """Record a named duration and publish it."""
        self._timings[label] = seconds
        self._publish(
            EVENT_TIMING,
            message=f"Timing: {label} = {seconds:.1f}s",
            data={"label": label, "seconds": seconds},
        )

    def summary(
        self,
        result: Any,
        *,
        successful_leads: int | None = None,
        missing_emails: int | None = None,
        missing_websites: int | None = None,
    ) -> None:
        """Publish the final run summary and its lead statistics."""
        self._summary = {
            "result": result,
            "successful_leads": successful_leads,
            "missing_emails": missing_emails,
            "missing_websites": missing_websites,
        }
        self._publish(EVENT_SUMMARY, message="Summary generated.", data=self._summary)

    def finished(self, result: Any) -> None:
        """Publish the end of the run with its outcome."""
        success = bool(getattr(result, "success", False))
        message = (
            f"Agent run finished: {getattr(result, 'collected_leads', 0)} collected, "
            f"{getattr(result, 'processed_leads', 0)} processed, "
            f"exported={getattr(result, 'excel_output_path', None)}."
        )
        self._publish(
            EVENT_FINISHED,
            message=message,
            data={"result": result, "status": "SUCCESS" if success else "FAILED"},
        )

    # -- Snapshot -----------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        """Return a copy of the timeline state for subscribers to read."""
        with self._lock:
            return {
                "history": list(self._history),
                "timings": dict(self._timings),
                "summary": dict(self._summary),
                "elapsed": time.perf_counter() - self._started_at,
            }

    @property
    def history(self) -> list[dict[str, Any]]:
        """Return the recorded tool history."""
        return self.snapshot()["history"]

    @property
    def timings(self) -> dict[str, float]:
        """Return the recorded named durations."""
        return self.snapshot()["timings"]

    # -- Internals ----------------------------------------------------------

    def _record_history(self, tool: str, status: str, detail: str, seconds: float | None) -> None:
        entry = {
            "tool": tool,
            "display": tool_display_name(tool),
            "status": status,
            "detail": detail,
            "seconds": seconds,
        }
        with self._lock:
            self._history.append(entry)
        self._publish(
            EVENT_HISTORY,
            message=f"History: {entry['display']} {status}",
            data={"entry": entry},
        )


_execution_logger: AgentExecutionLogger | None = None
_execution_logger_lock = threading.Lock()


def get_execution_logger() -> AgentExecutionLogger:
    """Return the process-wide AgentExecutionLogger singleton."""
    global _execution_logger
    with _execution_logger_lock:
        if _execution_logger is None:
            _execution_logger = AgentExecutionLogger()
        return _execution_logger


def reset_execution_logger() -> AgentExecutionLogger:
    """Replace the singleton with a fresh logger (used by tests)."""
    global _execution_logger
    fresh = AgentExecutionLogger()
    with _execution_logger_lock:
        _execution_logger = fresh
    return fresh
