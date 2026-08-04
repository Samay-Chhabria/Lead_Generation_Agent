"""End-to-end failure-path tests.

Every failure the user can realistically hit — an unavailable provider, an
unavailable website, a broken browser, a write-protected output directory, or
an invalid prompt — must be contained: the pipeline returns an unsuccessful
ExecutionResult (or continues where appropriate) instead of crashing the
process. A failure at one stage never discards data from earlier stages.
"""

import pytest

from app.exceptions.provider_exception import ProviderSearchError
from app.models.lead import Lead
from app.pipeline.application_pipeline import ApplicationPipeline
from app.providers.provider_factory import ProviderFactory
from app.providers.provider_registry import ProviderRegistry
from app.providers.search_provider import SearchProvider
from tests.conftest import make_settings
from tests.fakes import FakeBrowser, FakePage, build_fixed_factory

PROMPT = "software companies in Karachi"


class FailingInitializeProvider(SearchProvider):
    """Provider whose initialize() raises an unexpected error."""

    name = "fail_init"

    def initialize(self) -> None:
        raise RuntimeError("cannot connect to provider backend")

    def search(self) -> list[str]:
        return []

    def collect_results(self) -> list[object]:
        return []

    def close(self) -> None:
        pass


class FailingSearchProvider(SearchProvider):
    """Provider whose search() raises a documented search error."""

    name = "fail_search"

    def initialize(self) -> None:
        pass

    def search(self) -> list[str]:
        raise ProviderSearchError("search backend unavailable")

    def collect_results(self) -> list[object]:
        return []

    def close(self) -> None:
        pass


class FailingCollectProvider(SearchProvider):
    """Provider whose collect_results() raises a documented search error."""

    name = "fail_collect"

    def initialize(self) -> None:
        pass

    def search(self) -> list[str]:
        return []

    def collect_results(self) -> list[object]:
        raise ProviderSearchError("could not parse results")

    def close(self) -> None:
        pass


class ExplodingProvider(SearchProvider):
    """Provider that raises an unexpected, non-provider exception mid-search."""

    name = "explode"

    def initialize(self) -> None:
        pass

    def search(self) -> list[str]:
        raise RuntimeError("unexpected browser crash")

    def collect_results(self) -> list[object]:
        return []

    def close(self) -> None:
        pass


def _failing_factory(
    tmp_path: pytest.TempPathFactory,
    browser: FakeBrowser,
    provider_class: type[SearchProvider],
) -> tuple[object, ProviderFactory]:
    settings = make_settings(tmp_path, search_provider=provider_class.name)
    registry = ProviderRegistry()
    registry.register(provider_class)
    return settings, ProviderFactory(registry=registry, settings=settings, browser=browser)


def _lead(name: str = "Alpha Corp", website: str = "") -> Lead:
    return Lead(
        business_name=name,
        website=website,
        provider="fixed",
        search_query=PROMPT,
    )


def test_initialization_failure_returns_unsuccessful_and_closes_browser(
    tmp_path: pytest.TempPathFactory, browser: FakeBrowser
) -> None:
    settings, factory = _failing_factory(tmp_path, browser, FailingInitializeProvider)

    result = ApplicationPipeline(settings=settings, factory=factory).execute(PROMPT)

    assert result.success is False
    assert result.excel_output_path is None
    assert result.business_type == "software companies"
    assert browser.close_count == 1


def test_search_failure_returns_unsuccessful(
    tmp_path: pytest.TempPathFactory, browser: FakeBrowser
) -> None:
    settings, factory = _failing_factory(tmp_path, browser, FailingSearchProvider)

    result = ApplicationPipeline(settings=settings, factory=factory).execute(PROMPT)

    assert result.success is False
    assert result.excel_output_path is None
    assert browser.close_count == 1


def test_collect_failure_returns_unsuccessful(
    tmp_path: pytest.TempPathFactory, browser: FakeBrowser
) -> None:
    settings, factory = _failing_factory(tmp_path, browser, FailingCollectProvider)

    result = ApplicationPipeline(settings=settings, factory=factory).execute(PROMPT)

    assert result.success is False
    assert result.excel_output_path is None
    assert browser.close_count == 1


def test_unexpected_exception_returns_unsuccessful_instead_of_crashing(
    tmp_path: pytest.TempPathFactory, browser: FakeBrowser
) -> None:
    settings, factory = _failing_factory(tmp_path, browser, ExplodingProvider)

    result = ApplicationPipeline(settings=settings, factory=factory).execute(PROMPT)

    assert result.success is False
    assert result.excel_output_path is None
    assert browser.close_count == 1


def test_no_internet_keeps_leads_and_completes_run(
    tmp_path: pytest.TempPathFactory,
) -> None:
    settings = make_settings(tmp_path, search_provider="fixed")
    page = FakePage(goto_error=RuntimeError("net::ERR_INTERNET_DISCONNECTED"))
    browser = FakeBrowser(page)
    factory = build_fixed_factory(
        settings,
        browser,
        [_lead("Alpha Corp", website="https://alpha.example")],
    )

    result = ApplicationPipeline(settings=settings, factory=factory).execute(PROMPT)

    assert result.success is True
    assert result.processed_leads == 1
    assert browser.close_count == 1


def test_export_failure_returns_unsuccessful_keeping_plan_context(
    tmp_path: pytest.TempPathFactory, browser: FakeBrowser
) -> None:
    settings = make_settings(tmp_path, search_provider="fixed")
    settings.output_dir.write_bytes(b"not a directory")
    factory = build_fixed_factory(settings, browser, [_lead("Alpha Corp")])

    result = ApplicationPipeline(settings=settings, factory=factory).execute(PROMPT)

    assert result.success is False
    assert result.excel_output_path is None
    assert result.business_type == "software companies"
    assert result.location == "Karachi"
    assert browser.close_count == 1


def test_invalid_prompt_returns_unsuccessful_and_never_launches_browser(
    tmp_path: pytest.TempPathFactory,
) -> None:
    settings = make_settings(tmp_path, search_provider="fixed")

    result = ApplicationPipeline(settings=settings).execute("no location separator here")

    assert result.success is False
    assert result.excel_output_path is None
