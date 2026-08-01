"""Output model produced by a provider run."""

from dataclasses import dataclass, field
from typing import Any

from app.models.business_reference import BusinessReference
from app.models.lead import Lead


@dataclass(frozen=True, slots=True)
class ProviderResult:
    """Summary of one provider run.

    The discovered businesses are exposed as BusinessReference objects and the
    extracted leads as Lead objects. The success flag, query, provider name,
    and optional page reference describe the run itself.
    """

    business_links: list[str] = field(default_factory=list)
    raw_results: list[Any] = field(default_factory=list)
    business_references: list[BusinessReference] = field(default_factory=list)
    leads: list[Lead] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    success: bool = False
    query: str = ""
    provider_name: str = ""
    raw_page_reference: Any = None

    @property
    def business_count(self) -> int:
        """Return the number of discovered business references."""
        return len(self.business_references)

    @property
    def lead_count(self) -> int:
        """Return the number of extracted leads."""
        return len(self.leads)
