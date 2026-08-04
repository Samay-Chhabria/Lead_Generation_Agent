"""Tests for business detail extraction.

The navigator, extractor, and provider extraction workflow are exercised
against fake Playwright pages so no browser or network is used. Missing fields
must become empty strings and a failed business must never stop the remaining
ones (Requirement 7).
"""

import logging
from pathlib import Path

import pytest

from app.config.settings import Settings
from app.exceptions import ExtractionException
from app.extractor.business_detail_extractor import BusinessDetailExtractor
from app.extractor.business_navigator import DETAIL_CONTAINER_SELECTORS, BusinessNavigator
from app.models.business_reference import BusinessReference
from app.models.search_plan import SearchPlan
from app.pipeline.search_pipeline import SearchPipeline
from app.providers.google_maps_provider import GoogleMapsProvider
from app.providers.provider_factory import ProviderFactory
from app.providers.provider_registry import ProviderRegistry
from app.providers.result_collector import BUSINESS_CARD_SELECTORS
from tests.fakes import FakeBrowser, FakeElement, FakePage, fake_card


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        headless=True,
        timeout=2_000,
        max_leads=50,
        search_provider="google_maps",
        browser_type="chromium",
        output_dir=tmp_path / "outputs",
        log_dir=tmp_path / "logs",
        log_level="INFO",
    )


def _plan(max_results: int = 10) -> SearchPlan:
    return SearchPlan(
        original_prompt="software companies in Karachi",
        business_type="software companies",
        location="Karachi",
        provider="google_maps",
        max_results=max_results,
    )


def _reference(
    name: str = "Acme Corp",
    url: str = "https://www.google.com/maps/place/Acme",
    index: int = 0,
) -> BusinessReference:
    return BusinessReference(
        business_id=f"0x1:0x{index + 1}",
        business_name=name,
        listing_url=url,
        listing_index=index,
        provider="google_maps",
    )


def _detail_elements() -> dict[str, list[FakeElement]]:
    return {
        "h1": [FakeElement(text="Acme Corp")],
        'a[href^="tel:"]': [FakeElement(attributes={"href": "tel:+1 555 0100"})],
        '[data-attrid="website"] a': [FakeElement(attributes={"href": "https://acme.example"})],
        '[data-attrid="address"]': [FakeElement(text="Plot 42, Main Avenue, Karachi")],
        'a[href^="mailto:"]': [FakeElement(attributes={"href": "mailto:hello@acme.example"})],
    }


def _detail_elements_without_name() -> dict[str, list[FakeElement]]:
    elements = _detail_elements()
    elements.pop("h1")
    return elements


def _extractor() -> BusinessDetailExtractor:
    return BusinessDetailExtractor()


# --- BusinessDetailExtractor -------------------------------------------------


def test_extracts_complete_business() -> None:
    lead = _extractor().extract(
        FakePage(elements=_detail_elements()),
        _reference(),
        search_query="software companies in Karachi",
    )

    assert lead.business_name == "Acme Corp"
    assert lead.phone_number == "+1 555 0100"
    assert lead.website == "https://acme.example"
    assert lead.location == "Plot 42, Main Avenue, Karachi"
    assert lead.email == "hello@acme.example"
    assert lead.provider == "google_maps"
    assert lead.search_query == "software companies in Karachi"
    assert lead.source_url == "https://www.google.com/maps/place/Acme"


def test_missing_phone_returns_empty_string() -> None:
    elements = _detail_elements()
    elements.pop('a[href^="tel:"]')

    lead = _extractor().extract(FakePage(elements=elements), _reference())

    assert lead.phone_number == ""
    assert lead.email == "hello@acme.example"


def test_missing_website_returns_empty_string() -> None:
    elements = _detail_elements()
    elements.pop('[data-attrid="website"] a')

    lead = _extractor().extract(FakePage(elements=elements), _reference())

    assert lead.website == ""
    assert lead.phone_number == "+1 555 0100"


def test_missing_email_returns_empty_string() -> None:
    elements = _detail_elements()
    elements.pop('a[href^="mailto:"]')

    lead = _extractor().extract(FakePage(elements=elements), _reference())

    assert lead.email == ""
    assert lead.location == "Plot 42, Main Avenue, Karachi"


def test_missing_location_returns_empty_string() -> None:
    elements = _detail_elements()
    elements.pop('[data-attrid="address"]')

    lead = _extractor().extract(FakePage(elements=elements), _reference())

    assert lead.location == ""
    assert lead.website == "https://acme.example"


def test_name_falls_back_to_reference() -> None:
    lead = _extractor().extract(FakePage(), _reference(name="Fallback Name"))

    assert lead.business_name == "Fallback Name"


def test_extractor_never_raises_for_missing_fields() -> None:
    lead = _extractor().extract(FakePage(), _reference())

    assert lead.business_name == "Acme Corp"
    assert lead.phone_number == ""
    assert lead.email == ""
    assert lead.website == ""
    assert lead.location == ""


