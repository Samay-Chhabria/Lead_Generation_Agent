"""Email validation.

EmailValidator normalizes candidate email addresses and rejects malformed
ones. It is used by the email discovery engine to decide whether a scraped
string is a usable address. Invalid candidates yield an empty string so
callers never store garbage (Requirement 7).
"""

import re

EMAIL_PATTERN = re.compile(r"^[a-z0-9._%+-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}$")


class EmailValidator:
    """Validate and normalize email addresses.

    Validation strips surrounding whitespace and normalizes case before
    checking the address against a pragmatic structural pattern. A valid
    address is returned lowercased; everything else yields an empty string.
    """

    def is_valid(self, email: str) -> bool:
        """Return True when the candidate is a structurally valid email."""
        return bool(self.normalize(email))

    def normalize(self, email: str) -> str:
        """Return the normalized email, or an empty string when invalid."""
        candidate = (email or "").strip().lower()
        if not candidate or not EMAIL_PATTERN.match(candidate):
            return ""
        return candidate
