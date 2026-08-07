"""Website crawling tool.

Opens each lead's website and crawls it (including contact pages) to discover
an email address, then returns enriched leads. Builds on the existing
``WebsiteNavigator``, ``EmailDiscoveryEngine``, and ``ContactPageCrawler`` so
the enrichment behaviour matches the deterministic pipeline.
"""

from typing import Any

from app.execution.execution_logger import get_execution_logger
from app.extractor.contact_page_crawler import ContactPageCrawler
from app.models.lead import Lead
from app.tools.base import Tool, ToolResult


class WebsiteCrawlerTool(Tool):
    """Crawl business websites to discover contact emails."""

    name = "website_crawler"
    description = (
        "Open each business's website and crawl it (including contact and "
        "about pages) to discover email addresses."
    )

    def run(self, leads: list[Lead] | None = None, **kwargs: Any) -> ToolResult:
        """Enrich each lead with an email discovered on its website.

        Args:
            leads: The leads to enrich. Leads without a website are skipped.

        Returns:
            A ToolResult whose ``data`` holds the enriched ``leads``, the
            ``emails_found`` count, and a per-business ``emails`` map.
        """
        leads = list(leads or [])
        page = self.context.get_page()
        if page is None:
            return ToolResult.fail("No browser page is available for website crawling.")
        crawler = ContactPageCrawler(settings=self.settings, logger=self._logger)
        enriched: list[Lead] = []
        emails: dict[str, str] = {}
        exec_log = get_execution_logger()
        targets = [lead for lead in leads if lead.has_website()]
        total = len(targets)
        for index, lead in enumerate(targets):
            exec_log.business_started("website_crawler", lead.business_name, index + 1, total)
            self._logger.info("Crawling website for '%s'.", lead.business_name)
            try:
                email = crawler.enrich(lead, page)
                exec_log.business_done("website_crawler", lead.business_name, True, email)
            except Exception as exc:
                self._logger.warning("Website crawl failed for '%s': %s", lead.business_name, exc)
                email = ""
                exec_log.business_done("website_crawler", lead.business_name, False, str(exc))
            exec_log.progress(index + 1, total)
            emails[lead.business_name] = email
            enriched.append(lead.with_email(email))
        self._logger.info("Website crawl complete: %d emails found.", len(emails))
        return ToolResult.ok(
            leads=enriched,
            emails=emails,
            emails_found=sum(1 for value in emails.values() if value),
        )
