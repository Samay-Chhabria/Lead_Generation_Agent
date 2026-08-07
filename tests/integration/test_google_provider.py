"""Tests for the Google Maps search provider.

The provider is exercised against a fake Playwright page/browser so the tests
never touch the network or launch a real browser. The fakes record interactions
and can be configured to simulate missing elements, timeouts, and navigation
failures.
"""

import logging
from pathlib import Path

import pytest

from app.config.settings import Settings
from app.exceptions.provider_exception import (
    ProviderElementNotFoundError,
    ProviderNavigationError,
    ProviderSearchError,
)
from app.models.search_plan import SearchPlan
from app.pipeline.search_pipeline import SearchPipeline
from app.providers.google_maps_provider import (
    GOOGLE_MAPS_URL,
    RESULTS_CONTAINER_SELECTORS,
    SEARCH_INPUT_SELECTORS,
    GoogleMapsProvider,
)
from app.providers.provider_factory import ProviderFactory
from app.providers.provider_registry import ProviderRegistry
from app.providers.provider_result import ProviderResult
from app.providers.result_collector import BUSINESS_CARD_SELECTORS
from tests.fakes import FakeBrowser, FakeElement, FakePage, fake_card


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        headless=True,
        timeout=2_000,
        max_leads=10,
        search_provider="google_maps",
        browser_type="chromium",
        output_dir=tmp_path / "outputs",
        log_dir=tmp_path / "logs",
        log_level="INFO",
    )


def _plan(provider: str = "google_maps") -> SearchPlan:
    return SearchPlan(
        original_prompt="software companies in Karachi",
        business_type="software companies",
        location="Karachi",
        provider=provider,
        max_results=10,
    )


def _provider(
    settings: Settings,
    browser: FakeBrowser,
    plan: SearchPlan | None = None,
) -> GoogleMapsProvider:
    return GoogleMapsProvider(browser=browser, plan=plan or _plan(), settings=settings)


def test_query_is_built_from_plan(settings: Settings) -> None:
    provider = _provider(settings, FakeBrowser())

    assert provider.query == "software companies in Karachi"


def test_query_omits_location_when_absent(settings: Settings) -> None:
    plan = SearchPlan(
        original_prompt="restaurants",
        business_type="restaurants",
        location=None,
        provider="google_maps",
        max_results=5,
    )
    provider = _provider(settings, FakeBrowser(), plan=plan)

    assert provider.query == "restaurants"


def test_initialize_launches_browser_and_configures_page(settings: Settings) -> None:
    browser = FakeBrowser()
    provider = _provider(settings, browser)

    provider.initialize()

    assert provider.page is browser.page
    assert browser.page.default_timeout == settings.timeout
    assert browser.launch_count == 1


def test_initialize_reuses_running_browser(settings: Settings) -> None:
    browser = FakeBrowser()
    browser.launch()
    provider = _provider(settings, browser)

    provider.initialize()

    assert browser.launch_count == 1


def test_search_opens_maps_and_submits_query(settings: Settings) -> None:
    page = FakePage()
    provider = _provider(settings, FakeBrowser(page))
    provider.initialize()

    links = provider.search()

    assert links == []
    assert page.visited_url == GOOGLE_MAPS_URL
    assert ("#searchboxinput", "software companies in Karachi") in page.fills
    assert "Enter" in page.pressed_keys


def test_collect_results_verifies_results_loaded(settings: Settings) -> None:
    provider = _provider(settings, FakeBrowser())
    provider.initialize()
    provider.search()

    assert provider.collect_results() == []


def test_search_collects_business_references(settings: Settings) -> None:
    page = FakePage(
        cards=[
            fake_card("Alpha Corp", "https://www.google.com/maps/place/Alpha", "0x1:0x1"),
            fake_card("Beta Ltd", "https://www.google.com/maps/place/Beta", "0x1:0x2"),
            fake_card("Gamma Co", "https://www.google.com/maps/place/Gamma", "0x1:0x3"),
        ],
        card_selectors=set(BUSINESS_CARD_SELECTORS),
    )
    provider = _provider(settings, FakeBrowser(page))
    provider.initialize()

    provider.search()

    assert len(provider.references) == 3
    assert provider.references[0].business_name == "Alpha Corp"
    assert provider.references[0].business_id == "0x1:0x1"
    assert provider.references[0].listing_url == "https://www.google.com/maps/place/Alpha"
    assert provider.references[0].provider == "google_maps"


def test_close_releases_page(settings: Settings) -> None:
    browser = FakeBrowser()
    provider = _provider(settings, browser)
    provider.initialize()

    provider.close()

    assert provider.page is None
    assert browser.page.is_closed()


def _signal_card(
    name: str,
    url: str,
    rating: str,
    reviews: str,
    website: bool = False,
    verified: bool = False,
) -> FakeElement:
    attributes = {
        "aria-label": name,
        "href": url,
        "data-rating": rating,
        "data-reviews": reviews,
    }
    if website:
        attributes["data-website"] = "1"
    if verified:
        attributes["data-verified"] = "1"
    return FakeElement(attributes)


