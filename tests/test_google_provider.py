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
from tests.fakes import FakeBrowser, FakePage, fake_card


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
    assert ("#searchboxinput", "Enter") in page.presses


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
