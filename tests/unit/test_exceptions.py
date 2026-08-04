"""Tests for the exception hierarchy and scaffold contracts."""

from pathlib import Path

import pytest

from app.browser.browser_manager import BrowserManager
from app.exceptions import (
    BrowserException,
    ExportException,
    ExtractionException,
    LeadGenerationError,
    ParserException,
)
from app.exporter.excel_exporter import ExcelExporter
from app.exporter.file_manager import FileManager
from app.extractor.lead_extractor import LeadExtractor
from app.validator.validator import Validator


def test_exceptions_share_common_base() -> None:
    assert issubclass(ParserException, LeadGenerationError)
    assert issubclass(BrowserException, LeadGenerationError)
    assert issubclass(ExtractionException, LeadGenerationError)
    assert issubclass(ExportException, LeadGenerationError)


def test_parser_exception_is_raiseable() -> None:
    with pytest.raises(ParserException):
        raise ParserException("invalid prompt")


def test_export_exception_is_raiseable() -> None:
    with pytest.raises(ExportException):
        raise ExportException("workbook could not be saved")


def test_browser_manager_starts_idle() -> None:
    assert not BrowserManager().is_running()


def test_lead_extractor_is_scaffolded() -> None:
    with pytest.raises(NotImplementedError):
        LeadExtractor().extract("<html></html>")


def test_validator_is_scaffolded() -> None:
    from app.models.lead import Lead

    with pytest.raises(NotImplementedError):
        Validator().validate(Lead(business_name="Acme"))


def test_excel_exporter_is_implemented(tmp_path: Path) -> None:
    path = ExcelExporter(file_manager=FileManager(tmp_path)).export([], "coffee shops", "america")

    assert path.exists()
    assert path.suffix == ".xlsx"
