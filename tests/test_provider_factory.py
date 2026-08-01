"""Tests for the provider factory and the search pipeline."""

import logging
from pathlib import Path
from typing import Any

import pytest

from app.browser.browser_manager import BrowserManager
from app.config.settings import Settings
from app.exceptions.provider_exception import (
    ProviderInitializationError,
    UnknownProviderError,
)
from app.models.search_plan import SearchPlan
from app.pipeline.search_pipeline import SearchPipeline
from app.providers.google_maps_provider import GoogleMapsProvider
from app.providers.provider_factory import ProviderFactory
from app.providers.provider_registry import ProviderRegistry
from app.providers.provider_result import ProviderResult
from app.providers.search_provider import SearchProvider


class DummyProvider(SearchProvider):
    name = "dummy"


class RecordingProvider(SearchProvider):
    name = "recording"
    instances: list["RecordingProvider"] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.calls: list[str] = []
        RecordingProvider.instances.append(self)

    def initialize(self) -> None:
        self.calls.append("initialize")
        super().initialize()

    def search(self) -> list[str]:
        self.calls.append("search")
        return []

    def collect_results(self) -> list[Any]:
        self.calls.append("collect_results")
        return []

    def close(self) -> None:
        self.calls.append("close")


class FailingProvider(SearchProvider):
    name = "failing"

    def initialize(self) -> None:
        raise RuntimeError("cannot connect")


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        headless=True,
        timeout=30_000,
        max_leads=25,
        search_provider="google",
        browser_type="chromium",
        output_dir=tmp_path / "outputs",
        log_dir=tmp_path / "logs",
        log_level="INFO",
    )


def _plan(provider: str = "dummy") -> SearchPlan:
    return SearchPlan(
        original_prompt="coffee shops in America",
        business_type="coffee shops",
        location="America",
        provider=provider,
        max_results=10,
    )


def _registry(*provider_classes: type[SearchProvider]) -> ProviderRegistry:
    registry = ProviderRegistry()
    for provider_class in provider_classes:
        registry.register(provider_class)
    return registry


def test_factory_creates_provider_from_plan(settings: Settings) -> None:
    factory = ProviderFactory(registry=_registry(DummyProvider), settings=settings)

    provider = factory.create(_plan())

    assert isinstance(provider, DummyProvider)
    assert provider.plan.provider == "dummy"


def test_factory_injects_dependencies(settings: Settings) -> None:
    browser = BrowserManager(settings=settings)
    logger = logging.getLogger("tests.provider_factory")
    factory = ProviderFactory(
        registry=_registry(DummyProvider),
        settings=settings,
        logger=logger,
        browser=browser,
    )

    provider = factory.create(_plan())

    assert provider.browser is browser
    assert provider.plan is not None
    assert provider.settings is settings
    assert provider.logger is logger


def test_factory_raises_for_unknown_provider(settings: Settings) -> None:
    factory = ProviderFactory(registry=_registry(DummyProvider), settings=settings)

    with pytest.raises(UnknownProviderError):
        factory.create(_plan(provider="missing"))


def test_factory_uses_default_registry(settings: Settings) -> None:
    factory = ProviderFactory(settings=settings)

    provider = factory.create(_plan(provider="google"))

    assert isinstance(provider, GoogleMapsProvider)


def test_factory_resolves_placeholder_names_to_search_provider(settings: Settings) -> None:
    factory = ProviderFactory(settings=settings)

    provider = factory.create(_plan(provider="yelp"))

    assert isinstance(provider, SearchProvider)


def test_pipeline_returns_placeholder_result(settings: Settings) -> None:
    factory = ProviderFactory(
        registry=_registry(RecordingProvider),
        settings=settings,
    )
    pipeline = SearchPipeline(factory=factory)

    result = pipeline.run(_plan(provider="recording"))

    assert isinstance(result, ProviderResult)
    assert result.business_links == []
    assert result.raw_results == []
    assert result.execution_time >= 0.0
    assert result.metadata["provider"] == "recording"


def test_pipeline_calls_provider_lifecycle_in_order(settings: Settings) -> None:
    RecordingProvider.instances.clear()
    factory = ProviderFactory(
        registry=_registry(RecordingProvider),
        settings=settings,
    )
    pipeline = SearchPipeline(factory=factory)

    pipeline.run(_plan(provider="recording"))

    provider = RecordingProvider.instances[0]
    assert provider.calls == ["initialize", "search", "collect_results", "close"]


def test_pipeline_logs_initialization(caplog: pytest.LogCaptureFixture, settings: Settings) -> None:
    factory = ProviderFactory(
        registry=_registry(RecordingProvider),
        settings=settings,
    )
    pipeline = SearchPipeline(factory=factory)

    with caplog.at_level(logging.INFO):
        pipeline.run(_plan(provider="recording"))

    messages = [record.message for record in caplog.records]
    assert any("Search pipeline initialized." in message for message in messages)
    assert any("Provider initialized successfully." in message for message in messages)


def test_pipeline_wraps_initialization_failure(settings: Settings) -> None:
    factory = ProviderFactory(
        registry=_registry(FailingProvider),
        settings=settings,
    )
    pipeline = SearchPipeline(factory=factory)

    with pytest.raises(ProviderInitializationError):
        pipeline.run(_plan(provider="failing"))
