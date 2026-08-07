"""Pipeline-as-a-tool wrapper.

``PipelineTool`` exposes the existing end-to-end ``SearchPipeline`` to the agent
as just another tool. When the planner or the LLM selects it, the agent runs
the complete legacy workflow — provider search, detail extraction, website
email discovery, processing, and Excel export — in one call. The tool owns its
own provider factory and browser, mirroring the standalone ``ApplicationPipeline``
behaviour, so running it never disturbs the agent's shared browser.

This is the piece that turns "the pipeline is the whole application" into
"the pipeline is one of the tools the agent can choose".
"""

from typing import Any

from app.exceptions.parser_exception import ParserException
from app.models.search_plan import SearchPlan
from app.parser.prompt_parser import PromptParser
from app.pipeline.search_pipeline import SearchPipeline
from app.providers.provider_factory import ProviderFactory
from app.tools.base import Tool, ToolContext, ToolResult


class PipelineTool(Tool):
    """Run the complete legacy search pipeline end-to-end for a prompt."""

    name = "pipeline"
    description = (
        "Run the complete legacy search pipeline for a prompt end-to-end: "
        "provider search, detail extraction, website email discovery, "
        "processing, and Excel export."
    )

    def __init__(
        self,
        context: ToolContext | None = None,
        factory: ProviderFactory | None = None,
    ) -> None:
        super().__init__(context)
        self._factory = factory

    def run(self, prompt: str = "", **kwargs: Any) -> ToolResult:
        """Run the full pipeline for a natural-language prompt.

        Args:
            prompt: The natural-language prompt, e.g. "dentists in Karachi".

        Returns:
            A ToolResult whose ``data`` holds the parsed ``plan``, the
            ``provider``, the collected ``leads``, the processing ``metrics``,
            and the exported workbook ``path``.
        """
        prompt = " ".join(str(prompt or "").split())
        if not prompt:
            return ToolResult.fail("A prompt argument is required for the pipeline tool.")
        try:
            plan: SearchPlan = PromptParser().parse(prompt, settings=self.settings)
        except ParserException as exc:
            return ToolResult.fail(str(exc))
        factory = self._factory or ProviderFactory(
            browser=self.context.browser,
            settings=self.settings,
            logger=self._logger,
        )
        pipeline = SearchPipeline(factory=factory, logger=self._logger)
        try:
            provider_result, processing_result, path = pipeline.run_and_export(plan)
        except Exception as exc:
            return ToolResult.fail(f"Pipeline failed: {exc}")
        self._logger.info(
            "Pipeline tool complete: %d collected, %d processed, exported=%s.",
            provider_result.lead_count,
            processing_result.final_count,
            path,
        )
        return ToolResult.ok(
            plan=plan.original_prompt,
            provider=plan.provider,
            business_type=plan.business_type,
            location=plan.location,
            leads=list(provider_result.leads),
            metrics={
                "collected_leads": provider_result.lead_count,
                "processed_leads": processing_result.final_count,
                "duplicates_removed": processing_result.duplicates_removed,
            },
            path=path,
        )
