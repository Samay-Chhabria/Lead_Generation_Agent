"""Lead validation.

LeadValidator checks a normalized Lead against structural rules. The business
name is required; every present optional field must be well formed. Missing
optional fields never invalidate a lead — they simply remain empty strings —
so a business without an email, phone, or website still passes (Requirement 7).

The validator never mutates a lead. It reports a boolean verdict and, when a
lead is rejected, a human-readable reason that the pipeline logs so the run can
continue past an unusable lead.
"""

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from app.extractor.email_validator import EMAIL_PATTERN
from app.models.lead import Lead

PHONE_PATTERN = re.compile(r"^\+?\d{6,15}$")
SUPPORTED_URL_SCHEMES = ("http", "https")


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Outcome of validating a single lead.

    Attributes:
        is_valid: True when the lead passed every rule.
        reason: Human-readable explanation when the lead was rejected.
    """

    is_valid: bool
    reason: str = ""


class LeadValidator:
    """Validate leads and explain why a lead is rejected."""

    def validate(self, lead: Lead) -> ValidationResult:
        """Return the validation verdict for a lead.

        The business name must be non-empty. Any present optional field must
        be well formed: the website must be an http/https URL, the email must
        match a valid email pattern, and the phone must be in normalized form.
        Missing optional fields are always accepted.

        Args:
            lead: The (ideally normalized) lead to validate.

        Returns:
            A ValidationResult describing the verdict.
        """
        name = lead.business_name
        if not self.is_valid_business_name(name):
            return ValidationResult(False, "business name is empty")
        if lead.website and not self.is_valid_website(lead.website):
            return ValidationResult(False, f"invalid website URL: {lead.website!r}")
        if lead.email and not self.is_valid_email(lead.email):
            return ValidationResult(False, f"invalid email: {lead.email!r}")
        if lead.phone_number and not self.is_valid_phone(lead.phone_number):
            return ValidationResult(False, f"invalid phone number: {lead.phone_number!r}")
        return ValidationResult(True)

    def is_valid(self, lead: Lead) -> bool:
        """Return True when the lead passes validation."""
        return self.validate(lead).is_valid

    def is_valid_business_name(self, value: str | None) -> bool:
        """Return True when the business name is non-empty."""
        return bool((value or "").strip())

    def is_valid_website(self, value: str | None) -> bool:
        """Return True when the value is a valid http/https URL.

        An empty value is considered valid because the website is optional.
        """
        candidate = (value or "").strip()
        if not candidate:
            return True
        parsed = urlparse(candidate)
        return parsed.scheme.lower() in SUPPORTED_URL_SCHEMES and bool(parsed.netloc)

    def is_valid_email(self, value: str | None) -> bool:
        """Return True when the value matches a valid email pattern.

        An empty value is considered valid because the email is optional.
        """
        candidate = (value or "").strip().lower()
        if not candidate:
            return True
        return bool(EMAIL_PATTERN.match(candidate))

    def is_valid_phone(self, value: str | None) -> bool:
        """Return True when the value is a normalized phone number.

        A normalized phone is six to fifteen digits with an optional leading
        "+". An empty value is considered valid because the phone is optional.
        """
        candidate = (value or "").strip()
        if not candidate:
            return True
        return bool(PHONE_PATTERN.match(candidate))
