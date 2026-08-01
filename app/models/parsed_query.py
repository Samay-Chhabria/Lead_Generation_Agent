"""Parsed query data model."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParsedQuery:
    """Structured representation of a natural-language prompt.

    Produced by the prompt parser (Milestone 2) from inputs such as
    "coffee shops in America".
    """

    business_type: str
    location: str | None = None
