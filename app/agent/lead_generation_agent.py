"""Lead Generation Agent facade.

Acts as the console-facing orchestrator of the application. It shows the
ready banner, reads the natural-language prompt from the console when none is
supplied, and hands the whole workflow to the ApplicationPipeline, which runs
every module end to end and prints the execution summary. The agent never
contains extraction or browser logic: it only coordinates and presents.
"""

import logging

from rich.console import Console

from app.config.constants import APP_NAME, APP_VERSION
from app.config.logging_config import get_logger
from app.config.settings import Settings, get_settings
from app.models.execution_result import ExecutionResult
from app.pipeline.application_pipeline import ApplicationPipeline
from app.providers.provider_factory import ProviderFactory

_console = Console()


class LeadGenerationAgent:
    """Orchestrates the lead generation pipeline."""

    def __init__(
        self,
        settings: Settings | None = None,
        logger: logging.Logger | None = None,
        factory: ProviderFactory | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._logger = logger or get_logger()
        self._factory = factory

    def run(self, prompt: str | None = None) -> ExecutionResult:
        """Run the full workflow for a prompt and return its outcome.

        Args:
            prompt: The natural-language prompt. When omitted, the prompt is
                read from the console.

        Returns:
            An ExecutionResult describing the completed run.
        """
        self._logger.info("Lead Generation Agent Ready.")
        _console.print(f"{APP_NAME} v{APP_VERSION} is ready to use.", style="bold green")
        if prompt is None:
            prompt = input("Please enter your search: ")

        pipeline = ApplicationPipeline(
            settings=self._settings,
            logger=self._logger,
            factory=self._factory,
        )
        result = pipeline.execute(prompt)
        if result.success:
            _console.print("Search completed successfully.", style="bold green")
        _console.print("Application finished.", style="bold green")
        return result
