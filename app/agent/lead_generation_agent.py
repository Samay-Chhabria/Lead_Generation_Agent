"""Lead Generation Agent facade.

Console-facing orchestrator built on the Agent -> Planner -> Tools pattern. It
shows the ready banner, reads the natural-language prompt when none is
supplied, and hands the task to the Planner (intent analysis and step
selection), then runs the resulting plan through the AgentExecutor against the
shared tool registry. The agent never contains extraction or browser logic: it
only coordinates and presents.

The Agent -> Planner -> Tools chain:

1. The user gives a natural-language task, e.g. "Find dentists near Clifton
   Karachi with emails." — no hand-written query needed.
2. The Planner parses the intent (business type, location, wanted data) and
   builds an ordered plan of tool calls, optionally consulting the configured
   LLM for tool selection.
3. The executor runs each tool (search, details, crawl, extract, export) in
   order, logging its internal reasoning, and folds the results into a final
   ExecutionResult.

The agent reports every stage of a run through the AgentExecutionLogger. The
terminal timeline subscriber is attached for the run (unless ``console=False``,
as the GUI requests) and detached afterwards, so presentation never leaks into
the agent's own logic.
"""

from __future__ import annotations

import logging
from typing import Any

from app.agent.executor import AgentExecutor
from app.agent.planner import Planner, TaskPlan
from app.agent.tool_manager import ToolManager
from app.browser.browser_manager import BrowserManager
from app.config.logging_config import get_logger
from app.config.settings import Settings, get_settings
from app.exceptions.llm_exception import PlanningError
from app.execution.execution_logger import get_execution_logger
from app.execution.terminal_renderer import TerminalRenderer
from app.llm.base import LLMProvider
from app.llm.factory import create_llm_provider
from app.models.execution_plan import ExecutionPlan
from app.models.execution_result import ExecutionResult
from app.providers.provider_factory import ProviderFactory
from app.tools.base import ToolContext
from app.tools.registry import ToolRegistry, build_default_registry
from app.utils.execution_summary import ExecutionSummary

_ESTIMATED_RUNTIME = "30-60 seconds"