def test_selects_top_businesses_before_extraction(settings: Settings) -> None:
    cards = [
        _signal_card("B0", "https://www.google.com/maps/place/B0", "4.0", "10"),
        _signal_card("B1", "https://www.google.com/maps/place/B1", "4.3", "20"),
        _signal_card(
            "B2", "https://www.google.com/maps/place/B2", "4.9", "300", website=True, verified=True
        ),
        _signal_card("B3", "https://www.google.com/maps/place/B3", "4.7", "150"),
    ]
    page = FakePage(cards=cards, card_selectors=set(BUSINESS_CARD_SELECTORS))
    plan = SearchPlan(
        original_prompt="software companies in Karachi",
        business_type="software companies",
        location="Karachi",
        provider="google_maps",
        max_results=2,
    )
    provider = _provider(settings, FakeBrowser(page), plan=plan)
    provider.initialize()

    provider.search()

    assert [r.business_name for r in provider.references] == ["B2", "B3"]


def test_selects_only_as_many_as_requested(settings: Settings) -> None:
    page = FakePage(
        cards=[
            fake_card(f"Business {i}", f"https://www.google.com/maps/place/B{i}") for i in range(8)
        ],
        card_selectors=set(BUSINESS_CARD_SELECTORS),
    )
    plan = SearchPlan(
        original_prompt="coffee shops in Karachi",
        business_type="coffee shops",
        location="Karachi",
        provider="google_maps",
        max_results=5,
    )
    provider = _provider(settings, FakeBrowser(page), plan=plan)
    provider.initialize()

    provider.search()

    assert len(provider.references) == 5


def test_logs_ranking_selection_and_extraction(
    caplog: pytest.LogCaptureFixture, settings: Settings
) -> None:
    page = FakePage(
        cards=[
            fake_card(f"Business {i}", f"https://www.google.com/maps/place/B{i}") for i in range(6)
        ],
        card_selectors=set(BUSINESS_CARD_SELECTORS),
    )
    plan = SearchPlan(
        original_prompt="coffee shops in Karachi",
        business_type="coffee shops",
        location="Karachi",
        provider="google_maps",
        max_results=5,
    )
    provider = _provider(settings, FakeBrowser(page), plan=plan)
    provider.initialize()

    with caplog.at_level(logging.INFO):
        provider.search()

    messages = [record.message for record in caplog.records]
    assert any("Default result limit: 5." in message for message in messages)
    assert any("Ranking businesses..." in message for message in messages)
    assert any("Selected top 5 businesses." in message for message in messages)
    assert any("Beginning extraction..." in message for message in messages)


def test_logs_custom_result_limit_when_requested(
    caplog: pytest.LogCaptureFixture, settings: Settings
) -> None:
    page = FakePage(card_selectors=set(BUSINESS_CARD_SELECTORS))
    plan = SearchPlan(
        original_prompt="find 3 coffee shops in Karachi",
        business_type="find 3 coffee shops",
        location="Karachi",
        provider="google_maps",
        max_results=3,
    )
    provider = _provider(settings, FakeBrowser(page), plan=plan)
    provider.initialize()

    with caplog.at_level(logging.INFO):
        provider.search()

    messages = [record.message for record in caplog.records]
    assert any("Result limit: 3." in message for message in messages)


def test_search_before_initialize_raises(settings: Settings) -> None:
    provider = _provider(settings, FakeBrowser())

    with pytest.raises(ProviderSearchError):
        provider.search()


def test_missing_search_input_raises(settings: Settings) -> None:
    page = FakePage(missing=set(SEARCH_INPUT_SELECTORS))
    provider = _provider(settings, FakeBrowser(page))
    provider.initialize()

    with pytest.raises(ProviderElementNotFoundError):
        provider.search()


def test_missing_results_raises(settings: Settings) -> None:
    page = FakePage(missing=set(RESULTS_CONTAINER_SELECTORS))
    provider = _provider(settings, FakeBrowser(page))
    provider.initialize()

    with pytest.raises(ProviderSearchError):
        provider.search()


def test_search_box_falls_back_to_name_q_when_canonical_inputs_missing(settings: Settings) -> None:
    """Regression: the real input on lightweight Maps is input[name="q"]; when
    #searchboxinput and the aria-label input are absent, the layered strategy
    must still resolve and type into the surviving input."""
    missing = {selector for selector in SEARCH_INPUT_SELECTORS if selector != 'input[name="q"]'}
    page = FakePage(missing=missing)
    provider = _provider(settings, FakeBrowser(page))
    provider.initialize()

    provider.search()

    assert ('input[name="q"]', "software companies in Karachi") in page.fills
    assert "Enter" in page.pressed_keys


