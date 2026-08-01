"""Business reference data model.

A BusinessReference is a discovered business listing. It is intentionally
lightweight: it carries only enough information to identify a listing, dedupe
it against other listings, and revisit it later. Contact data (phone, email,
website, address) is deliberately excluded and arrives in the extraction
milestone.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BusinessReference:
    """A discovered business listing on a search provider's results page.

    Attributes:
        business_id: A unique identifier for the listing. On Google Maps this
            is the listing's data-entity-id; when that is unavailable the
            listing URL is used instead.
        business_name: The display name of the business.
        listing_url: The URL of the business listing page, if the provider
            exposes one.
        listing_index: The zero-based position of the listing on the results
            page at the moment it was discovered.
        provider: The name of the provider that discovered the listing.
    """

    business_id: str
    business_name: str
    listing_url: str | None = None
    listing_index: int = 0
    provider: str = ""

    @property
    def dedupe_key(self) -> str:
        """Return the key used to detect duplicate listings.

        Prefers the listing URL because it is the most stable identifier a
        provider exposes; falls back to the business id, and finally to the
        business name so listings without any provider identifier can still be
        deduplicated.
        """
        if self.listing_url:
            return self.listing_url
        if self.business_id:
            return self.business_id
        return self.business_name

    def __post_init__(self) -> None:
        if not self.business_id.strip():
            raise ValueError("business_id must not be empty.")
        if not self.business_name.strip():
            raise ValueError("business_name must not be empty.")
        if self.listing_index < 0:
            raise ValueError("listing_index must be a non-negative integer.")
