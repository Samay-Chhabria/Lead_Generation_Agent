"""End-to-end application pipeline.

ApplicationPipeline connects every module of the application into one complete
workflow: it parses a natural-language prompt into a SearchPlan, runs the
selected provider through the SearchPipeline (search, business detail
extraction, and website email discovery), processes the collected leads,
exports them to an .xlsx workbook, and prints an execution summary
(Requirement 1, 11, 12).

A failure in one stage never discards data already collected by earlier
stages: provider or export failures are logged and surfaced through a
non-successful ExecutionResult instead of being re-raised.
"""

import logging
import time

from rich.console import Console

from app.config.logging_config import get_logger
from app.config.settings import Settings
from app.exceptions.export_exception import ExportException
from app.exceptions.parser_exception import ParserException
from app.exceptions.provider_exception import ProviderException
from app.models.execution_result import ExecutionResult
from app.models.search_plan import SearchPlan
from app.parser.prompt_parser import PromptParser
from app.pipeline.search_pipeline import SearchPipeline
from app.processing.processing_pipeline import ProcessingPipeline
from app.providers.provider_factory import ProviderFactory
from app.utils.execution_summary import ExecutionSummary

_console = Console()


class ApplicationPipeline:
    """Coordinate the full lead generation workflow for a single prompt."""

    def __init__(
        self,
        settings: Settings,
        logger: logging.Logger | None = None,
        factory: ProviderFactory | None = None,
        processing: ProcessingPipeline | None = None,
        summary: ExecutionSummary | None = None,
    ) -> None:
        """Initialize the pipeline with its collaborators.

        Args:
            settings: Application configuration.
            logger: Optional logger; a package logger is used when omitted.
            factory: Optional provider factory; one is created from the
                settings when omitted.
            processing: Optional processing pipeline; the SearchPipeline
                creates a default one when omitted.
            summary: Optional execution summary renderer.
        """
        self._settings = settings
        self._logger = logger or get_logger("application")
        self._parser = PromptParser()
        self._factory = factory
        self._processing = processing
        self._summary = summary or ExecutionSummary()

    def execute(self, prompt: str) -> ExecutionResult:
        """Run the complete workflow for a prompt and return its outcome.

        Args:
            prompt: The natural-language prompt supplied by the user.

        Returns:
            An ExecutionResult describing what was collected, processed,
            exported, and whether the run completed successfully.
        """
        started = time.perf_counter()
        self._logger.info("Pipeline started.")
        plan = self._parse(prompt)
        if plan is None:
            result = ExecutionResult(
                search_query=prompt,
                execution_time=self._elapsed(started),
                success=False,
            )
            self._finish(result)
            return result
        self._logger.info("Parsed search plan: %s", plan)
        self._print_plan(plan)

        try:
            pipeline = self._build_pipeline()
            provider_result, processing_result, path = pipeline.run_and_export(plan)
        except (ProviderException, ExportException) as exc:
            self._logger.exception("Pipeline failed: %s", exc)
            result = ExecutionResult(
                search_query=plan.original_prompt,
                business_type=plan.business_type,
                location=plan.location,
                provider=plan.provider,
                requested_leads=plan.max_results,
                execution_time=self._elapsed(started),
                success=False,
            )
            self._finish(result)
            return result

        result = ExecutionResult(
            search_query=plan.original_prompt,
            business_type=plan.business_type,
            location=plan.location,
            provider=plan.provider,
            requested_leads=plan.max_results,
            collected_leads=provider_result.lead_count,
            processed_leads=processing_result.final_count,
            duplicates_removed=processing_result.duplicates_removed,
            excel_output_path=path,
            execution_time=self._elapsed(started),
            success=True,
        )
        self._finish(result)
        return result

    def _parse(self, prompt: str) -> SearchPlan | None:
        """Parse a prompt into a plan, returning None when it is invalid."""
        try:
            return self._parser.parse(prompt, settings=self._settings)
        except ParserException as exc:
            self._logger.error("Failed to parse prompt: %s", exc)
            return None

    def _build_pipeline(self) -> SearchPipeline:
        factory = self._factory or ProviderFactory(settings=self._settings, logger=self._logger)
        self._logger.info("Browser started.")
        self._logger.info("Provider initialized.")
        return SearchPipeline(factory=factory, logger=self._logger, processing=self._processing)

    def _print_plan(self, plan: SearchPlan) -> None:
        _console.print()
        _console.print("Search Plan", style="bold")
        _console.print("=" * 40)
        _console.print(f"Original Prompt: {plan.original_prompt}")
        _console.print(f"Business Type: {plan.business_type}")
        _console.print(f"Location: {plan.location}")
        _console.print(f"Provider: {plan.provider}")
        _console.print(f"Maximum Leads: {plan.max_results}")

    def _finish(self, result: ExecutionResult) -> None:
        self._logger.info("Summary generated.")
        self._summary.print(result)
        self._logger.info("Pipeline finished.")

    @staticmethod
    def _elapsed(started: float) -> float:
        return time.perf_counter() - started
