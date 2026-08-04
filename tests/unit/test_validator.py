"""Tests for lead validation."""

from app.models.lead import Lead
from app.processing.lead_validator import LeadValidator, ValidationResult


def _lead(**overrides) -> Lead:
    fields = {"business_name": "Acme Corp"}
    fields.update(overrides)
    return Lead(**fields)


def test_valid_email_is_valid() -> None:
    lead = _lead(email="info@acme.example")

    assert LeadValidator().is_valid(lead) is True


def test_invalid_email_is_invalid() -> None:
    lead = _lead(email="not-an-email")

    verdict = LeadValidator().validate(lead)

    assert verdict.is_valid is False
    assert "email" in verdict.reason


def test_email_pattern_checks() -> None:
    validator = LeadValidator()

    assert validator.is_valid_email("info@acme.example") is True
    assert validator.is_valid_email("INFO@ACME.EXAMPLE") is True
    assert validator.is_valid_email("not-an-email") is False
    assert validator.is_valid_email("info@") is False
    assert validator.is_valid_email("@acme.example") is False


def test_valid_url_is_valid() -> None:
    lead = _lead(website="https://acme.example")

    assert LeadValidator().is_valid(lead) is True


def test_valid_url_with_path_is_valid() -> None:
    validator = LeadValidator()

    assert validator.is_valid_website("https://acme.example/about") is True
    assert validator.is_valid_website("http://acme.example:8080/path?q=1") is True


def test_invalid_url_is_invalid() -> None:
    lead = _lead(website="htp://broken.example")

    verdict = LeadValidator().validate(lead)

    assert verdict.is_valid is False
    assert "website" in verdict.reason


def test_url_without_scheme_is_invalid() -> None:
    validator = LeadValidator()

    assert validator.is_valid_website("www.acme.example") is False
    assert validator.is_valid_website("not a url") is False
    assert validator.is_valid_website("https://") is False


def test_valid_phone_is_valid() -> None:
    lead = _lead(phone_number="+12121234567")

    assert LeadValidator().is_valid(lead) is True


def test_phone_pattern_checks() -> None:
    validator = LeadValidator()

    assert validator.is_valid_phone("+12121234567") is True
    assert validator.is_valid_phone("5551234") is True
    assert validator.is_valid_phone("abc123") is False
    assert validator.is_valid_phone("123") is False


def test_invalid_phone_is_invalid() -> None:
    lead = _lead(phone_number="abc")

    verdict = LeadValidator().validate(lead)

    assert verdict.is_valid is False
    assert "phone" in verdict.reason


def test_missing_optional_fields_are_valid() -> None:
    lead = _lead()

    verdict = LeadValidator().validate(lead)

    assert verdict.is_valid is True
    assert lead.email == ""
    assert lead.phone_number == ""
    assert lead.website == ""


def test_blank_location_is_valid() -> None:
    lead = _lead(location="  ")

    assert LeadValidator().is_valid(lead) is True


def test_missing_business_name_is_invalid() -> None:
    lead = _lead(business_name="   ", email="info@acme.example")

    verdict = LeadValidator().validate(lead)

    assert verdict.is_valid is False
    assert "business name" in verdict.reason


def test_rejects_only_the_bad_field() -> None:
    lead = _lead(email="bad-email", website="https://acme.example")

    verdict = LeadValidator().validate(lead)

    assert verdict.is_valid is False
    assert "email" in verdict.reason


def test_validate_returns_validation_result() -> None:
    verdict = LeadValidator().validate(_lead())

    assert isinstance(verdict, ValidationResult)
    assert isinstance(verdict.is_valid, bool)
    assert isinstance(verdict.reason, str)
