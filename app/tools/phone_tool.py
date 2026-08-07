"""Phone extraction tool.

Extracts phone numbers for businesses that still miss one. When a lead lacks a
phone number and carries a listing source URL, the listing is reopened and the
phone is read with the existing ``BusinessNavigator`` and
``BusinessDetailExtractor`` components.
"""

from typing import Any

from app.execution.execution_logger import get_execution_logger
from app.extractor.business_detail_extractor import BusinessDetailExtractor
from app.extractor.business_navigator import BusinessNavigator
from app.models.business_reference import BusinessReference
from app.models.lead import Lead
from app.tools.base import Tool, ToolResult


class PhoneExtractorTool(Tool):
    """Extract phone numbers from business listing pages."""

    name = "phone_extractor"
    description = "Extract phone numbers for businesses by reopening their listing pages."

    def run(
        self,
        leads: list[Lead] | None = None,
        references: list[Any] | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Enrich leads with phone numbers found on their listing pages.

        Args:
            leads: The leads to enrich. Leads that already have a phone are
                kept unchanged.
            references: Optional BusinessReference objects to scan when leads
                have no source URL.

        Returns:
            A ToolResult whose ``data`` holds the enriched ``leads`` and the
            number of phones found.
        """
        leads = list(leads or [])
        page = self.context.get_page()
        if page is None:
            return ToolResult.fail("No browser page is available for phone extraction.")
        navigator = BusinessNavigator(settings=self.settings, logger=self._logger)
        extractor = BusinessDetailExtractor(logger=self._logger)
        references = list(references or [])

        enriched: list[Lead] = []
        phones_found = 0
        exec_log = get_execution_logger()
        total = len(leads)
        for index, lead in enumerate(leads):
            if lead.has_phone():
                enriched.append(lead)
                continue
            exec_log.business_started("phone_extractor", lead.business_name, index + 1, total)
            self._logger.info("Extracting phone for '%s'.", lead.business_name)
            reference = self._reference_for(lead, references, index)
            try:
                listing_page = navigator.open(reference, page)
                extracted = extractor.extract(
                    listing_page, reference, search_query=lead.search_query
                )
                phone = extracted.phone_number
                exec_log.business_done("phone_extractor", lead.business_name, True, phone)
            except Exception as exc:
                self._logger.warning(
                    "Phone extraction failed for '%s': %s", lead.business_name, exc
                )
                phone = ""
                exec_log.business_done("phone_extractor", lead.business_name, False, str(exc))
            exec_log.progress(index + 1, total)
            if phone:
                phones_found += 1
            enriched.append(_set_phone(lead, phone))
        self._logger.info("Phone extraction complete: %d phones found.", phones_found)
        return ToolResult.ok(leads=enriched, phones_found=phones_found)

    @staticmethod
    def _reference_for(lead: Lead, references: list[Any], index: int) -> BusinessReference:
        """Build a reference for a lead, preferring a matching provided one."""
        for ref in references:
            if getattr(ref, "business_name", "") == lead.business_name:
                return ref
        return BusinessReference(
            business_id=lead.source_url or lead.business_name,
            business_name=lead.business_name,
            listing_url=lead.source_url or None,
            listing_index=index,
            provider=lead.provider,
        )


def _set_phone(lead: Lead, phone: str) -> Lead:
    """Return a copy of the lead with a phone set when it was missing."""
    if lead.has_phone() or not phone:
        return lead
    from dataclasses import replace

    return replace(lead, phone_number=phone)