def test_logs_missing_fields(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        _extractor().extract(FakePage(), _reference())

    messages = [record.message for record in caplog.records]
    assert any("Missing phone." in message for message in messages)
    assert any("Missing website." in message for message in messages)
    assert any("Missing email." in message for message in messages)
    assert any("Missing location." in message for message in messages)
    assert any("Business extracted." in message for message in messages)
    assert any("Extraction complete." in message for message in messages)


# --- BusinessNavigator -------------------------------------------------------


def test_navigator_opens_listing_and_returns_page(settings: Settings) -> None:
    page = FakePage()

    result = BusinessNavigator(settings=settings).open(_reference(), page)

    assert result is page
    assert page.visited_url == "https://www.google.com/maps/place/Acme"


def test_navigator_raises_when_listing_has_no_url(settings: Settings) -> None:
    with pytest.raises(ExtractionException):
        BusinessNavigator(settings=settings).open(_reference(url=None), FakePage())


def test_navigator_raises_on_navigation_failure(settings: Settings) -> None:
    page = FakePage(goto_error=TimeoutError("net::ERR_CONNECTION_TIMED_OUT"))

    with pytest.raises(ExtractionException):
        BusinessNavigator(settings=settings).open(_reference(), page)


def test_navigator_raises_when_details_never_load(settings: Settings) -> None:
    page = FakePage(missing=set(DETAIL_CONTAINER_SELECTORS))

    with pytest.raises(ExtractionException):
        BusinessNavigator(settings=settings).open(_reference(), page)


# --- GoogleMapsProvider extraction workflow ----------------------------------


def test_provider_extracts_leads_after_search(settings: Settings) -> None:
    page = FakePage(
        cards=[fake_card("Acme Corp", "https://www.google.com/maps/place/Acme", "0x1:0x1")],
        card_selectors=set(BUSINESS_CARD_SELECTORS),
        elements=_detail_elements(),
    )
    provider = GoogleMapsProvider(browser=FakeBrowser(page), plan=_plan(), settings=settings)
    provider.initialize()

    provider.search()

    assert len(provider.leads) == 1
    lead = provider.leads[0]
    assert lead.business_name == "Acme Corp"
    assert lead.phone_number == "+1 555 0100"
    assert lead.website == "https://acme.example"
    assert lead.location == "Plot 42, Main Avenue, Karachi"
    assert lead.email == "hello@acme.example"
    assert lead.provider == "google_maps"
    assert lead.search_query == "software companies in Karachi"
    assert lead.source_url == "https://www.google.com/maps/place/Acme"


def test_provider_continues_after_failures(
    settings: Settings,
    caplog: pytest.LogCaptureFixture,
) -> None:
    cards = [
        fake_card("Acme Corp", "https://www.google.com/maps/place/Acme", "0x1:0x1"),
        fake_card("Gone Ltd", "https://www.google.com/maps/place/Gone", "0x1:0x2"),
        fake_card("Beta Co", "https://www.google.com/maps/place/Beta", "0x1:0x3"),
    ]
    page = FakePage(
        cards=cards,
        card_selectors=set(BUSINESS_CARD_SELECTORS),
        elements=_detail_elements_without_name(),
        goto_errors={"https://www.google.com/maps/place/Gone": TimeoutError("listing removed")},
    )
    provider = GoogleMapsProvider(browser=FakeBrowser(page), plan=_plan(), settings=settings)
    provider.initialize()

    with caplog.at_level(logging.INFO):
        provider.search()

    assert [lead.business_name for lead in provider.leads] == ["Acme Corp", "Beta Co"]
    assert provider.leads[0].phone_number == "+1 555 0100"
    messages = [record.message for record in caplog.records]
    assert any("skipping" in message for message in messages)
    assert any("3 businesses processed." in message for message in messages)


def test_fifty_business_extraction_run(settings: Settings) -> None:
    cards = [
        fake_card(f"Business {i}", f"https://www.google.com/maps/place/B{i}", f"0x1:0x{i}")
        for i in range(50)
    ]
    page = FakePage(
        cards=cards,
        card_selectors=set(BUSINESS_CARD_SELECTORS),
        elements=_detail_elements_without_name(),
    )
    provider = GoogleMapsProvider(
        browser=FakeBrowser(page), plan=_plan(max_results=50), settings=settings
    )
    provider.initialize()

    provider.search()

    assert len(provider.references) == 50
    assert len(provider.leads) == 50
    assert provider.leads[49].business_name == "Business 49"
    assert provider.leads[49].phone_number == "+1 555 0100"


def test_provider_logs_extraction_steps(
    settings: Settings,
    caplog: pytest.LogCaptureFixture,
) -> None:
    page = FakePage(
        cards=[fake_card("Acme Corp", "https://www.google.com/maps/place/Acme", "0x1:0x1")],
        card_selectors=set(BUSINESS_CARD_SELECTORS),
        elements=_detail_elements_without_name(),
    )
    provider = GoogleMapsProvider(browser=FakeBrowser(page), plan=_plan(), settings=settings)
    provider.initialize()

    with caplog.at_level(logging.INFO):
        provider.search()

    messages = [record.message for record in caplog.records]
    assert any("1 businesses discovered." in message for message in messages)
    assert any("Opening Business 1." in message for message in messages)
    assert any("Business opened." in message for message in messages)
    assert any("Business extracted successfully." in message for message in messages)
    assert any("1 businesses processed." in message for message in messages)


# --- SearchPipeline ----------------------------------------------------------


def test_pipeline_returns_leads(settings: Settings) -> None:
    page = FakePage(
        cards=[fake_card("Acme Corp", "https://www.google.com/maps/place/Acme", "0x1:0x1")],
        card_selectors=set(BUSINESS_CARD_SELECTORS),
        elements=_detail_elements(),
    )
    registry = ProviderRegistry()
    registry.register(GoogleMapsProvider)
    factory = ProviderFactory(registry=registry, settings=settings, browser=FakeBrowser(page))
    pipeline = SearchPipeline(factory=factory)

    result = pipeline.run(_plan())

    assert result.success is True
    assert result.lead_count == 1
    assert result.leads[0].business_name == "Acme Corp"
    assert result.leads[0].phone_number == "+1 555 0100"
    assert result.leads[0].search_query == "software companies in Karachi"
