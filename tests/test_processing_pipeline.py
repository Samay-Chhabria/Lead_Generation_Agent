"""Tests for the full data processing pipeline."""

import logging

import pytest

from app.models.lead import Lead
from app.processing.processing_pipeline import ProcessingPipeline, ProcessingResult


def _lead(**overrides) -> Lead:
    fields = {"business_name": "Acme Corp"}
    fields.update(overrides)
    return Lead(**fields)


def test_pipeline_normalizes_leads() -> None:
    leads = [_lead(business_name="  Acme   Corp ", phone_number="+1 (212) 123-4567")]

    result = ProcessingPipeline().process(leads)

    assert result.leads[0].business_name == "Acme Corp"
    assert result.leads[0].phone_number == "+12121234567"


def test_pipeline_removes_duplicates() -> None:
    leads = [
        _lead(business_name="Acme Corp", website="https://acme.example"),
        _lead(business_name="Acme Corp", website="https://acme.example"),
        _lead(business_name="Beta Corp", website="https://beta.example"),
    ]

    result = ProcessingPipeline().process(leads)

    assert result.duplicates_removed == 1
    assert [lead.business_name for lead in result.leads] == ["Acme Corp", "Beta Corp"]


def test_pipeline_drops_invalid_leads_and_continues() -> None:
    leads = [
        _lead(business_name="   "),
        _lead(business_name="Acme Corp", website="https://acme.example"),
    ]

    result = ProcessingPipeline().process(leads)

    assert result.invalid_count == 1
    assert result.valid_count == 1
    assert [lead.business_name for lead in result.leads] == ["Acme Corp"]


def test_pipeline_never_crashes_on_missing_data() -> None:
    leads = [
        _lead(),
        _lead(business_name="Beta Corp"),
        _lead(business_name="Gamma Corp", website="", email="", phone_number="", location=""),
    ]

    result = ProcessingPipeline().process(leads)

    assert result.valid_count == 3
    assert len(result.leads) == 3


def test_pipeline_handles_unexpected_values() -> None:
    leads: list[Lead] = [_lead(business_name="Acme Corp")]
    result = ProcessingPipeline().process(leads + [None])  # type: ignore[list-item]

    assert result.invalid_count == 1
    assert len(result.leads) == 1
    assert result.leads[0].business_name == "Acme Corp"


def test_pipeline_empty_input() -> None:
    result = ProcessingPipeline().process([])

    assert isinstance(result, ProcessingResult)
    assert result.input_count == 0
    assert result.valid_count == 0
    assert result.invalid_count == 0
    assert result.duplicates_removed == 0
    assert result.final_count == 0
    assert result.leads == []


def test_pipeline_statistics() -> None:
    leads = [
        _lead(business_name="Acme Corp", website="https://acme.example"),
        _lead(business_name="Duplicate", website="https://acme.example"),
        _lead(business_name="   "),
        _lead(business_name="Beta Corp", website="https://beta.example"),
    ]

    result = ProcessingPipeline().process(leads)

    assert result.input_count == 4
    assert result.valid_count == 3
    assert result.invalid_count == 1
    assert result.duplicates_removed == 1
    assert result.final_count == 2


def test_pipeline_expected_output_fifty_leads() -> None:
    leads: list[Lead] = []
    for index in range(43):
        leads.append(
            _lead(
                business_name=f"Business {index}",
                website=f"https://site{index}.example",
            )
        )
    for index in range(7):
        leads.append(
            _lead(
                business_name=f"Duplicate {index}",
                website=f"https://site{index}.example",
            )
        )

    result = ProcessingPipeline().process(leads)

    assert result.input_count == 50
    assert result.valid_count == 50
    assert result.invalid_count == 0
    assert result.duplicates_removed == 7
    assert result.final_count == 43


def test_pipeline_logs_lifecycle(caplog: pytest.LogCaptureFixture) -> None:
    leads = [
        _lead(business_name="Acme Corp", website="https://acme.example"),
        _lead(business_name="Duplicate", website="https://acme.example"),
        _lead(business_name="   "),
    ]

    with caplog.at_level(logging.INFO):
        ProcessingPipeline().process(leads)

    messages = [record.message for record in caplog.records]
    assert any("Processing started" in message for message in messages)
    assert any("Normalization started" in message for message in messages)
    assert any("Validation started" in message for message in messages)
    assert any("Deduplication started" in message for message in messages)
    assert any("Processing completed" in message for message in messages)
    assert any("Lead removed" in message for message in messages)
    assert any("Duplicate detected" in message for message in messages)
    assert any("Input leads: 3" in message for message in messages)
    assert any("valid leads: 2" in message for message in messages)
    assert any("duplicates removed: 1" in message for message in messages)
    assert any("final leads: 1" in message for message in messages)
