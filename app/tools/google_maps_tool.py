"""Google Maps search tool.

Wraps the existing ``GoogleMapsProvider`` behind the agent's Tool interface so
the provider is reused exactly as-is: the tool builds a SearchPlan, drives the
provider lifecycle, and returns the discovered leads. The provider is closed
after each run but the shared browser stays open for the other tools.
"""

import time
from typing import Any

from app.exceptions.provider_exception import (
    ProviderInitializationError,
    ProviderSearchError,
    UnknownProviderError,
)
from app.execution.execution_logger import get_execution_logger
from app.models.search_plan import SearchPlan
from app.providers.provider_factory import ProviderFactory
from app.providers.result_selection import (
    MAX_RESULT_LIMIT,
    parse_requested_limit,
)
from app.tools.base import Tool, ToolContext, ToolResult


class GoogleMapsSearchTool(Tool):
    """Search Google Maps for businesses and collect the resulting leads."""

    name = "google_maps_search"
    description = (
        "Search Google Maps for a business type in a location and return the "
        "collected business leads."
    )

    def __init__(
        self,
        context: ToolContext | None = None,
        factory: ProviderFactory | None = None,
    ) -> None:
        super().__init__(context)
        self._factory = factory
        if factory is None:
            self._factory = ProviderFactory(
                browser=self.context.browser,
                settings=self.context.settings,
                logger=self.context.logger,
            )

    def run(
        self,
        business_type: str,
        location: str,
        max_results: int = 0,
        **kwargs: Any,
    ) -> ToolResult:
        """Run the search and return the collected leads.

        Args:
            business_type: The type of business to search for, e.g. "dentists".
            location: The target location, e.g. "Clifton, Karachi".
            max_results: Optional cap on the number of leads to collect. Zero
                means use the configured default.

        Returns:
            A ToolResult whose ``data`` holds ``leads``, ``business_links``,
            ``provider``, and ``query``.
        """
        if not business_type or not str(business_type).strip():
            return ToolResult.fail("A business_type argument is required.")
        if not location or not str(location).strip():
            return ToolResult.fail("A location argument is required.")
        limit = self._resolve_limit(business_type, max_results)
        self.context.settings = _override_max_leads(self.context.settings, limit)
        plan = SearchPlan(
            original_prompt=f"{business_type} in {location}",
            business_type=str(business_type).strip(),
            location=str(location).strip(),
            provider=self.context.settings.search_provider,
            max_results=limit,
        )
        exec_log = get_execution_logger()
        exec_log.selecting_provider(plan.provider)
        provider = None
        try:
            provider = self._factory.create(plan)
            provider.initialize()
            search_started = time.perf_counter()
            business_links = provider.search()
            provider.collect_results()
            exec_log.timing("provider_search", time.perf_counter() - search_started)
            references = list(getattr(provider, "references", []) or [])
            leads = list(getattr(provider, "leads", []) or [])
            provider_name = getattr(provider, "name", None) or plan.provider
            self._logger.info(
                "Google Maps search completed: %d leads collected for '%s'.",
                len(leads),
                provider.query,
            )
            return ToolResult.ok(
                leads=leads,
                business_links=business_links,
                references=references,
                provider=provider_name,
                query=getattr(provider, "query", plan.business_type),
            )
        except (ProviderInitializationError, ProviderSearchError, UnknownProviderError) as exc:
            return ToolResult.fail(str(exc))
        except Exception as exc:  # pragma: no cover - defensive catch-all
            return ToolResult.fail(f"Google Maps search failed: {exc}")
        finally:
            if provider is not None:
                try:
                    provider.close()
                except Exception as exc:  # pragma: no cover - defensive
                    self._logger.warning("Failed to close provider: %s", exc)

    def _resolve_limit(self, business_type: str, max_results: int) -> int:
        """Resolve the effective result limit for a tool run.

        Priority: (1) an explicit count in the business type ("3 coffee
        shops"), (2) a ``max_results`` that differs from the configured default
        (an explicit caller override), and (3) the configured default capped at
        ``MAX_RESULT_LIMIT`` so nothing exceeds 10 without an explicit request.
        """
        requested = parse_requested_limit(str(business_type))
        if requested is not None:
            return requested
        configured = self.context.settings.max_leads
        if max_results and max_results != configured:
            return int(max_results)
        return min(configured, MAX_RESULT_LIMIT)


def _override_max_leads(settings: Any, max_results: int) -> Any:
    """Return settings-like object with a capped max_leads value."""
    if hasattr(settings, "max_leads"):
        try:
            from dataclasses import replace

            return replace(settings, max_leads=max_results)
        except TypeError:
            settings.max_leads = max_results
    return settings
