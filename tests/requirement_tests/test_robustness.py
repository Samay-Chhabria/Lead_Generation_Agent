"""Failure and robustness tests not covered by the component suites.

These tests exercise the application-level boundaries: unexpected failures are
contained at the application layer, logging is actually written to the
configured log file, hostile prompts produce safe filenames, and runs with
mostly-empty lead data still complete. They complement the per-component tests
without duplicating them.
"""

import logging

from app.application.application import LeadGenerationApplication
from app.config.constants import LOG_FILE_NAME
from app.models.lead import Lead
from app.pipeline.application_pipeline import ApplicationPipeline
from app.providers.provider_factory import ProviderFactory
from app.providers.provider_registry import ProviderRegistry
from app.providers.search_provider import SearchProvider
from tests.conftest import make_settings
from tests.fakes import FakeBrowser, FixedLeadsProvider

PROMPT = "software companies in Karachi"


class _ExplodingProvider(SearchProvider):
    """Provider whose search() raises an unexpected exception mid-run."""

    name = "explode"

    def initialize(self) -> None:
        pass

    def search(self) -> list[str]:
        raise RuntimeError("provider crashed unexpectedly")

    def collect_results(self) -> list[object]:
        return []

    def close(self) -> None:
        pass


def _valid_settings(tmp_path):
    """Settings that pass Settings.validate() so the application starts."""
    return make_settings(tmp_path, search_provider="google")


def _app_factory(
    settings, browser: FakeBrowser, provider_class: type[SearchProvider]
) -> ProviderFactory:
    """Build a factory mapping the supported 'google' name to a test provider."""
    registry = ProviderRegistry()
    registry.register(provider_class, name="google")
    return ProviderFactory(registry=registry, settings=settings, browser=browser)


def _reset_root_handlers() -> None:
    """Remove previously configured handlers so log files are deterministic."""
    root = logging.getLogger()
    for handler in list(root.handlers):
        handler.close()
        root.removeHandler(handler)


def _lead(name: str = "Alpha Corp") -> Lead:
    return Lead(
        business_name=name,
        provider="fixed",
        search_query=PROMPT,
    )


def test_application_contains_config_failure_and_returns_nonzero(
    tmp_path, caplog: logging.LogCaptureFixture
) -> None:
    settings = make_settings(tmp_path, log_level="NOT_A_LEVEL")

    with caplog.at_level(logging.ERROR):
        exit_code = LeadGenerationApplication(settings=settings).run(prompt=PROMPT)

    assert exit_code == 1
    assert any("Application failed" in record.message for record in caplog.records)


def test_application_writes_lifecycle_to_configured_log_file(
    tmp_path, browser: FakeBrowser
) -> None:
    _reset_root_handlers()
    settings = _valid_settings(tmp_path)
    FixedLeadsProvider.current_leads = [_lead()]
    factory = _app_factory(settings, browser, FixedLeadsProvider)

    exit_code = LeadGenerationApplication(settings=settings, factory=factory).run(prompt=PROMPT)

    assert exit_code == 0
    log_file = settings.log_dir / LOG_FILE_NAME
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "Application starting..." in content
    assert "Pipeline finished." in content
    assert "Application shutting down..." in content


def test_failed_run_writes_error_to_configured_log_file(tmp_path, browser: FakeBrowser) -> None:
    _reset_root_handlers()
    settings = _valid_settings(tmp_path)
    factory = _app_factory(settings, browser, _ExplodingProvider)

    exit_code = LeadGenerationApplication(settings=settings, factory=factory).run(prompt=PROMPT)

    assert exit_code == 1
    log_file = settings.log_dir / LOG_FILE_NAME
    assert log_file.exists()
    assert "Pipeline failed" in log_file.read_text(encoding="utf-8")
    assert browser.close_count == 1


def test_prompt_with_filename_hostile_characters_still_succeeds(tmp_path, fixed_factory) -> None:
    settings = make_settings(tmp_path, search_provider="fixed")

    result = ApplicationPipeline(
        settings=settings, factory=fixed_factory([_lead("Café Zürich")])
    ).execute("café/restaurants: in Paris")

    assert result.success is True
    assert result.excel_output_path is not None
    assert result.excel_output_path.suffix == ".xlsx"
    assert "/" not in result.excel_output_path.name
    assert ":" not in result.excel_output_path.name


def test_run_with_minimal_lead_data_completes(tmp_path, fixed_factory) -> None:
    settings = make_settings(tmp_path, search_provider="fixed")
    leads = [_lead("Minimal A"), _lead("Minimal B")]

    result = ApplicationPipeline(settings=settings, factory=fixed_factory(leads)).execute(PROMPT)

    assert result.success is True
    assert result.collected_leads == 2
    assert result.processed_leads == 2
    assert result.excel_output_path is not None
    assert result.excel_output_path.exists()
