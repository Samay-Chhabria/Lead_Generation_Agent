"""Lead extraction from business pages (planned for Milestone 5).

Scaffold only. The extractor will visit business pages and pull out the
business name, email, phone number, website, and location without failing
when any of those fields is missing.
"""

from app.models.lead import Lead


class LeadExtractor:
    """Extracts structured Lead objects from raw page content."""

    def extract(self, html: str) -> list[Lead]:
        """Extract all leads found in the given page content.

        Args:
            html: Raw HTML content of a business listing page.

        Returns:
            A list of extracted Lead objects.

        Raises:
            NotImplementedError: Milestone 5 implements this method.
        """
        raise NotImplementedError("LeadExtractor.extract will be implemented in Milestone 5.")
