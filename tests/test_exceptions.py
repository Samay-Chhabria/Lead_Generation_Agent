"""Tests for the exception hierarchy and scaffold contracts."""

import pytest

from app.browser.browser_manager import BrowserManager
from app.exceptions import (
    BrowserException,
    ExtractionException,
    LeadGenerationError,
    ParserException,
)
from app.exporter.excel_exporter import ExcelExporter
from app.extractor.lead_extractor import LeadExtractor
from app.validator.validator import Validator


def test_exceptions_share_common_base() -> None:
    assert issubclass(ParserException, LeadGenerationError)
    assert issubclass(BrowserException, LeadGenerationError)
    assert issubclass(ExtractionException, LeadGenerationError)


def test_parser_exception_is_raiseable() -> None:
    with pytest.raises(ParserException):
        raise ParserException("invalid prompt")


def test_browser_manager_starts_idle() -> None:
    assert not BrowserManager().is_running()


def test_lead_extractor_is_scaffolded() -> None:
    with pytest.raises(NotImplementedError):
        LeadExtractor().extract("<html></html>")


def test_validator_is_scaffolded() -> None:
    from app.models.lead import Lead

    with pytest.raises(NotImplementedError):
        Validator().validate(Lead(business_name="Acme"))


def test_excel_exporter_is_scaffolded() -> None:
    with pytest.raises(NotImplementedError):
        ExcelExporter().export([], "output.xlsx")
