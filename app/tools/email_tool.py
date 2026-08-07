"""Email extraction tool.

Extracts email addresses from business pages. Works in two modes: when a
``leads`` list is provided it opens each lead's website homepage and scans it
for an email; when raw ``pages`` (already-opened pages) are provided it scans
those directly.
"""

from typing import Any

from app.execution.execution_logger import get_execution_logger
from app.extractor.email_discovery_engine import EmailDiscoveryEngine
from app.extractor.website_navigator import WebsiteNavigator
from app.models.lead import Lead
from app.tools.base import Tool, ToolResult


class EmailExtractorTool(Tool):
    """Extract email addresses from business websites."""

    name = "email_extractor"
    description = (
        "Open each business website's homepage and extract its email address when one is present."
    )

    def run(
        self,
        leads: list[Lead] | None = None,
        pages: list[Any] | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Extract emails from the given leads or already-open pages.

        Args:
            leads: Leads whose websites should be opened and scanned. Leads
                without a website are skipped.
            pages: Optional already-loaded pages to scan directly.

        Returns:
            A ToolResult whose ``data`` holds the enriched ``leads``, the
            ``emails_found`` count, and a per-business ``emails`` map.
        """
        leads = list(leads or [])
        engine = EmailDiscoveryEngine(logger=self._logger)
        emails: dict[str, str] = {}

        if pages:
            for index, page in enumerate(pages):
                email = self._discover(engine, page)
                if email:
                    emails[f"page_{index}"] = email

        navigator = WebsiteNavigator(settings=self.settings, logger=self._logger)
        page = self.context.get_page()
        if page is None:
            return ToolResult.fail("No browser page is available for email extraction.")
        enriched: list[Lead] = []
        exec_log = get_execution_logger()
        targets = [lead for lead in leads if lead.has_website()]
        total = len(targets)
        for index, lead in enumerate(targets):
            exec_log.business_started("email_extractor", lead.business_name, index + 1, total)
            self._logger.info("Extracting email for '%s'.", lead.business_name)
            try:
                navigator.open(lead, page)
                email = self._discover(engine, page)
                exec_log.business_done("email_extractor", lead.business_name, True, email)
            except Exception as exc:
                self._logger.warning(
                    "Email extraction failed for '%s': %s", lead.business_name, exc
                )
                email = ""
                exec_log.business_done("email_extractor", lead.business_name, False, str(exc))
            exec_log.progress(index + 1, total)
            emails[lead.business_name] = email
            enriched.append(lead.with_email(email))
        self._logger.info("Email extraction complete: %d emails found.", len(emails))
        return ToolResult.ok(
            leads=enriched,
            emails=emails,
            emails_found=sum(1 for value in emails.values() if value),
        )

    @staticmethod
    def _discover(engine: EmailDiscoveryEngine, page: Any) -> str:
        """Run the discovery engine defensively on a page."""
        try:
            return engine.discover(page)
        except Exception:
            return ""
