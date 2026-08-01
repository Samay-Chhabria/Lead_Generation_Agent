"""Tests for application bootstrap and agent startup.

The agent normally launches a real browser and searches Google Maps, which the
tests must not do. A placeholder factory is injected so the agent runs its full
workflow without touching the network or launching a browser.
"""

import logging
from pathlib import Path

import pytest

from app.agent.lead_generation_agent import LeadGenerationAgent
from app.application.application import LeadGenerationApplication
from app.config.settings import Settings
from app.providers.provider_factory import ProviderFactory
from app.providers.provider_registry import ProviderRegistry
from app.providers.search_provider import SearchProvider

_PROMPT = "coffee shops in America"


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        headless=True,
        timeout=5_000,
        max_leads=10,
        search_provider="google",
        browser_type="chromium",
        output_dir=tmp_path / "outputs",
        log_dir=tmp_path / "logs",
        log_level="INFO",
    )


@pytest.fixture
def factory(settings: Settings) -> ProviderFactory:
    registry = ProviderRegistry()
    registry.register(SearchProvider, name="google")
    return ProviderFactory(registry=registry, settings=settings)


def test_application_run_returns_zero(
    settings: Settings,
    factory: ProviderFactory,
) -> None:
    assert LeadGenerationApplication(settings=settings, factory=factory).run(prompt=_PROMPT) == 0


def test_application_logs_lifecycle(
    caplog: pytest.LogCaptureFixture,
    settings: Settings,
    factory: ProviderFactory,
) -> None:
    with caplog.at_level(logging.INFO):
        LeadGenerationApplication(settings=settings, factory=factory).run(prompt=_PROMPT)

    messages = [record.message for record in caplog.records]
    assert any("Application starting..." in message for message in messages)
    assert any("Loading configuration..." in message for message in messages)
    assert any("Logging initialized." in message for message in messages)
    assert any("Application shutting down..." in message for message in messages)


def test_agent_logs_ready(
    caplog: pytest.LogCaptureFixture,
    settings: Settings,
    factory: ProviderFactory,
) -> None:
    with caplog.at_level(logging.INFO):
        LeadGenerationAgent(settings=settings, factory=factory).run(prompt=_PROMPT)

    messages = [record.message for record in caplog.records]
    assert any("Lead Generation Agent Ready." in message for message in messages)
    assert any("Parsed search plan:" in message for message in messages)


def test_agent_prints_search_plan(
    capsys: pytest.CaptureFixture,
    settings: Settings,
    factory: ProviderFactory,
) -> None:
    LeadGenerationAgent(settings=settings, factory=factory).run(
        prompt="software companies in Karachi"
    )

    output = capsys.readouterr().out
    assert "Search Plan" in output
    assert "Original Prompt: software companies in Karachi" in output
    assert "Business Type: software companies" in output
    assert "Location: Karachi" in output
    assert "Provider:" in output
    assert "Maximum Leads:" in output
    assert "Search completed successfully." in output
