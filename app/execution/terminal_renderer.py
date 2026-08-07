"""Terminal (Rich) subscriber for the agent's execution timeline.

TerminalRenderer subscribes to the AgentExecutionLogger and renders the
human-readable activity timeline described by the user: the agent header and
request, the understanding and planning blocks, each tool execution with its
before/success/failure lines, per-business progress, error and recovery
messages, and the final timing, history, and summary blocks.

The renderer is presentation only: every line is derived from the structured
ExecutionEvent objects it receives, and it never reads the agent's internal
chain-of-thought.
"""

from __future__ import annotations

import sys
from typing import Any

from rich.console import Console

from app.execution.execution_logger import (
    ExecutionEvent,
    business_action,
    tool_display_name,
)
from app.utils.execution_summary import ExecutionSummary

_PROVIDER_LABELS = {
    "google": "Google Maps",
    "google_maps": "Google Maps",
    "bing_maps": "Bing Maps",
    "yellow_pages": "Yellow Pages",
    "yelp": "Yelp",
}

_TIMING_ORDER = ("total", "browser_launch", "provider_search", "extraction", "export")
_TIMING_LABELS = {
    "total": "Total Execution Time",
    "browser_launch": "Browser Launch",
    "provider_search": "Provider Search",
    "extraction": "Extraction",
    "export": "Export",
}

_ESTIMATED_RUNTIME = "30-60 seconds"


def _ensure_utf8(stream: Any) -> Any:
    """Return a stream that can encode the timeline's unicode glyphs.

    Windows consoles default to a legacy code page (e.g. cp1252) that cannot
    encode the emoji used by the timeline, which makes Rich's writes raise
    ``UnicodeEncodeError``. Reconfigure the stream to UTF-8 so both TTY and
    piped output render identically. Streams without ``reconfigure`` (captured
    buffers) are returned unchanged.
    """
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is not None:
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):  # pragma: no cover - defensive
            pass
    return stream


