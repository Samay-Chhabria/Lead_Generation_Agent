"""Tests for lead normalization."""

from app.models.lead import Lead
from app.processing.lead_normalizer import LeadNormalizer


def _lead(**overrides) -> Lead:
    fields = {"business_name": "Acme Corp"}
    fields.update(overrides)
    return Lead(**fields)


def test_trims_leading_and_trailing_whitespace() -> None:
    lead = LeadNormalizer().normalize(_lead(business_name="  Acme Corp  "))

    assert lead.business_name == "Acme Corp"


def test_collapses_repeated_whitespace() -> None:
    lead = LeadNormalizer().normalize(_lead(business_name="Acme   Corp\tLtd"))

    assert lead.business_name == "Acme Corp Ltd"


def test_blank_name_becomes_empty_string() -> None:
    lead = LeadNormalizer().normalize(_lead(business_name="   "))

    assert lead.business_name == ""


def test_lowercases_email() -> None:
    lead = LeadNormalizer().normalize(_lead(email="  INFO@ABC.COM "))

    assert lead.email == "info@abc.com"


def test_trims_email_whitespace() -> None:
    lead = LeadNormalizer().normalize(_lead(email="  sales@acme.example  "))

    assert lead.email == "sales@acme.example"


def test_normalizes_phone_format() -> None:
    lead = LeadNormalizer().normalize(_lead(phone_number="+1 (212) 123-4567"))

    assert lead.phone_number == "+12121234567"


def test_phone_without_country_code_stays_digits() -> None:
    lead = LeadNormalizer().normalize(_lead(phone_number="555-1234"))

    assert lead.phone_number == "5551234"


def test_phone_without_digits_becomes_empty() -> None:
    lead = LeadNormalizer().normalize(_lead(phone_number="N/A"))

    assert lead.phone_number == ""


def test_website_removes_trailing_slash() -> None:
    lead = LeadNormalizer().normalize(_lead(website="https://abc.com/"))

    assert lead.website == "https://abc.com"


def test_website_lowercases_scheme_and_host() -> None:
    lead = LeadNormalizer().normalize(_lead(website="HTTP://ABC.COM/"))

    assert lead.website == "http://abc.com"


def test_website_preserves_path_case() -> None:
    lead = LeadNormalizer().normalize(_lead(website="https://Acme.Example/Blog/Post/"))

    assert lead.website == "https://acme.example/Blog/Post"


def test_website_without_scheme_kept_as_is() -> None:
    lead = LeadNormalizer().normalize(_lead(website="  www.Acme.Example/  "))

    assert lead.website == "www.Acme.Example"


def test_location_whitespace_collapsed() -> None:
    lead = LeadNormalizer().normalize(_lead(location="  New   York,   NY "))

    assert lead.location == "New York, NY"


def test_none_values_become_empty_strings() -> None:
    lead = LeadNormalizer().normalize(
        _lead(phone_number=None, email=None, website=None, location=None)
    )

    assert lead.phone_number == ""
    assert lead.email == ""
    assert lead.website == ""
    assert lead.location == ""


def test_missing_optional_fields_remain_empty() -> None:
    lead = LeadNormalizer().normalize(_lead())

    assert lead.business_name == "Acme Corp"
    assert lead.phone_number == ""
    assert lead.email == ""
    assert lead.website == ""
    assert lead.location == ""


def test_normalize_preserves_unrelated_fields() -> None:
    original = _lead(
        email="INFO@ABC.COM",
        provider="google_maps",
        search_query="software companies in Karachi",
        source_url="https://www.google.com/maps/place/Acme",
    )
    normalized = LeadNormalizer().normalize(original)

    assert normalized.provider == "google_maps"
    assert normalized.search_query == "software companies in Karachi"
    assert normalized.source_url == "https://www.google.com/maps/place/Acme"
    assert normalized.collected_at is original.collected_at


def test_normalize_returns_new_lead_and_keeps_original_untouched() -> None:
    original = _lead(phone_number="+1 (212) 123-4567")
    normalized = LeadNormalizer().normalize(original)

    assert normalized is not original
    assert original.phone_number == "+1 (212) 123-4567"
    assert normalized.phone_number == "+12121234567"
