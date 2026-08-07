"""Business details tool.

Opens each discovered business listing and extracts the full detail set —
name, phone, email, website, location, and supplemental data such as rating —
using the existing ``BusinessNavigator`` and ``BusinessDetailExtractor``.
Returns both extracted leads and a rating map used for rating-filtering.
"""

import re
import time
from typing import Any

from app.execution.execution_logger import get_execution_logger
from app.extractor.business_detail_extractor import BusinessDetailExtractor
from app.extractor.business_navigator import BusinessNavigator
from app.models.business_reference import BusinessReference
from app.models.lead import Lead
from app.providers.google_maps_provider import SELECTOR_PROBE_TIMEOUT_MS, SUPPLEMENTAL_SELECTORS
from app.tools.base import Tool, ToolResult

_RATING_PATTERN = re.compile(r"(\d+(?:\.\d+)?)")


class BusinessDetailsTool(Tool):
    """Open business listings and extract their detailed information."""

    name = "business_details"
    description = (
        "Open each business listing and extract detailed information including "
        "phone, email, website, location, and rating."
    )

    def run(
        self,
        references: list[Any] | None = None,
        leads: list[Lead] | None = None,
        search_query: str = "",
        **kwargs: Any,
    ) -> ToolResult:
        """Extract detailed information for every business.

        Args:
            references: The business references to open. When omitted and
                ``leads`` are provided, references are rebuilt from each
                lead's source URL.
            leads: Optional leads; provided to rebuild references and to
                preserve already-collected data.
            search_query: The query that discovered the businesses.

        Returns:
            A ToolResult whose ``data`` holds the extracted ``leads`` and a
            ``details`` list with per-business supplemental information.
        """
        page = self.context.get_page()
        if page is None:
            return ToolResult.fail("No browser page is available for business details.")
        navigator = BusinessNavigator(settings=self.settings, logger=self._logger)
        extractor = BusinessDetailExtractor(logger=self._logger)

        references = list(references or [])
        leads = list(leads or [])
        if not references:
            references = [
                self._reference_from_lead(lead, index) for index, lead in enumerate(leads)
            ]

        extracted: list[Lead] = []
        details: list[dict[str, str]] = []
        exec_log = get_execution_logger()
        extraction_started = time.perf_counter()
        total = len(references)
        for index, reference in enumerate(references):
            exec_log.business_started("business_details", reference.business_name, index + 1, total)
            self._logger.info("Extracting details for '%s'.", reference.business_name)
            lead = self._extract_with_retry(navigator, extractor, reference, page, search_query)
            if lead is None:
                exec_log.business_done("business_details", reference.business_name, False)
                exec_log.progress(index + 1, total)
                continue
            extracted.append(lead)
            exec_log.business_done("business_details", reference.business_name, True)
            exec_log.progress(index + 1, total)
            try:
                details.append(self._supplemental(page, reference.business_name))
            except Exception:
                details.append({"business_name": reference.business_name})
        exec_log.timing("extraction", time.perf_counter() - extraction_started)
        self._logger.info("Business details complete: %d businesses extracted.", len(extracted))
        return ToolResult.ok(leads=extracted, details=details)

    def _extract_with_retry(
        self,
        navigator: Any,
        extractor: Any,
        reference: Any,
        page: Any,
        search_query: str,
    ) -> Any:
        """Open and extract a business, retrying once before giving up.

        A single slow page or flaky selector is retried; a business that still
        fails is logged and skipped so it never stops the remaining businesses.

        Returns:
            The extracted Lead, or None when the business could not be opened.
        """
        last_error: Exception | None = None
        exec_log = get_execution_logger()
        for attempt in range(1, 3):
            try:
                listing_page = navigator.open(reference, page)
                lead = extractor.extract(listing_page, reference, search_query=search_query)
                if attempt > 1:
                    exec_log.recovered(reference.business_name)
                return lead
            except Exception as exc:
                last_error = exc
                if attempt == 1:
                    exec_log.error("Business Details", str(exc))
                    exec_log.retrying(reference.business_name, attempt, 2)
                self._logger.warning(
                    "Business details attempt %d for '%s' failed: %s",
                    attempt,
                    reference.business_name,
                    exc,
                )
        self._logger.warning("Skipping '%s': %s", reference.business_name, last_error)
        return None

    @staticmethod
    def _reference_from_lead(lead: Lead, index: int) -> BusinessReference:
        return BusinessReference(
            business_id=lead.source_url or lead.business_name,
            business_name=lead.business_name,
            listing_url=lead.source_url or None,
            listing_index=index,
            provider=lead.provider,
        )

    def _supplemental(self, page: Any, business_name: str) -> dict[str, str]:
        """Extract rating and other supplemental values defensively."""
        extra = {"business_name": business_name}
        for field_name, selectors in SUPPLEMENTAL_SELECTORS.items():
            extra[field_name] = self._first_value(page, selectors)
        return extra

    def _first_value(self, page: Any, selectors: tuple[str, ...]) -> str:
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                value = locator.inner_text(timeout=SELECTOR_PROBE_TIMEOUT_MS).strip()
                if value:
                    return value
            except Exception:
                pass
            try:
                value = locator.get_attribute("aria-label", timeout=SELECTOR_PROBE_TIMEOUT_MS)
            except Exception:
                value = None
            if value:
                return value.strip()
        return ""

    @staticmethod
    def rating_of(details: list[dict[str, str]], business_name: str) -> float | None:
        """Return the parsed rating for a business name, if any."""
        for entry in details:
            if entry.get("business_name") == business_name:
                match = _RATING_PATTERN.search(entry.get("rating", "") or "")
                if match:
                    return float(match.group(1))
        return None
