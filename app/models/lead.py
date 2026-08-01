"""Lead data model."""

from dataclasses import dataclass, field, replace
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Lead:
    """A single business lead collected during a search.

    Missing information is represented by empty strings and never causes
    failures (Requirement 7). ``collected_at`` records when the lead was
    created.
    """

    business_name: str
    phone_number: str = ""
    email: str = ""
    website: str = ""
    location: str = ""
    provider: str = ""
    search_query: str = ""
    source_url: str = ""
    collected_at: datetime = field(default_factory=datetime.now)

    @property
    def phone(self) -> str:
        """Backward-compatible alias for ``phone_number``."""
        return self.phone_number

    def with_email(self, email: str) -> "Lead":
        """Return a copy with the email set, preserving an existing email.

        An already-populated email is never overwritten, so enrichment does
        not destroy previously discovered contact data. ``collected_at`` is
        preserved.
        """
        if self.email:
            return self
        return replace(self, email=email)

    def __post_init__(self) -> None:
        if not isinstance(self.business_name, str):
            raise TypeError("business_name must be a string.")
        if not isinstance(self.collected_at, datetime):
            raise TypeError("collected_at must be a datetime.")