class LeadGenerationAgent:
    """Orchestrates the Agent -> Planner -> Tools lead generation flow."""

    def __init__(
        self,
        settings: Settings | None = None,
        logger: logging.Logger | None = None,
        factory: ProviderFactory | None = None,
        planner: Planner | None = None,
        llm: LLMProvider | None = None,
        registry: ToolRegistry | None = None,
        executor: AgentExecutor | None = None,
        summary: ExecutionSummary | None = None,
        tool_manager: Any = None,
    ) -> None:
        """Initialize the agent and its collaborators.

        Args:
            settings: Application configuration.
            logger: Optional logger; the package logger is used when omitted.
            factory: Optional provider factory whose browser is shared with the
                tools. When omitted, the agent owns its own browser manager.
            planner: Optional Planner; a default is created when omitted.
            llm: Optional LLM provider; the configured provider is created from
                settings when omitted. Missing API keys fall back to offline
                (deterministic) planning instead of crashing.
            registry: Optional tool registry; a default registry with all
                built-in tools is created when omitted.
            executor: Optional executor; a default is created when omitted.
            summary: Optional execution summary renderer.
            tool_manager: Optional ToolManager; one is created over the tool
                registry when omitted.
        """
        self._settings = settings or get_settings()
        self._logger = logger or get_logger()
        self._factory = factory
        self._planner = planner or Planner(settings=self._settings, logger=self._logger)
        self._llm = self._resolve_llm(llm)
        self._summary = summary or ExecutionSummary()

        browser = (
            factory.browser
            if factory is not None
            else BrowserManager(settings=self._settings, logger=self._logger)
        )
        self._browser = browser
        context = ToolContext(browser=browser, settings=self._settings, logger=self._logger)
        self._registry = registry or build_default_registry(context, factory=factory)
        self._tool_manager = tool_manager or ToolManager(
            registry=self._registry, context=context, logger=self._logger
        )
        self._executor = executor or AgentExecutor(
            registry=self._registry,
            context=context,
            settings=self._settings,
            logger=self._logger,
            manager=self._tool_manager,
        )

    def _resolve_llm(self, llm: LLMProvider | None) -> LLMProvider | None:
        """Return the LLM provider, falling back to offline planning."""
        if llm is not None:
            return llm
        try:
            return create_llm_provider(self._settings)
        except Exception as exc:
            self._logger.warning(
                "LLM provider unavailable (%s); using deterministic planning.", exc
            )
            return None

    def run(
        self,
        prompt: str | None = None,
        plan: TaskPlan | None = None,
        console: bool = True,
    ) -> ExecutionResult:
        """Run the full agent flow for a prompt and return its outcome.

        Args:
            prompt: The natural-language task. When omitted, the prompt is read
                from the console.
            plan: Optional precomputed plan; when omitted, the planner is used.
                Passing a plan avoids planning twice when the caller already
                showed the plan to the user (e.g. the GUI).
            console: When True, the terminal timeline renderer is attached for
                the duration of the run. Presentation layers that render their
                own view (the GUI) pass False.

        Returns:
            An ExecutionResult describing the completed run.
        """
        exec_log = get_execution_logger()
        exec_log.clear()
        renderer = TerminalRenderer() if console else None
        if renderer is not None:
            exec_log.subscribe(renderer.on_event)
        try:
            self._logger.info("Lead Generation Agent Ready.")
            if prompt is None:
                prompt = input("Please enter your search: ")
            prompt = " ".join(str(prompt or "").split())
            exec_log.agent_started(prompt)

            try:
                plan = plan or self._planner.plan(prompt, llm=self._llm, registry=self._registry)
            except PlanningError as exc:
                self._logger.error("Planning failed: %s", exc)
                exec_log.planning_failed(str(exc))
                result = ExecutionResult(search_query=prompt, success=False)
                self._finish(result, exec_log)
                return result

            self._logger.info("Parsed search plan: %s", plan)
            self._emit_planning(exec_log, plan)

            try:
                result = self._executor.run(prompt, plan)
            except Exception as exc:
                self._logger.exception("Agent run failed: %s", exc)
                result = ExecutionResult(
                    search_query=plan.intent.original,
                    business_type=plan.intent.business_type,
                    location=plan.intent.location,
                    provider=self._settings.search_provider,
                    execution_time=0.0,
                    success=False,
                )
            finally:
                self._close_browser()

            self._finish(result, exec_log)
            return result
        finally:
            if renderer is not None:
                exec_log.unsubscribe(renderer.on_event)

    def plan(self, prompt: str) -> TaskPlan | None:
        """Produce the execution plan for a prompt, or None when unplannable.

        The plan is exposed separately so presentation layers (the GUI) can
        show it before a run starts. Calling ``run`` afterwards with this plan
        avoids planning twice.

        Args:
            prompt: The natural-language task.

        Returns:
            The TaskPlan, or None when the prompt cannot be planned.
        """
        try:
            return self._planner.plan(prompt, llm=self._llm, registry=self._registry)
        except PlanningError as exc:
            self._logger.error("Planning failed: %s", exc)
            return None

    def to_execution_plan(self, plan: TaskPlan) -> ExecutionPlan:
        """Convert a TaskPlan into the displayable ExecutionPlan.

        Args:
            plan: The executable plan produced by the planner.

        Returns:
            The ExecutionPlan the GUI renders.
        """
        return self._planner.to_execution_plan(plan)

    def _emit_planning(self, exec_log: Any, plan: TaskPlan) -> None:
        """Publish the planning and visualization events for a plan."""
        intent = plan.intent
        steps = [{"tool": step.tool, "description": step.description} for step in plan.steps]
        needs_crawl = (
            intent.wants_emails or intent.wants_websites or "website_crawler" in plan.tool_sequence
        )
        exec_log.understanding(
            intent.business_type,
            intent.location,
            wants_emails=intent.wants_emails,
            wants_websites=intent.wants_websites,
            wants_phones=intent.wants_phones,
            min_rating=intent.min_rating,
        )
        exec_log.planning(
            goal=f"Find {intent.business_type} in {intent.location} and export their leads.",
            steps=steps,
            expected_leads=self._settings.max_leads,
            provider=self._settings.search_provider,
            business_type=intent.business_type,
            location=intent.location,
            max_results=self._settings.max_leads,
            needs_crawl=needs_crawl,
            export=True,
            estimated_runtime=_ESTIMATED_RUNTIME,
        )

    def _finish(self, result: ExecutionResult, exec_log: Any) -> None:
        """Publish the end of the run for the timeline subscribers."""
        self._logger.info("Summary generated.")
        exec_log.finished(result)
        self._logger.info("Pipeline finished.")

    def _close_browser(self) -> None:
        """Close the shared browser after the run (matches legacy behaviour)."""
        try:
            self._browser.close()
        except Exception as exc:  # pragma: no cover - defensive
            self._logger.warning("Failed to close browser: %s", exc)
