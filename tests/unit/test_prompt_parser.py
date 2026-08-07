"""Tests for the prompt parser."""

from pathlib import Path

import pytest

from app.config.settings import Settings
from app.exceptions.parser_exception import ParserException
from app.parser.prompt_parser import PromptParser


@pytest.fixture
def settings() -> Settings:
    return Settings(
        headless=True,
        timeout=30_000,
        max_leads=25,
        search_provider="google_maps",
        output_dir=Path("outputs"),
        log_dir=Path("logs"),
        log_level="INFO",
    )


def test_parses_simple_prompt(settings: Settings) -> None:
    plan = PromptParser().parse("coffee shops in America", settings=settings)

    assert plan.business_type == "coffee shops"
    assert plan.location == "America"


def test_parses_software_companies(settings: Settings) -> None:
    plan = PromptParser().parse("software companies in Karachi", settings=settings)

    assert plan.business_type == "software companies"
    assert plan.location == "Karachi"


def test_parses_restaurants(settings: Settings) -> None:
    plan = PromptParser().parse("restaurants in New York", settings=settings)

    assert plan.business_type == "restaurants"
    assert plan.location == "New York"


def test_parses_marketing_agencies(settings: Settings) -> None:
    plan = PromptParser().parse("marketing agencies in Dubai", settings=settings)

    assert plan.business_type == "marketing agencies"
    assert plan.location == "Dubai"


def test_parses_near_separator(settings: Settings) -> None:
    plan = PromptParser().parse("dentists near Lahore", settings=settings)

    assert plan.business_type == "dentists"
    assert plan.location == "Lahore"


def test_parses_around_separator(settings: Settings) -> None:
    plan = PromptParser().parse("law firms around Islamabad", settings=settings)

    assert plan.business_type == "law firms"
    assert plan.location == "Islamabad"


def test_collapses_extra_whitespace(settings: Settings) -> None:
    plan = PromptParser().parse("  coffee   shops   in   America  ", settings=settings)

    assert plan.business_type == "coffee shops"
    assert plan.location == "America"
    assert plan.original_prompt == "coffee shops in America"


def test_is_case_insensitive(settings: Settings) -> None:
    plan = PromptParser().parse("Coffee Shops IN America", settings=settings)

    assert plan.business_type == "Coffee Shops"
    assert plan.location == "America"


def test_uses_provider_and_max_results_from_settings(settings: Settings) -> None:
    plan = PromptParser().parse("coffee shops in America", settings=settings)

    assert plan.provider == "google_maps"
    assert plan.max_results == 25


@pytest.mark.parametrize(
    "prompt,expected",
    [
        ("find 3 coffee shops in America", 3),
        ("collect 50 software companies in Pakistan", 50),
        ("Top 10 restaurants in New York", 10),
        ("at least 7 dentists near Lahore", 7),
        ("5 coffee shops in Lahore", 5),
    ],
)
def test_respects_explicit_numeric_requests(prompt: str, expected: int, settings: Settings) -> None:
    plan = PromptParser().parse(prompt, settings=settings)

    assert plan.max_results == expected


def test_ignores_numbers_inside_locations(settings: Settings) -> None:
    plan = PromptParser().parse("plumbers in DHA Phase 5 Karachi", settings=settings)

    assert plan.max_results == 25


def test_parses_without_explicit_settings() -> None:
    plan = PromptParser().parse("coffee shops in America")

    assert plan.business_type == "coffee shops"
    assert plan.location == "America"


def test_rejects_empty_prompt(settings: Settings) -> None:
    with pytest.raises(ParserException):
        PromptParser().parse("", settings=settings)


def test_rejects_whitespace_only_prompt(settings: Settings) -> None:
    with pytest.raises(ParserException):
        PromptParser().parse("   ", settings=settings)


def test_rejects_missing_location(settings: Settings) -> None:
    with pytest.raises(ParserException):
        PromptParser().parse("coffee shops", settings=settings)


def test_rejects_missing_business_type(settings: Settings) -> None:
    with pytest.raises(ParserException):
        PromptParser().parse("in America", settings=settings)
