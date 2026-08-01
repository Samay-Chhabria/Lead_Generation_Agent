"""Lead data validation and cleaning (planned for Milestone 6).

Scaffold only. The validator will check and normalize email addresses,
phone numbers, and URLs, and remove duplicate leads before export.
"""

from app.models.lead import Lead


class Validator:
    """Validates and cleans extracted lead data."""

    def validate(self, lead: Lead) -> bool:
        """Return True if the lead passes validation.

        Args:
            lead: The lead to validate.

        Returns:
            True when the lead is valid, False otherwise.

        Raises:
            NotImplementedError: Milestone 6 implements this method.
        """
        raise NotImplementedError("Validator.validate will be implemented in Milestone 6.")
