"""Search pipeline orchestration.

The pipeline drives one provider through its lifecycle for a given search plan
and returns a ProviderResult. It performs no searches itself: the provider is
responsible for that. The browser is only injected into the provider and is
never launched or interacted with by the pipeline. When the provider produces
leads with a website URL, the pipeline enriches them by discovering an email
address from the company's own website before the browser is released. The
pipeline guarantees that both the provider and the factory's browser are
released after every run, even when the run fails.
"""

import logging
import time
from typing import Any

from app.config.logging_config import get_logger
from app.exceptions.provider_exception import ProviderInitializationError, ProviderSearchError
from app.extractor.contact_page_crawler import ContactPageCrawler
from app.models.lead import Lead
from app.models.search_plan import SearchPlan
from app.providers.base_provider import BaseProvider
from app.providers.provider_factory import ProviderFactory
from app.providers.provider_result import ProviderResult


class SearchPipeline:
    """Runs a search plan through a provider's lifecycle."""

    def __init__(
        self,
        factory: ProviderFactory,
        logger: logging.Logger | None = None,
        crawler: ContactPageCrawler | None = None,
    ) -> None:
        self._factory = factory
        self._logger = logger or get_logger("pipeline")
        self._crawler = crawler or ContactPageCrawler(factory.settings, logger=self._logger)
        self._logger.info("Search pipeline initialized.")

    def run(self, plan: SearchPlan) -> ProviderResult:
        """Execute the provider lifecycle for a search plan.

        Args:
            plan: The plan describing what to search for.

        Returns:
            A ProviderResult summarizing the run.

        Raises:
            ProviderInitializationError: When the provider fails to initialize.
            ProviderSearchError: When the provider cannot complete the search.
            UnknownProviderError: When the plan selects an unregistered provider.
        """
        self._logger.info("Running search pipeline for provider '%s'.", plan.provider)
        provider: BaseProvider | None = None
        business_links: list[str] = []
        raw_results: list[Any] = []
        page_reference: Any = None
        started = time.perf_counter()
        try:
            provider = self._factory.create(plan)
            self._initialize(provider)
            business_links = provider.search()
            raw_results = provider.collect_results()
            references = list(getattr(provider, "references", []) or [])
            leads = list(getattr(provider, "leads", []) or [])
            page_reference = getattr(provider, "page", None)
            if leads and page_reference is not None:
                leads = self._enrich_leads(leads, page_reference)
        finally:
            try:
                if provider is not None:
                    provider.close()
            finally:
                self._factory.close()
        if provider is None:
            raise ProviderSearchError("Provider could not be created.")
        execution_time = time.perf_counter() - started
        result = ProviderResult(
            business_links=business_links,
            raw_results=raw_results,
            business_references=references,
            leads=leads,
            metadata={
                "provider": plan.provider,
                "business_type": plan.business_type,
                "location": plan.location,
            },
            execution_time=execution_time,
            success=True,
            query=provider.query,
            provider_name=provider.name or plan.provider,
            raw_page_reference=page_reference,
        )
        self._logger.info("Search pipeline completed in %.3f seconds.", execution_time)
        return result

    def _initialize(self, provider: BaseProvider) -> None:
        try:
            provider.initialize()
        except Exception as exc:
            raise ProviderInitializationError(
                f"Failed to initialize provider '{provider.plan.provider}': {exc}"
            ) from exc

    def _enrich_leads(self, leads: list[Lead], page: Any) -> list[Lead]:
        """Discover website emails for leads that have a website URL.

        Leads without a website are returned unchanged. A single website that
        cannot be opened or scanned never stops the remaining leads
        (Requirement 7); the affected lead keeps its existing data.
        """
        enriched: list[Lead] = []
        for lead in leads:
            if not lead.website:
                enriched.append(lead)
                continue
            try:
                email = self._crawler.enrich(lead, page)
            except Exception as exc:
                self._logger.warning("Website failed for '%s': %s", lead.business_name, exc)
                enriched.append(lead)
                continue
            if email:
                self._logger.info("Email discovered for '%s': %s.", lead.business_name, email)
            enriched.append(lead.with_email(email))
        return enriched
