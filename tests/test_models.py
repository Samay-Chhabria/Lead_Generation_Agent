"""Tests for data models."""

from datetime import datetime

import pytest

from app.models.business_reference import BusinessReference
from app.models.lead import Lead
from app.models.parsed_query import ParsedQuery
from app.models.search_plan import SearchPlan
from app.providers.base_provider import BaseProvider


def test_lead_defaults_are_empty_strings() -> None:
    lead = Lead(business_name="Acme")

    assert lead.business_name == "Acme"
    assert lead.phone_number == ""
    assert lead.phone == ""
    assert lead.email == ""
    assert lead.website == ""
    assert lead.location == ""
    assert lead.provider == ""
    assert lead.search_query == ""
    assert lead.source_url == ""
    assert isinstance(lead.collected_at, datetime)


def test_lead_full_fields() -> None:
    lead = Lead(
        business_name="Acme Corp",
        phone_number="+1 555 0100",
        email="hello@acme.example",
        website="https://acme.example",
        location="Karachi",
        provider="google_maps",
        search_query="software companies in Karachi",
        source_url="https://www.google.com/maps/place/Acme",
    )

    assert lead.business_name == "Acme Corp"
    assert lead.phone_number == "+1 555 0100"
    assert lead.email == "hello@acme.example"
    assert lead.website == "https://acme.example"
    assert lead.location == "Karachi"
    assert lead.provider == "google_maps"
    assert lead.search_query == "software companies in Karachi"
    assert lead.source_url == "https://www.google.com/maps/place/Acme"


def test_lead_rejects_non_string_business_name() -> None:
    with pytest.raises(TypeError):
        Lead(business_name=None)  # type: ignore[arg-type]


def test_parsed_query_fields() -> None:
    query = ParsedQuery(business_type="coffee shops", location="America")

    assert query.business_type == "coffee shops"
    assert query.location == "America"


def test_search_plan_fields() -> None:
    plan = SearchPlan(
        original_prompt="software companies in Karachi",
        business_type="software companies",
        location="Karachi",
        provider="google_maps",
        max_results=25,
    )

    assert plan.original_prompt == "software companies in Karachi"
    assert plan.business_type == "software companies"
    assert plan.location == "Karachi"
    assert plan.provider == "google_maps"
    assert plan.max_results == 25


def test_search_plan_rejects_blank_business_type() -> None:
    with pytest.raises(ValueError):
        SearchPlan(
            original_prompt="in America",
            business_type=" ",
            location="America",
            provider="google",
        )


def test_search_plan_rejects_non_positive_max_results() -> None:
    with pytest.raises(ValueError):
        SearchPlan(
            original_prompt="coffee shops in America",
            business_type="coffee shops",
            location="America",
            provider="google",
            max_results=0,
        )


def test_base_provider_is_abstract() -> None:
    assert BaseProvider.__abstractmethods__


def test_business_reference_fields() -> None:
    reference = BusinessReference(
        business_id="0x1:0x2a",
        business_name="Acme Corp",
        listing_url="https://www.google.com/maps/place/Acme",
        listing_index=3,
        provider="google_maps",
    )

    assert reference.business_id == "0x1:0x2a"
    assert reference.business_name == "Acme Corp"
    assert reference.listing_url == "https://www.google.com/maps/place/Acme"
    assert reference.listing_index == 3
    assert reference.provider == "google_maps"


def test_business_reference_dedupe_key_prefers_url() -> None:
    reference = BusinessReference(
        business_id="0x1:0x2a",
        business_name="Acme Corp",
        listing_url="https://www.google.com/maps/place/Acme",
    )

    assert reference.dedupe_key == "https://www.google.com/maps/place/Acme"


def test_business_reference_dedupe_key_falls_back_to_id() -> None:
    reference = BusinessReference(
        business_id="0x1:0x2a",
        business_name="Acme Corp",
    )

    assert reference.dedupe_key == "0x1:0x2a"


def test_business_reference_rejects_empty_name() -> None:
    with pytest.raises(ValueError):
        BusinessReference(business_id="0x1:0x1", business_name=" ")


def test_business_reference_rejects_negative_index() -> None:
    with pytest.raises(ValueError):
        BusinessReference(
            business_id="0x1:0x1",
            business_name="Acme Corp",
            listing_index=-1,
        )
