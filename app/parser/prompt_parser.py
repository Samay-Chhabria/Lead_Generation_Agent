"""Natural-language prompt parsing.

Converts prompts such as "coffee shops in America" into a SearchPlan containing
the business type, location, provider, and maximum results. Parsing is
deterministic: no external APIs or language models are involved.
"""

import re

from app.config.settings import Settings, get_settings
from app.exceptions.parser_exception import ParserException
from app.models.search_plan import SearchPlan

_SEPARATOR_PATTERN = re.compile(r"\b(in|near|around)\b", re.IGNORECASE)


class PromptParser:
    """Converts a natural-language prompt into a SearchPlan."""

    def parse(self, prompt: str, settings: Settings | None = None) -> SearchPlan:
        """Parse a prompt into a structured search plan.

        Args:
            prompt: The natural-language prompt supplied by the user.
            settings: Application settings; supplies the provider and maximum
                results. Defaults to the process-wide settings.

        Returns:
            A SearchPlan describing the business type and location.

        Raises:
            ParserException: When the prompt is empty, contains no location
                separator, or is missing a business type or location.
        """
        normalized = self._normalize(prompt)
        match = _SEPARATOR_PATTERN.search(normalized)
        if match is None:
            raise ParserException(
                f"Could not determine a location for prompt '{prompt}'. "
                "Expected a prompt like 'coffee shops in America' using "
                "'in', 'near', or 'around'."
            )
        business_type = normalized[: match.start()].strip()
        location = normalized[match.end() :].strip()
        if not business_type:
            raise ParserException(f"Missing business type in prompt '{prompt}'.")
        if not location:
            raise ParserException(f"Missing location in prompt '{prompt}'.")
        settings = settings or get_settings()
        return SearchPlan(
            original_prompt=normalized,
            business_type=business_type,
            location=location,
            provider=settings.search_provider,
            max_results=settings.max_leads,
        )

    @staticmethod
    def _normalize(prompt: str) -> str:
        """Collapse whitespace and reject empty prompts."""
        cleaned = " ".join(prompt.split())
        if not cleaned:
            raise ParserException("Prompt must not be empty.")
        return cleaned
