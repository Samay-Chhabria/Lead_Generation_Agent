"""Agent executor: runs a plan step by step through the tool registry.

The executor implements the Agent loop: for every planned step it records the
internal reasoning, invokes the tool through the registry, folds the result
into the shared state, and moves on. Failed tools are logged and skipped so one
bad step never kills the run. After the loop the collected leads are filtered
by the requested minimum rating, cleaned through the processing pipeline, and
exported — the export path drives the final ExecutionResult.
"""

from __future__ import annotations

import logging
import time
from dataclasses import replace
from typing import Any

from app.agent.memory import AgentMemory
from app.agent.planner import TaskPlan
from app.agent.state import AgentState
from app.config.logging_config import get_logger
from app.config.settings import Settings, get_settings
from app.exceptions.tool_exception import UnknownToolError
from app.execution.execution_logger import get_execution_logger
from app.models.execution_result import ExecutionResult
from app.models.lead import Lead
from app.processing.processing_pipeline import ProcessingPipeline
from app.tools.base import ToolContext
from app.tools.business_details_tool import BusinessDetailsTool
from app.tools.registry import ToolRegistry

_PAYLOAD_ARGUMENTS = {
    "business_details": ("references", "leads"),
    "website_crawler": ("leads",),
    "email_extractor": ("leads",),
    "phone_extractor": ("leads",),
}

# Agent-facing aliases map onto the canonical pipeline tools so their results
# fold into the shared state exactly like the tools they wrap.
_WRAPPER_TO_TOOL = {
    "search": "google_maps_search",
    "business_collection": "google_maps_search",
    "business_extraction": "business_details",
    "export": "lead_exporter",
}


