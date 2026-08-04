"""Lead field normalization.

LeadNormalizer cleans the raw values of a Lead so that every lead carries a
consistent, comparable representation of its data. Normalization is purely
textual: whitespace is trimmed and collapsed, emails are lowercased, website
URLs lose their trailing slashes and host case, and phone numbers are
flattened into a digits-only form with an optional leading "+".

A lead is never discarded here. Values that cannot be cleaned become empty
strings, so missing or unexpected data never crashes the pipeline and always
remains safe to store (Requirement 7).
"""

import re
from dataclasses import replace
from urllib.parse import urlparse, urlunsplit

from app.models.lead import Lead

_WHITESPACE_RE = re.compile(r"\s+")
_NON_DIGITS_RE = re.compile(r"\D")
_HTTP_SCHEMES = ("http://", "https://")


def _clean_text(value: str | None) -> str:
    """Trim a value and collapse every internal whitespace run into one space."""
    if value is None:
        return ""
    return _WHITESPACE_RE.sub(" ", str(value).strip())


class LeadNormalizer:
    """Normalize every field of a Lead into a clean, comparable form."""

    def normalize(self, lead: Lead) -> Lead:
        """Return a copy of the lead with every field normalized.

        The input lead is never mutated; a new Lead carrying the normalized
        values is returned. ``collected_at`` and any unrelated fields are
        preserved.

        Args:
            lead: The raw lead to normalize.

        Returns:
            A new Lead with normalized field values.
        """
        return replace(
            lead,
            business_name=self.normalize_business_name(lead.business_name),
            phone_number=self.normalize_phone(lead.phone_number),
            email=self.normalize_email(lead.email),
            website=self.normalize_website(lead.website),
            location=self.normalize_location(lead.location),
        )

    def normalize_business_name(self, value: str | None) -> str:
        """Trim the name and collapse internal whitespace."""
        return _clean_text(value)

    def normalize_email(self, value: str | None) -> str:
        """Return the email trimmed and lowercased, or an empty string."""
        return _clean_text(value).lower()

    def normalize_location(self, value: str | None) -> str:
        """Trim the location and collapse internal whitespace."""
        return _clean_text(value)

    def normalize_phone(self, value: str | None) -> str:
        """Flatten a phone number into digits with an optional leading ``+``.

        All non-digit characters are removed. A leading "+" is preserved so
        international numbers keep their country-code marker. A value that
        contains no digits becomes an empty string.
        """
        if value is None:
            return ""
        cleaned = _clean_text(value)
        if not cleaned:
            return ""
        digits = _NON_DIGITS_RE.sub("", cleaned)
        if not digits:
            return ""
        prefix = "+" if cleaned.startswith("+") else ""
        return f"{prefix}{digits}"

    def normalize_website(self, value: str | None) -> str:
        """Clean a website URL into a canonical, comparable form.

        Trailing slashes are removed and, for http/https URLs, the scheme and
        host are lowercased while the path keeps its original case. Values
        without a scheme are left otherwise untouched; validity is decided
        later by the validator.
        """
        cleaned = _clean_text(value)
        if not cleaned:
            return ""
        if cleaned.lower().startswith(_HTTP_SCHEMES):
            parsed = urlparse(cleaned)
            return urlunsplit(
                (
                    parsed.scheme.lower(),
                    parsed.netloc.lower(),
                    parsed.path.rstrip("/"),
                    parsed.query,
                    parsed.fragment,
                )
            )
        return cleaned.rstrip("/")
