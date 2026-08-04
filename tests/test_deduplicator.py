"""Tests for lead deduplication."""

import logging

import pytest

from app.models.lead import Lead
from app.processing.lead_deduplicator import LeadDeduplicator


def _lead(**overrides) -> Lead:
    fields = {"business_name": "Acme Corp"}
    fields.update(overrides)
    return Lead(**fields)


def test_duplicate_website_removed() -> None:
    leads = [
        _lead(business_name="Acme Corp", website="https://acme.example"),
        _lead(business_name="Acme Corp", website="https://acme.example"),
    ]

    result = LeadDeduplicator().deduplicate(leads)

    assert result.duplicates_removed == 1
    assert [lead.business_name for lead in result.leads] == ["Acme Corp"]


def test_duplicate_website_folded_for_comparison() -> None:
    leads = [
        _lead(business_name="Acme Corp", website="https://ACME.example"),
        _lead(business_name="Acme Corp", website="https://acme.example/"),
    ]

    result = LeadDeduplicator().deduplicate(leads)

    assert result.duplicates_removed == 1
    assert len(result.leads) == 1


def test_duplicate_phone_removed() -> None:
    leads = [
        _lead(business_name="Acme Corp", phone_number="+12121234567"),
        _lead(business_name="Beta Corp", phone_number="+12121234567"),
    ]

    result = LeadDeduplicator().deduplicate(leads)

    assert result.duplicates_removed == 1
    assert len(result.leads) == 1


def test_duplicate_business_name_and_location_removed() -> None:
    leads = [
        _lead(business_name="Acme Corp", location="New York"),
        _lead(business_name="acme corp", location="  new york "),
    ]

    result = LeadDeduplicator().deduplicate(leads)

    assert result.duplicates_removed == 1
    assert len(result.leads) == 1


def test_same_name_different_location_kept() -> None:
    leads = [
        _lead(business_name="Acme Corp", location="New York"),
        _lead(business_name="Acme Corp", location="London"),
    ]

    result = LeadDeduplicator().deduplicate(leads)

    assert result.duplicates_removed == 0
    assert len(result.leads) == 2


def test_website_takes_priority_over_name() -> None:
    leads = [
        _lead(business_name="Acme Corp", website="https://acme.example"),
        _lead(business_name="Acme Corp", location="New York"),
    ]

    result = LeadDeduplicator().deduplicate(leads)

    assert result.duplicates_removed == 0
    assert len(result.leads) == 2


def test_unique_leads_remain() -> None:
    leads = [
        _lead(business_name="Acme Corp", website="https://acme.example"),
        _lead(business_name="Beta Corp", website="https://beta.example"),
        _lead(business_name="Gamma Corp", website="https://gamma.example"),
    ]

    result = LeadDeduplicator().deduplicate(leads)

    assert result.duplicates_removed == 0
    assert len(result.leads) == 3


def test_lead_without_identity_never_removed() -> None:
    leads = [
        _lead(business_name="Acme Corp"),
        _lead(business_name="Acme Corp"),
    ]

    result = LeadDeduplicator().deduplicate(leads)

    assert result.duplicates_removed == 0
    assert len(result.leads) == 2


def test_first_occurrence_is_kept() -> None:
    leads = [
        _lead(business_name="First", website="https://acme.example"),
        _lead(business_name="Second", website="https://acme.example"),
    ]

    result = LeadDeduplicator().deduplicate(leads)

    assert [lead.business_name for lead in result.leads] == ["First"]
    assert result.removed == ["Second"]


def test_removed_names_are_reported() -> None:
    leads = [
        _lead(business_name="Acme Corp", website="https://acme.example"),
        _lead(business_name="Beta Corp", website="https://acme.example"),
        _lead(business_name="Gamma Corp", website="https://gamma.example"),
    ]

    result = LeadDeduplicator().deduplicate(leads)

    assert result.removed == ["Beta Corp"]
    assert result.duplicates_removed == 1


def test_logs_duplicate_removal(caplog: pytest.LogCaptureFixture) -> None:
    leads = [
        _lead(business_name="Acme Corp", website="https://acme.example"),
        _lead(business_name="Beta Corp", website="https://acme.example"),
    ]

    with caplog.at_level(logging.WARNING):
        LeadDeduplicator().deduplicate(leads)

    messages = [record.message for record in caplog.records]
    assert any("Duplicate detected" in message for message in messages)
    assert any("'Beta Corp'" in message for message in messages)