class AgentExecutor:
    """Execute a TaskPlan against a ToolRegistry and produce a result."""

    def __init__(
        self,
        registry: ToolRegistry,
        context: ToolContext | None = None,
        processing: ProcessingPipeline | None = None,
        memory: AgentMemory | None = None,
        settings: Settings | None = None,
        logger: logging.Logger | None = None,
        manager: Any = None,
    ) -> None:
        self._registry = registry
        self._manager = manager
        self._context = context or ToolContext(logger=logger)
        self._settings = settings or self._context.settings or get_settings()
        self._processing = processing or ProcessingPipeline(logger=logger)
        self._logger = logger or get_logger("agent.executor")
        self._memory = memory or AgentMemory(logger=self._logger)

    def run(self, task: str, plan: TaskPlan) -> ExecutionResult:
        """Execute every step of the plan and return the run summary."""
        started = time.perf_counter()
        exec_log = get_execution_logger()
        self._memory.begin(task)
        self._logger.info("Starting agent loop for %d planned steps.", len(plan.steps))

        state = AgentState(task=task, steps=plan.steps)
        executed = 0
        tool_total = len(plan.steps)
        while not state.is_finished:
            step = state.next_step()
            if step is None:
                break
            if step.tool == "lead_exporter":
                exec_log.phase(
                    "Saving Excel",
                    message=(
                        "Export step deferred: the final lead export runs after "
                        "processing during finalization."
                    ),
                )
                self._logger.info(
                    "Export step deferred: the final lead export runs after "
                    "processing during finalization."
                )
                state.mark_current_done()
                continue
            self._log_reasoning(step)
            tool = self._resolve(step.tool)
            if tool is None:
                self._logger.warning("Skipping step '%s': tool not registered.", step.tool)
                state.mark_current_done()
                continue
            args = self._build_arguments(step, state)
            executed += 1
            exec_log.tool_started(
                step.tool, step=executed, total=tool_total, description=step.description
            )
            self._logger.info("Executing tool: %s", step.tool)
            tool_started_at = time.perf_counter()
            if self._manager is not None:
                result = self._manager.execute(step.tool, **args)
            else:
                result = tool.run(**args)
            elapsed = time.perf_counter() - tool_started_at
            state.mark_current_done()
            summary = self._summarize(step.tool, result)
            self._memory.record_tool(step.tool, result.success, summary)
            if not result.success:
                exec_log.tool_failed(step.tool, result.error, seconds=elapsed)
                self._logger.warning("Tool '%s' failed: %s", step.tool, result.error)
                if step.tool == "google_maps_search":
                    self._logger.error("Pipeline failed: %s", result.error)
                    return self._failed_result(task, plan, started)
                self._logger.info("Planning next action...")
                continue
            exec_log.tool_succeeded(step.tool, summary, seconds=elapsed)
            self._merge_result(step.tool, result, state)
            self._logger.info("Tool finished: %s", step.tool)
            self._logger.info("Planning next action...")

        return self._finalize(task, plan, state, started)

    def _failed_result(self, task: str, plan: TaskPlan, started: float) -> ExecutionResult:
        """Build a failed ExecutionResult, matching the legacy run semantics."""
        self._logger.info("Pipeline finished.")
        result = ExecutionResult(
            search_query=task,
            business_type=plan.intent.business_type,
            location=plan.intent.location,
            provider=self._settings.search_provider,
            execution_time=time.perf_counter() - started,
            success=False,
        )
        exec_log = get_execution_logger()
        exec_log.timing("total", result.execution_time)
        exec_log.summary(result)
        return result

    def _resolve(self, name: str) -> Any:
        """Return the tool for a step name, or None when unregistered."""
        try:
            return self._registry.get(name)
        except UnknownToolError as exc:
            self._logger.warning("%s", exc)
            return None

    def _build_arguments(self, step: Any, state: AgentState) -> dict[str, Any]:
        """Merge static step arguments with live state payload data."""
        args = dict(step.arguments)
        if step.tool == "pipeline" and "prompt" not in args:
            args["prompt"] = state.task
        canonical = _WRAPPER_TO_TOOL.get(step.tool, step.tool)
        for key in _PAYLOAD_ARGUMENTS.get(canonical, ()):
            if key in state.payload:
                args[key] = state.payload[key]
        return args

    def _merge_result(self, tool_name: str, result: Any, state: AgentState) -> None:
        """Fold a tool result into the shared execution state."""
        tool_name = _WRAPPER_TO_TOOL.get(tool_name, tool_name)
        data = result.data or {}
        if tool_name == "google_maps_search":
            state.payload["leads"] = list(data.get("leads") or [])
            state.payload["references"] = list(data.get("references") or [])
            state.payload["provider"] = data.get("provider") or self._settings.search_provider
            state.payload["query"] = data.get("query") or state.task
            state.payload["business_links"] = list(data.get("business_links") or [])
            details = data.get("details") or []
            if details:
                state.payload["details"] = list(details)
            return
        if tool_name == "business_details":
            incoming = list(data.get("leads") or [])
            state.payload["leads"] = self._merge_leads(state.payload.get("leads", []), incoming)
            details = state.payload.get("details", [])
            details.extend(data.get("details") or [])
            state.payload["details"] = details
            return
        if tool_name in ("website_crawler", "email_extractor", "phone_extractor"):
            incoming = list(data.get("leads") or [])
            state.payload["leads"] = self._merge_leads(state.payload.get("leads", []), incoming)
            return
        if tool_name == "lead_exporter":
            state.payload["export_path"] = data.get("path")
            state.payload["exported_count"] = data.get("exported_count", 0)
        if tool_name == "pipeline":
            state.payload["provider"] = data.get("provider") or self._settings.search_provider
            state.payload["query"] = data.get("plan") or state.task
            state.payload["leads"] = list(data.get("leads") or [])
            state.payload["export_path"] = data.get("path")
            metrics = data.get("metrics") or {}
            state.payload["collected_leads"] = metrics.get("collected_leads", 0)
            state.payload["processed_leads"] = metrics.get("processed_leads", 0)
            state.payload["duplicates_removed"] = metrics.get("duplicates_removed", 0)
        if tool_name == "summary":
            state.payload["summary"] = data.get("summary") or ""

    @staticmethod
    def _merge_leads(base: list[Lead], incoming: list[Lead]) -> list[Lead]:
        """Overlay incoming leads onto the base list by business name."""
        merged = {lead.business_name: lead for lead in base}
        for lead in incoming:
            if lead.business_name:
                merged[lead.business_name] = lead
        return list(merged.values())

    def _filter_by_rating(
        self, leads: list[Lead], details: list[dict[str, str]], minimum: float
    ) -> list[Lead]:
        """Keep only leads whose rating meets the requested minimum."""
        filtered: list[Lead] = []
        for lead in leads:
            rating = BusinessDetailsTool.rating_of(details, lead.business_name)
            if rating is None:
                self._logger.info("Dropping '%s': no rating found.", lead.business_name)
                continue
            if rating < minimum:
                self._logger.info(
                    "Dropping '%s': rating %.1f below %.1f.",
                    lead.business_name,
                    rating,
                    minimum,
                )
                continue
            filtered.append(lead)
        return filtered

    def _finalize(
        self, task: str, plan: TaskPlan, state: AgentState, started: float
    ) -> ExecutionResult:
        """Process, export, and summarize the run."""
        exec_log = get_execution_logger()
        intent = plan.intent
        leads = list(state.payload.get("leads", []))
        collected = len(leads)
        pipeline_completed = state.payload.get("export_path") is not None

        if intent.min_rating is not None and state.payload.get("details"):
            leads = self._filter_by_rating(
                leads, state.payload.get("details", []), intent.min_rating
            )

        processed = self._processing.process(leads)

        if pipeline_completed:
            path = state.payload.get("export_path")
            processed_leads = int(state.payload.get("processed_leads") or processed.final_count)
            duplicates_removed = int(
                state.payload.get("duplicates_removed") or processed.duplicates_removed
            )
            self._memory.record_tool("pipeline", True, f"wrote {processed_leads} leads to {path}")
            exec_log.tool_succeeded("lead_exporter", f"wrote {processed_leads} leads to {path}")
        else:
            exec_log.tool_started(
                "lead_exporter",
                step=len(plan.steps),
                total=len(plan.steps),
                description="Export the collected leads to an Excel workbook.",
            )
            export_args = {
                "leads": processed.leads,
                "business_type": intent.business_type,
                "location": intent.location,
            }
            exporter = self._registry.get("lead_exporter")
            export_started = time.perf_counter()
            export_result = exporter.run(**export_args)
            export_elapsed = time.perf_counter() - export_started
            exec_log.timing("export", export_elapsed)
            path = None
            processed_leads = 0
            duplicates_removed = processed.duplicates_removed
            if export_result.success:
                path = export_result.data.get("path")
                processed_leads = processed.final_count
                exec_log.tool_succeeded(
                    "lead_exporter",
                    f"wrote {export_result.data.get('exported_count', 0)} leads to {path}",
                    seconds=export_elapsed,
                )
                self._memory.record_tool(
                    "lead_exporter",
                    True,
                    f"wrote {export_result.data.get('exported_count', 0)} leads to {path}",
                )
            else:
                exec_log.tool_failed("lead_exporter", export_result.error, seconds=export_elapsed)
                self._logger.warning("Export failed: %s", export_result.error)
                self._memory.record_tool("lead_exporter", False, export_result.error)

        execution_time = time.perf_counter() - started
        result = ExecutionResult(
            search_query=(
                state.payload.get("query") or f"{intent.business_type} in {intent.location}"
            ),
            business_type=intent.business_type,
            location=intent.location,
            provider=state.payload.get("provider") or self._settings.search_provider,
            requested_leads=self._settings.max_leads,
            collected_leads=collected,
            processed_leads=processed_leads,
            duplicates_removed=duplicates_removed,
            excel_output_path=path,
            execution_time=execution_time,
            success=path is not None,
        )
        result = replace(result, summary=self._generate_summary(result, processed.leads))
        exec_log.timing("total", execution_time)
        exec_log.summary(
            result,
            successful_leads=processed_leads,
            missing_emails=sum(1 for lead in processed.leads if not lead.has_email()),
            missing_websites=sum(1 for lead in processed.leads if not lead.has_website()),
        )
        self._logger.info(
            "Agent run finished: %d collected, %d processed, exported=%s.",
            result.collected_leads,
            result.processed_leads,
            path,
        )
        return result

    def _generate_summary(self, result: ExecutionResult, leads: list[Lead]) -> str:
        """Produce the final human-readable summary via the SummaryTool."""
        try:
            summary_tool = self._registry.get("summary")
            outcome = summary_tool.run(result=result, leads=leads)
        except Exception as exc:  # pragma: no cover - defensive
            self._logger.warning("Summary generation failed: %s", exc)
            return ""
        return (outcome.data or {}).get("summary") or ""

    def _log_reasoning(self, step: Any) -> None:
        """Log the internal chain-of-thought for a step (debug level)."""
        self._logger.info(
            "Reasoning: %s",
            step.reason or f"Executing {step.tool} for the current task.",
        )
        self._logger.debug(
            "Step %s | args=%s | completed=%s",
            step.tool,
            {k: v for k, v in step.arguments.items() if k not in ("leads", "references")},
            self._memory.completed_tools,
        )

    @staticmethod
    def _summarize(tool_name: str, result: Any) -> str:
        """Build a short summary string from a tool result."""
        data = result.data or {}
        if tool_name in ("google_maps_search", "search", "business_collection"):
            return f"collected {len(data.get('leads') or [])} leads"
        if tool_name in ("lead_exporter", "export"):
            return f"wrote {data.get('exported_count', 0)} leads to {data.get('path')}"
        if tool_name in ("business_details", "business_extraction"):
            return f"extracted {len(data.get('leads') or [])} businesses"
        if tool_name in ("website_crawler", "email_extractor"):
            return f"found {data.get('emails_found', 0)} emails"
        if tool_name == "phone_extractor":
            return f"found {data.get('phones_found', 0)} phones"
        if tool_name == "summary":
            return f"summary: {data.get('summary', '')[:60]}"
        if tool_name == "pipeline":
            return (
                f"pipeline: {data.get('metrics', {}).get('processed_leads', 0)} "
                f"leads exported to {data.get('path')}"
            )
        if tool_name == "navigation":
            return f"navigated to {data.get('url', '')}"
        return "completed"
