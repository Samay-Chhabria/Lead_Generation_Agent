"""Live log stream widget.

Renders every AgentExecutionLogger event as a timestamped line, coloured by
its nature (success green, failure red, progress muted). The panel never reads
the backend itself — it only consumes the events the controller forwards.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QTextEdit, QWidget

from app.execution.execution_logger import (
    EVENT_AGENT_STARTED,
    EVENT_BUSINESS_DONE,
    EVENT_BUSINESS_STARTED,
    EVENT_ERROR,
    EVENT_FINISHED,
    EVENT_HISTORY,
    EVENT_LAUNCHING_BROWSER,
    EVENT_PHASE,
    EVENT_PLANNING,
    EVENT_PLANNING_FAILED,
    EVENT_PROGRESS,
    EVENT_RECOVERED,
    EVENT_RETRYING,
    EVENT_SELECTING_PROVIDER,
    EVENT_SUMMARY,
    EVENT_TIMING,
    EVENT_TOOL_FAILED,
    EVENT_TOOL_STARTED,
    EVENT_TOOL_SUCCEEDED,
    EVENT_UNDERSTANDING,
    ExecutionEvent,
)
from app.gui.themes.theme import Theme
from app.gui.widgets.cards import Panel

_VERBS = {
    "business_details": "Details extracted",
    "website_crawler": "Website crawled",
    "email_extractor": "Email extracted",
    "phone_extractor": "Phone extracted",
}


class LiveLogsPanel(Panel):
    """Continuously streaming, colour-coded, terminal-style execution log."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Live Logs", icon="💬", parent=parent)
        self._colors = {
            "text": "#e6e9ef",
            "muted": "#8b95a6",
            "success": "#2fce7a",
            "danger": "#ff5c68",
            "warning": "#ffb454",
            "accent": "#4f8cff",
        }
        self._view = QTextEdit()
        self._view.setObjectName("logView")
        self._view.setReadOnly(True)
        self._view.document().setMaximumBlockCount(4000)
        self._view.setAcceptRichText(True)
        self._view.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.add(self._view)

    def apply_theme(self, theme: Theme) -> None:
        """Update the colour palette used for the log lines."""
        self._colors = {
            "text": theme.text,
            "muted": theme.muted,
            "success": theme.success,
            "danger": theme.danger,
            "warning": theme.warning,
            "accent": theme.accent,
        }

    def reset(self) -> None:
        """Clear the log for a new run."""
        self._view.clear()

    def append_event(self, event: ExecutionEvent) -> None:
        """Format an event and stream it as a new terminal-style line."""
        line, color = self._format(event)
        if line is None:
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        tag = self._tag_for(color)
        html = (
            f'<span style="color:{self._colors["muted"]}">[{timestamp}]</span>'
            f' <span style="color:{color};font-weight:600">{tag}</span>'
            f' <span style="color:{color}">{line}</span>'
        )
        self._view.append(html)
        self._view.moveCursor(QTextCursor.MoveOperation.End)

    def _tag_for(self, color: str) -> str:
        """Return a short level tag that matches the line's colour."""
        if color == self._colors.get("success"):
            return "OK"
        if color == self._colors.get("danger"):
            return "ERR"
        if color == self._colors.get("warning"):
            return "WRN"
        if color == self._colors.get("accent"):
            return "RUN"
        return "· "

    def _format(self, event: ExecutionEvent) -> tuple[str | None, str]:
        """Return the (text, colour) pair for an event (None skips it)."""
        kind = event.kind
        data = event.data
        c = self._colors
        if kind == EVENT_AGENT_STARTED:
            return f"🤖 {event.message}", c["text"]
        if kind == EVENT_UNDERSTANDING:
            return (
                f"🧠 Understood: {data.get('business_type') or '-'} in "
                f"{data.get('location') or '-'}",
                c["text"],
            )
        if kind == EVENT_PLANNING:
            return f"✅ Plan ready — {len(data.get('steps') or [])} steps", c["text"]
        if kind == EVENT_PLANNING_FAILED:
            return f"⚠️ Planning failed: {data.get('reason') or '-'}", c["danger"]
        if kind == EVENT_SELECTING_PROVIDER:
            return f"🔀 Selecting provider: {data.get('provider') or '-'}", c["muted"]
        if kind == EVENT_LAUNCHING_BROWSER:
            return "🌐 Launching browser...", c["muted"]
        if kind == EVENT_PHASE:
            return f"{data.get('phase') or ''}...", c["muted"]
        if kind == EVENT_TOOL_STARTED:
            return f"▶ Running {data.get('display') or '-'}...", c["accent"]
        if kind == EVENT_TOOL_SUCCEEDED:
            detail = data.get("detail") or ""
            text = f"✓ {data.get('display') or '-'} completed"
            if detail:
                text += f" — {detail}"
            return text, c["success"]
        if kind == EVENT_TOOL_FAILED:
            return (
                f"✗ {data.get('display') or '-'} failed — {data.get('reason') or '-'}",
                c["danger"],
            )
        if kind == EVENT_BUSINESS_STARTED:
            return event.message, c["muted"]
        if kind == EVENT_BUSINESS_DONE:
            verb = _VERBS.get(data.get("tool"), "Processed")
            detail = data.get("detail") or ""
            text = f"✓ {verb} for {data.get('business') or '-'}"
            if detail:
                text += f" — {detail}"
            return text, c["success"] if data.get("success", True) else c["danger"]
        if kind == EVENT_PROGRESS:
            return event.message, c["muted"]
        if kind == EVENT_ERROR:
            return (
                f"⚠️ Error at {data.get('step') or '-'}: {data.get('reason') or '-'}",
                c["danger"],
            )
        if kind == EVENT_RETRYING:
            return (
                f"🔄 Retrying {data.get('step') or '-'}... "
                f"Attempt {data.get('attempt')}/{data.get('maximum')}",
                c["warning"],
            )
        if kind == EVENT_RECOVERED:
            return f"✅ Recovered: {data.get('step') or '-'}", c["success"]
        if kind == EVENT_TIMING:
            return event.message, c["muted"]
        if kind == EVENT_HISTORY:
            return None, c["muted"]
        if kind == EVENT_SUMMARY:
            return "📊 Summary generated", c["text"]
        if kind == EVENT_FINISHED:
            status = data.get("status", "")
            icon = "🎉" if status == "SUCCESS" else "❌"
            return f"{icon} {event.message}", c["success"] if status == "SUCCESS" else c["danger"]
        return event.message, c["text"]