def test_search_box_skips_hidden_and_not_editable_candidates(settings: Settings) -> None:
    """Regression: a matched-but-hidden or read-only search input must not be
    selected; the provider keeps trying every strategy until an editable one is
    found."""
    page = FakePage(hidden={"#searchboxinput", 'input[aria-label="Search Google Maps"]'})
    provider = _provider(settings, FakeBrowser(page))
    provider.initialize()

    provider.search()

    assert any('input[role="combobox"]' in selector for selector, _ in page.fills)


def test_fill_failure_triggers_typing_fallback(settings: Settings) -> None:
    """Regression: a stale locator makes fill() raise. The provider must not
    abort or retry the same fill; it re-resolves the box and types the query via
    click -> Ctrl+A -> type(delay=40) -> Enter."""
    page = FakePage(fill_errors={"#searchboxinput"})
    provider = _provider(settings, FakeBrowser(page))
    provider.initialize()

    provider.search()

    assert len(page.fills) == 1
    assert ("#searchboxinput", "software companies in Karachi") in page.fills
    assert "#searchboxinput" in page.clicks
    assert ("#searchboxinput", "Control+A") in page.presses
    assert ("#searchboxinput", "software companies in Karachi", 40) in page.typed
    assert ("#searchboxinput", "Enter") in page.presses


def test_ensure_fillable_logs_why_it_rejects(
    caplog: pytest.LogCaptureFixture, settings: Settings
) -> None:
    page = FakePage(not_editable={"#searchboxinput"})
    provider = _provider(settings, FakeBrowser(page))

    with caplog.at_level(logging.WARNING):
        assert provider._ensure_fillable(page, page.locator("#searchboxinput")) is False

    messages = [record.message for record in caplog.records]
    assert any("not editable" in message for message in messages)


def test_ensure_fillable_rejects_hidden_when_logging_reason(
    caplog: pytest.LogCaptureFixture, settings: Settings
) -> None:
    page = FakePage(hidden={"#searchboxinput"})
    provider = _provider(settings, FakeBrowser(page))

    with caplog.at_level(logging.WARNING):
        assert provider._ensure_fillable(page, page.locator("#searchboxinput")) is False

    messages = [record.message for record in caplog.records]
    assert any("not visible" in message for message in messages)


def test_navigation_failure_raises(settings: Settings) -> None:
    page = FakePage(goto_error=TimeoutError("net::ERR_CONNECTION_TIMED_OUT"))
    provider = _provider(settings, FakeBrowser(page))
    provider.initialize()

    with pytest.raises(ProviderNavigationError):
        provider.search()


def test_provider_logs_search_steps(caplog: pytest.LogCaptureFixture, settings: Settings) -> None:
    provider = _provider(settings, FakeBrowser())
    provider.initialize()

    with caplog.at_level(logging.INFO):
        provider.search()

    messages = [record.message for record in caplog.records]
    assert any("Opening Google Maps." in message for message in messages)
    assert any("Google Maps opened." in message for message in messages)
    assert any("Searching software companies in Karachi" in message for message in messages)
    assert any("Waiting for results..." in message for message in messages)
    assert any("Results loaded successfully." in message for message in messages)
    assert any("Collecting business references..." in message for message in messages)
    assert any("Business references collected" in message for message in messages)
    assert any("Total 0 business references." in message for message in messages)
    assert any("Search completed." in message for message in messages)


def test_pipeline_runs_provider_and_returns_result(settings: Settings) -> None:
    page = FakePage(
        cards=[
            fake_card("Alpha Corp", "https://www.google.com/maps/place/Alpha", "0x1:0x1"),
            fake_card("Beta Ltd", "https://www.google.com/maps/place/Beta", "0x1:0x2"),
        ],
        card_selectors=set(BUSINESS_CARD_SELECTORS),
    )
    registry = ProviderRegistry()
    registry.register(GoogleMapsProvider)
    factory = ProviderFactory(
        registry=registry,
        settings=settings,
        browser=FakeBrowser(page),
    )
    pipeline = SearchPipeline(factory=factory)

    result = pipeline.run(_plan())

    assert isinstance(result, ProviderResult)
    assert result.success is True
    assert result.query == "software companies in Karachi"
    assert result.provider_name == "google_maps"
    assert result.business_links == []
    assert result.raw_results == result.business_references
    assert result.execution_time >= 0.0
    assert result.raw_page_reference is page
    assert result.metadata["provider"] == "google_maps"
    assert result.business_count == 2
    assert [r.business_name for r in result.business_references] == ["Alpha Corp", "Beta Ltd"]


def test_pipeline_closes_browser(settings: Settings) -> None:
    browser = FakeBrowser()
    registry = ProviderRegistry()
    registry.register(GoogleMapsProvider)
    factory = ProviderFactory(registry=registry, settings=settings, browser=browser)
    pipeline = SearchPipeline(factory=factory)

    pipeline.run(_plan())

    assert browser.close_count == 1
