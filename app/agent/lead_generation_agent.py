"""Lead Generation Agent facade.

Acts as the central orchestrator of the lead generation pipeline. In future
milestones it will coordinate the lead extractor, validator, and exporter.
For this milestone it reads a natural-language prompt, parses it into a
SearchPlan, and runs the Google Maps search provider to verify that a real
search executes. No extraction is performed.
"""

import logging

from rich.console import Console

from app.config.constants import APP_NAME, APP_VERSION
from app.config.logging_config import get_logger
from app.config.settings import Settings, get_settings
from app.models.search_plan import SearchPlan
from app.parser.prompt_parser import PromptParser
from app.pipeline.search_pipeline import SearchPipeline
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
        self._parser = PromptParser()
        self._factory = factory

    def run(self, prompt: str | None = None) -> None:
        """Parse a prompt into a search plan and run the provider pipeline.

        Args:
            prompt: The natural-language prompt. When omitted, the prompt is
                read from the console.
        """
        self._logger.info("Lead Generation Agent Ready.")
        _console.print(f"{APP_NAME} v{APP_VERSION} is ready to use.", style="bold green")
        if prompt is None:
            prompt = input("Enter a search prompt (e.g. 'coffee shops in America'): ")
        plan = self._parser.parse(prompt, settings=self._settings)
        self._logger.info("Parsed search plan: %s", plan)
        self._print_plan(plan)

        factory = self._factory or ProviderFactory(settings=self._settings, logger=self._logger)
        pipeline = SearchPipeline(factory=factory, logger=self._logger)
        result = pipeline.run(plan)

        if result.success:
            _console.print(
                f"Total {result.business_count} business references.",
                style="bold",
            )
            _console.print("Search completed successfully.", style="bold green")
        _console.print("Application finished.", style="bold green")

    def _print_plan(self, plan: SearchPlan) -> None:
        _console.print()
        _console.print("Search Plan", style="bold")
        _console.print("=" * 40)
        _console.print(f"Original Prompt: {plan.original_prompt}")
        _console.print(f"Business Type: {plan.business_type}")
        _console.print(f"Location: {plan.location}")
        _console.print(f"Provider: {plan.provider}")
        _console.print(f"Maximum Leads: {plan.max_results}")
