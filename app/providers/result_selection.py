"""Intelligent result selection.

Decides how many businesses a search should collect and which of the collected
candidates become the final leads. The default result limit is 5 and a search
never collects more than 10 candidates unless the user explicitly asked for a
larger number (for example "collect 50 software companies"). Collected
candidates are ranked before extraction using whatever card-level signals are
visible (rating, review count, website, verified marker) plus their position in
the results; missing signals never fail the ranking, they simply leave the
position in the results as the deciding factor.
"""

import math
import re

from app.models.business_reference import BusinessReference

#: How many businesses to deliver by default.
DEFAULT_RESULT_LIMIT = 5

#: Hard ceiling for non-explicit requests: never collect more than this unless
#: the user explicitly asked for a larger number.
MAX_RESULT_LIMIT = 10

#: Ranking weights (they sum to 1.0). Position in the results acts as the
#: overall-popularity signal Google already encoded into the ordering.
WEIGHT_RATING = 0.30
WEIGHT_REVIEWS = 0.20
WEIGHT_WEBSITE = 0.20
WEIGHT_VERIFIED = 0.15
WEIGHT_POSITION = 0.15

_COUNT_PATTERNS = (
    re.compile(r"\btop\s+(\d+)", re.IGNORECASE),
    re.compile(r"\b(?:first|best)\s+(\d+)", re.IGNORECASE),
    re.compile(
        r"\b(?:at\s+least|a\s+minimum\s+of|minimum\s+of|up\s+to|no\s+more\s+than)\s+(\d+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:fetch|collect|gather|grab|find|get|list|search|need|discover|want|give\s+me)\s+(\d+)",
        re.IGNORECASE,
    ),
    re.compile(r"^\s*(\d+)\s+"),
)

_RATING_PATTERN = re.compile(r"(\d(?:\.\d+)?)\s*(?:stars?|rating|out\s+of\s+5|/5)", re.IGNORECASE)
_DECIMAL_PATTERN = re.compile(r"\b(\d+\.\d+)\b")
_REVIEWS_PATTERN = re.compile(r"(\d[\d,]*)\s*reviews?", re.IGNORECASE)
_REVIEWS_PAREN_PATTERN = re.compile(r"\((\d[\d,]+)\)")
_WEBSITE_PATTERN = re.compile(r"\bwebsite\b|https?://|www\.", re.IGNORECASE)
_VERIFIED_PATTERN = re.compile(r"\bverified\b|\bowned\b|\bclaimed\b", re.IGNORECASE)


def parse_requested_limit(text: str) -> int | None:
    """Return an explicit count named in the text, or None.

    Understands "top 10 restaurants", "first 5 / best 5", "at least 5",
    "collect 50 software companies", "find 3 coffee shops", and a leading bare
    number ("5 coffee shops"). Numbers inside locations ("DHA Phase 5") are
    deliberately not treated as requests.
    """
    if not text:
        return None
    for pattern in _COUNT_PATTERNS:
        match = pattern.search(text)
        if match is None:
            continue
        try:
            limit = int(match.group(1))
        except (TypeError, ValueError):
            continue
        if limit >= 1:
            return limit
    return None


def resolve_result_limit(requested: int | None, default: int) -> int:
    """Resolve the effective result limit.

    An explicit user request always wins. Otherwise the configured default is
    used as-is; the configured value is the operator's explicit intent, so it is
    not capped here. The ``MAX_RESULT_LIMIT`` ceiling is enforced where a
    non-user default could creep in (the agent tool path).
    """
    if requested is not None:
        return requested
    return max(default, 1)


def candidate_budget(limit: int) -> int:
    """Return how many candidates to collect before ranking.

    A small buffer over the target lets ranking pick the best businesses while
    keeping scrolling bounded: the default target (5) collects at most 10
    candidates. Explicit large requests are not capped.
    """
    if limit <= 10:
        return min(limit + 5, MAX_RESULT_LIMIT)
    return limit


def parse_rating(text: str) -> float | None:
    """Extract a Google rating (1.0-5.0) from card text, if present."""
    match = _RATING_PATTERN.search(text)
    if match is not None:
        try:
            value = float(match.group(1))
        except (TypeError, ValueError):
            value = None
        if value is not None and 1.0 <= value <= 5.0:
            return value
    for match in _DECIMAL_PATTERN.finditer(text):
        try:
            value = float(match.group(1))
        except (TypeError, ValueError):
            continue
        if 1.0 <= value <= 5.0:
            return value
    return None


def parse_review_count(text: str) -> int | None:
    """Extract a review count from card text, if present."""
    match = _REVIEWS_PATTERN.search(text)
    if match is not None:
        return _to_int(match.group(1))
    match = _REVIEWS_PAREN_PATTERN.search(text)
    if match is not None:
        return _to_int(match.group(1))
    return None


def has_website_marker(text: str) -> bool:
    """Return True when the text suggests the listing has a website."""
    return bool(text and _WEBSITE_PATTERN.search(text))


def has_verified_marker(text: str) -> bool:
    """Return True when the text suggests the listing is verified/claimed."""
    return bool(text and _VERIFIED_PATTERN.search(text))


def extract_card_signals(*texts: str) -> tuple[float | None, int | None, bool, bool]:
    """Best-effort (rating, review_count, has_website, verified) from card text.

    Missing signals come back as None/False so callers never fail on them.
    """
    combined = " ".join(text for text in texts if text)
    return (
        parse_rating(combined),
        parse_review_count(combined),
        has_website_marker(combined),
        has_verified_marker(combined),
    )


def score_reference(reference: BusinessReference, pool_size: int) -> float:
    """Score a candidate from 0.0 to 1.0; higher means a better lead."""
    score = 0.0
    if reference.rating is not None:
        score += WEIGHT_RATING * min(reference.rating / 5.0, 1.0)
    if reference.review_count:
        score += WEIGHT_REVIEWS * min(math.log10(reference.review_count) / 3.0, 1.0)
    if reference.has_website:
        score += WEIGHT_WEBSITE
    if reference.verified:
        score += WEIGHT_VERIFIED
    if pool_size > 0:
        score += WEIGHT_POSITION * max(0.0, 1.0 - reference.listing_index / pool_size)
    return score


def select_top(references: list[BusinessReference], limit: int) -> list[BusinessReference]:
    """Return the best ``limit`` references, ranked before extraction.

    When there are no more candidates than the limit, the discovery order is
    preserved unchanged. Ties keep their discovery order because sorting is
    stable.
    """
    if limit <= 0 or not references:
        return []
    if len(references) <= limit:
        return list(references)
    pool_size = len(references)
    ranked = sorted(
        references,
        key=lambda reference: score_reference(reference, pool_size),
        reverse=True,
    )
    return ranked[:limit]


def _to_int(value: str) -> int | None:
    try:
        return int(value.replace(",", ""))
    except (TypeError, ValueError):
        return None