class TerminalRenderer:
    """Render the execution timeline to a Rich console as events arrive."""

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console(file=_ensure_utf8(sys.stdout))
        self._timings: dict[str, float] = {}
        self._history: list[dict[str, Any]] = []
        self._summary: dict[str, Any] = {}
        self._error_active = False

    def on_event(self, event: ExecutionEvent) -> None:
        """Handle one event from the execution logger."""
        handler = getattr(self, f"_on_{event.kind}", None)
        if handler is not None:
            handler(event)

    # -- Agent lifecycle ----------------------------------------------------

    def _on_agent_started(self, event: ExecutionEvent) -> None:
        self._console.print()
        self._console.print("🤖 Lead Generation Agent", style="bold")
        self._console.print(event.message)

    def _on_understanding(self, event: ExecutionEvent) -> None:
        data = event.data
        self._console.print()
        self._console.print("🧠 Understanding Request...", style="bold")
        self._console.print(f"✓ Business Type: {data.get('business_type') or '-'}")
        self._console.print(f"✓ Location: {data.get('location') or '-'}")

    def _on_planning(self, event: ExecutionEvent) -> None:
        data = event.data
        steps = data.get("steps") or []
        self._console.print()
        self._console.print("🧠 Planning...", style="bold")
        self._console.print(f"Goal: {data.get('goal') or '-'}")
        self._console.print("Execution Plan:")
        for index, step in enumerate(steps, start=1):
            tool = step.get("tool", "")
            self._console.print(
                f"  {index}. {tool_display_name(tool)} → {step.get('description') or ''}"
            )
        self._console.print(f"Estimated Leads: {data.get('expected_leads') or 0}")
        self._console.print(f"Selected Provider: {data.get('provider') or '-'}")

        self._console.print()
        self._console.print("🛠️ Execution Plan", style="bold")
        provider = self._provider_label(data.get("provider") or "")
        self._console.print(f"  Provider:         {provider}")
        self._console.print(f"  Business Type:    {data.get('business_type') or '-'}")
        self._console.print(f"  Location:         {data.get('location') or '-'}")
        self._console.print(f"  Maximum Results:  {data.get('max_results') or 0}")
        self._console.print(f"  Website Crawling: {'Yes' if data.get('needs_crawl') else 'No'}")
        self._console.print(f"  Export:           {'Yes' if data.get('export') else 'No'}")
        estimated = data.get("estimated_runtime") or _ESTIMATED_RUNTIME
        self._console.print(f"  Estimated Runtime: {estimated}")

    def _on_planning_failed(self, event: ExecutionEvent) -> None:
        self._console.print()
        self._console.print("⚠️ Planning Failed", style="bold red")
        self._console.print(f"  Reason: {event.data.get('reason') or event.message}")

    def _on_llm_model_selected(self, event: ExecutionEvent) -> None:
        data = event.data
        reason = data.get("reason") or ""
        line = f"🤖 Trying model: {data.get('model') or '-'}"
        if reason:
            line += f" ({reason})"
        self._console.print(line)

    def _on_selecting_provider(self, event: ExecutionEvent) -> None:
        self._console.print(f"Selecting Provider: {event.data.get('provider') or '-'}")

    def _on_launching_browser(self, _event: ExecutionEvent) -> None:
        self._console.print("Launching Browser...")

    def _on_phase(self, event: ExecutionEvent) -> None:
        self._console.print(f"{event.data.get('phase') or ''}...")

    # -- Tool lifecycle -----------------------------------------------------

    def _on_tool_started(self, event: ExecutionEvent) -> None:
        data = event.data
        step = data.get("step")
        total = data.get("total")
        self._console.print()
        header = f"🔧 Tool Execution [{step}/{total}]" if step and total else "🔧 Tool Execution"
        self._console.print(header, style="bold")
        self._console.print(f"Running {data.get('display') or '-'}...")

    def _on_tool_succeeded(self, event: ExecutionEvent) -> None:
        data = event.data
        detail = data.get("detail") or ""
        line = f"✓ {data.get('display') or '-'} completed"
        if detail:
            line += f": {detail}"
        self._console.print(line, style="bold green")

    def _on_tool_failed(self, event: ExecutionEvent) -> None:
        data = event.data
        reason = data.get("reason") or "Unknown error"
        self._console.print(
            f"✗ {data.get('display') or '-'} failed Reason: {reason}", style="bold red"
        )

    # -- Per-business progress ----------------------------------------------

    def _on_business_started(self, event: ExecutionEvent) -> None:
        data = event.data
        tool = data.get("tool") or ""
        if tool == "business_details":
            self._console.print(f"Opening Business: {data.get('business') or '-'}")
        else:
            self._console.print(f"{business_action(tool)}: {data.get('business') or '-'}")

    def _on_business_done(self, event: ExecutionEvent) -> None:
        data = event.data
        tool = data.get("tool") or ""
        verb = {
            "business_details": "Details extracted",
            "website_crawler": "Website crawled",
            "email_extractor": "Email extracted",
            "phone_extractor": "Phone extracted",
        }.get(tool, "Processed")
        line = f"✓ {verb} for {data.get('business') or '-'}"
        self._console.print(line, style="bold green")

    def _on_progress(self, event: ExecutionEvent) -> None:
        data = event.data
        self._console.print(
            f"📈 Progress: Businesses Processed {data.get('processed')}/{data.get('total')}"
        )

    # -- Error reporting and recovery ---------------------------------------

    def _on_error(self, event: ExecutionEvent) -> None:
        data = event.data
        self._console.print()
        self._console.print("⚠️ Error Encountered", style="bold red")
        self._console.print(f"  Current Step: {data.get('step') or '-'}")
        self._console.print(f"  Status: {data.get('status') or 'FAILED'}")
        self._console.print(f"  Reason: {data.get('reason') or '-'}")
        self._error_active = True

    def _on_retrying(self, event: ExecutionEvent) -> None:
        data = event.data
        prefix = "  " if self._error_active else ""
        self._console.print(
            f"{prefix}Recovery: Retrying... Attempt {data.get('attempt')}/{data.get('maximum')}"
        )

    def _on_recovered(self, _event: ExecutionEvent) -> None:
        prefix = "  " if self._error_active else ""
        self._console.print(f"{prefix}Recovered Successfully", style="bold green")
        self._error_active = False

    # -- Metrics and finalization -------------------------------------------

    def _on_timing(self, event: ExecutionEvent) -> None:
        data = event.data
        self._timings[data.get("label", "")] = data.get("seconds", 0.0)

    def _on_history(self, event: ExecutionEvent) -> None:
        entry = event.data.get("entry")
        self._history.append(dict(entry) if entry else dict(event.data))

    def _on_summary(self, event: ExecutionEvent) -> None:
        self._summary = dict(event.data)

    def _on_finished(self, event: ExecutionEvent) -> None:
        data = event.data
        result = data.get("result")
        if self._summary:
            result = self._summary.get("result") or result
        self._render_timing()
        self._render_history()
        self._render_summary(result)

    # -- Final blocks -------------------------------------------------------

    def _render_timing(self) -> None:
        if not self._timings:
            return
        self._console.print()
        self._console.print("⏱️ Timing:", style="bold")
        for label in _TIMING_ORDER:
            seconds = self._timings.get(label)
            if seconds is None:
                continue
            self._console.print(f"  {_TIMING_LABELS.get(label, label)}: {seconds:.1f} seconds")
        for label in sorted(self._timings):
            if label in _TIMING_ORDER:
                continue
            self._console.print(f"  {label}: {self._timings[label]:.1f} seconds")

    def _render_history(self) -> None:
        if not self._history:
            return
        self._console.print()
        self._console.print("📋 Execution History:", style="bold")
        for entry in self._history:
            icon = "✓" if entry.get("status") == "success" else "✗"
            display = entry.get("display") or entry.get("tool") or "-"
            detail = entry.get("detail") or ""
            seconds = entry.get("seconds")
            line = f"  [{icon}] {display}"
            if detail:
                line += f" — {detail}"
            if seconds is not None:
                line += f" ({seconds:.1f}s)"
            self._console.print(line)

    def _render_summary(self, result: Any) -> None:
        if result is None:
            return
        lines = ExecutionSummary().to_lines(result)
        for line in lines:
            self._console.print(line)
        stats = self._summary
        if stats.get("successful_leads") is not None:
            self._console.print(f"Successful Leads: {stats['successful_leads']}")
        if stats.get("missing_emails") is not None:
            self._console.print(f"Missing Emails: {stats['missing_emails']}")
        if stats.get("missing_websites") is not None:
            self._console.print(f"Missing Websites: {stats['missing_websites']}")

    @staticmethod
    def _provider_label(provider: str) -> str:
        return _PROVIDER_LABELS.get(provider, provider or "-")
