"""Search plan data model."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SearchPlan:
    """Planned searches that drive lead collection (Milestone 4+).

    A plan describes what to search for, where, via which provider, and how
    many results to collect. Produced by the prompt parser (Milestone 2).
    """

    original_prompt: str
    business_type: str
    location: str | None = None
    provider: str = "google"
    max_results: int = 5

    def __post_init__(self) -> None:
        if not self.original_prompt.strip():
            raise ValueError("original_prompt must not be empty.")
        if not self.business_type.strip():
            raise ValueError("business_type must not be empty.")
        if not self.provider.strip():
            raise ValueError("provider must not be empty.")
        if self.max_results <= 0:
            raise ValueError("max_results must be a positive integer.")
