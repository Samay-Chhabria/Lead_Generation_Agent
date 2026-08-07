"""Tests for intelligent result selection (limits, parsing, ranking)."""

import pytest

from app.models.business_reference import BusinessReference
from app.providers.result_selection import (
    DEFAULT_RESULT_LIMIT,
    candidate_budget,
    extract_card_signals,
    parse_rating,
    parse_requested_limit,
    parse_review_count,
    resolve_result_limit,
    score_reference,
    select_top,
)


def _reference(name: str, index: int, **signals) -> BusinessReference:
    return BusinessReference(
        business_id=f"id:{name}",
        business_name=name,
        listing_index=index,
        provider="google_maps",
        **signals,
    )


# --------------------------------------------------------------------------- #
# parse_requested_limit
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "text",
    [
        "Top 10 restaurants in Lahore",
        "top 10 restaurants",
        "find the top 10 restaurants",
    ],
)
def test_parses_top_number(text: str) -> None:
    assert parse_requested_limit(text) == 10


@pytest.mark.parametrize(
    "text,expected",
    [
        ("first 5 coffee shops in Karachi", 5),
        ("best 3 law firms in Islamabad", 3),
        ("at least 7 dentists near Lahore", 7),
        ("up to 12 gyms in Karachi", 12),
        ("find 3 coffee shops in Lahore", 3),
        ("collect 50 software companies in Pakistan", 50),
        ("give me 5 restaurants near Clifton", 5),
        ("need 4 plumbers in Karachi", 4),
        ("5 coffee shops in Lahore", 5),
        ("50 software companies in Pakistan", 50),
    ],
)
def test_parses_explicit_counts(text: str, expected: int) -> None:
    assert parse_requested_limit(text) == expected


def test_ignores_numbers_inside_locations() -> None:
    assert parse_requested_limit("plumbers in DHA Phase 5 Karachi") is None
    assert parse_requested_limit("car mechanics in Block 12 Gulberg") is None
    assert parse_requested_limit("law firms near Sector 6 Islamabad") is None


def test_returns_none_for_empty_text() -> None:
    assert parse_requested_limit("") is None
    assert parse_requested_limit(None) is None  # type: ignore[arg-type]


def test_ignores_non_positive_counts() -> None:
    assert parse_requested_limit("find 0 coffee shops") is None


def test_prefers_top_over_a_later_verb() -> None:
    assert parse_requested_limit("find the top 3 coffee shops in Sector 12") == 3


# --------------------------------------------------------------------------- #
# resolve_result_limit / candidate_budget
# --------------------------------------------------------------------------- #


def test_resolve_uses_explicit_request() -> None:
    assert resolve_result_limit(3, DEFAULT_RESULT_LIMIT) == 3
    assert resolve_result_limit(50, DEFAULT_RESULT_LIMIT) == 50


def test_resolve_passes_through_configured_default() -> None:
    assert resolve_result_limit(None, DEFAULT_RESULT_LIMIT) == 5
    assert resolve_result_limit(None, 8) == 8
    assert resolve_result_limit(None, 25) == 25
    assert resolve_result_limit(None, 100) == 100


def test_candidate_budget_provides_a_small_pool() -> None:
    assert candidate_budget(5) == 10
    assert candidate_budget(10) == 10
    assert candidate_budget(3) == 8
    assert candidate_budget(50) == 50


# --------------------------------------------------------------------------- #
# Card signal parsing
# --------------------------------------------------------------------------- #


def test_parses_rating_from_card_text() -> None:
    assert parse_rating("4.3 stars") == 4.3
    assert parse_rating("4.5 out of 5") == 4.5
    assert parse_rating("rating 4.7") == 4.7
    assert parse_rating("Acme · 4.9/5 · (120)") == 4.9


def test_parses_review_count() -> None:
    assert parse_review_count("120 reviews") == 120
    assert parse_review_count("4.3 stars (120)") == 120
    assert parse_review_count("1,200 reviews") == 1200


def test_extract_card_signals_combines_markers() -> None:
    rating, reviews, website, verified = extract_card_signals(
        "Acme Corp", "4.6 (320) reviews", "www.acme.example"
    )
    assert rating == 4.6
    assert reviews == 320
    assert website is True
    assert verified is False

    _, _, _, verified = extract_card_signals("Beta Ltd", "Verified listing")
    assert verified is True


def test_extract_card_signals_missing_values_are_neutral() -> None:
    rating, reviews, website, verified = extract_card_signals("Acme Corp")
    assert rating is None
    assert reviews is None
    assert website is False
    assert verified is False


# --------------------------------------------------------------------------- #
# Scoring and selection
# --------------------------------------------------------------------------- #


def test_score_reference_uses_available_signals() -> None:
    rich = _reference("Rich", 0, rating=5.0, review_count=1000, has_website=True, verified=True)
    bare = _reference("Bare", 1)
    assert score_reference(rich, pool_size=2) > score_reference(bare, pool_size=2)


def test_select_top_preserves_discovery_order_when_within_limit() -> None:
    references = [_reference("A", 0), _reference("B", 1), _reference("C", 2)]

    selected = select_top(references, 5)

    assert [r.business_name for r in selected] == ["A", "B", "C"]


def test_select_top_ranks_by_quality_before_extraction() -> None:
    references = [
        _reference("Low", 0, rating=4.0, review_count=10),
        _reference("High", 1, rating=5.0, review_count=900, has_website=True, verified=True),
        _reference("Mid", 2, rating=4.6, review_count=200),
    ]

    selected = select_top(references, 2)

    assert [r.business_name for r in selected] == ["High", "Mid"]


def test_select_top_without_signals_keeps_top_results() -> None:
    references = [_reference(f"B{i}", i) for i in range(6)]

    selected = select_top(references, 3)

    assert [r.business_name for r in selected] == ["B0", "B1", "B2"]


def test_select_top_is_stable_and_bounded() -> None:
    references = [_reference(f"B{i}", i) for i in range(12)]

    selected = select_top(references, 5)

    assert len(selected) == 5
    assert len(set(r.business_name for r in selected)) == 5


def test_select_top_handles_empty_and_non_positive_limits() -> None:
    references = [_reference("A", 0)]
    assert select_top([], 5) == []
    assert select_top(references, 0) == []
