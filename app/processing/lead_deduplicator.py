"""Lead deduplication.

LeadDeduplicator removes duplicate businesses from a list of normalized,
validated leads. Every lead is identified by the strongest signal it carries,
in priority order:

1. Website URL
2. Business name + location
3. Phone number

The first occurrence of each identity is kept; later matches are dropped and
each removal is logged. A lead that carries none of these signals is treated as
unique and is never removed, so distinct businesses are always preserved.
"""

import logging
import re
from dataclasses import dataclass, field

from app.config.logging_config import get_logger
from app.models.lead import Lead

_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class DeduplicationResult:
    """Outcome of deduplicating a list of leads.

    Attributes:
        leads: The surviving leads, in their original relative order.
        duplicates_removed: How many duplicate leads were dropped.
        removed: The business names of the dropped leads, in removal order.
    """

    leads: list[Lead]
    duplicates_removed: int
    removed: list[str] = field(default_factory=list)


class LeadDeduplicator:
    """Remove duplicate businesses while preserving unique leads."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        """Initialize the deduplicator.

        Args:
            logger: Optional logger; a package logger is used when omitted.
        """
        self._logger = logger or get_logger("deduplicator")

    def deduplicate(self, leads: list[Lead]) -> DeduplicationResult:
        """Return the input leads with duplicates removed.

        The first occurrence of each identity is kept. Each removal is logged
        with the business name that was dropped.

        Args:
            leads: Normalized, validated leads to deduplicate.

        Returns:
            A DeduplicationResult with the surviving leads and statistics.
        """
        seen: set[tuple[str, ...]] = set()
        kept: list[Lead] = []
        removed: list[str] = []
        for lead in leads:
            identity = self._identity(lead)
            if identity is not None and identity in seen:
                removed.append(lead.business_name)
                self._logger.warning(
                    "Duplicate detected and lead removed: '%s'.", lead.business_name
                )
                continue
            if identity is not None:
                seen.add(identity)
            kept.append(lead)
        return DeduplicationResult(
            leads=kept,
            duplicates_removed=len(removed),
            removed=removed,
        )

    def _identity(self, lead: Lead) -> tuple[str, ...] | None:
        """Return the strongest identity key for a lead, or None.

        The website is preferred when present, then the business name paired
        with the location, then the phone number. A lead with none of these
        signals has no identity and is never deduplicated.
        """
        website = self._fold(lead.website).rstrip("/")
        if website:
            return ("website", website)
        name = self._fold(lead.business_name)
        location = self._fold(lead.location)
        if name and location:
            return ("name_location", name, location)
        if lead.phone_number:
            return ("phone", lead.phone_number)
        return None

    @staticmethod
    def _fold(value: str | None) -> str:
        """Lowercase a value and collapse internal whitespace for comparison."""
        if value is None:
            return ""
        return _WHITESPACE_RE.sub(" ", value.strip().lower())
