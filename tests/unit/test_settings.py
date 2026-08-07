"""Tests for the configuration system."""

import pytest

from app.config.settings import Settings, get_settings


def test_from_env_uses_defaults(
    tmp_path: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in (
        "HEADLESS",
        "TIMEOUT",
        "MAX_LEADS",
        "SEARCH_PROVIDER",
        "LOG_LEVEL",
        "PLAYWRIGHT_HEADLESS",
        "PLAYWRIGHT_TIMEOUT",
        "LEAD_MAX_RESULTS",
        "ENABLE_LLM",
        "LLM_PROVIDER",
        "LLM_MODEL",
        "FREELLM_API_KEY",
        "FREELLM_BASE_URL",
        "LLM_API_KEY",
        "LLM_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = Settings.from_env(env_file=tmp_path / "missing.env")

    assert settings.headless is True
    assert settings.timeout == 30_000
    assert settings.max_leads == 5
    assert settings.search_provider == "google"
    assert settings.log_level == "INFO"
    assert settings.output_dir.is_absolute()
    assert settings.log_dir.is_absolute()
    assert settings.llm_provider == "freellm"
    assert settings.llm_model == "auto"


def test_from_env_reads_environment_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    for name in ("PLAYWRIGHT_HEADLESS", "PLAYWRIGHT_TIMEOUT", "LEAD_MAX_RESULTS"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HEADLESS", "false")
    monkeypatch.setenv("TIMEOUT", "15000")
    monkeypatch.setenv("MAX_LEADS", "10")
    monkeypatch.setenv("SEARCH_PROVIDER", "bing_maps")

    settings = Settings.from_env(env_file=tmp_path / "missing.env")

    assert settings.headless is False
    assert settings.timeout == 15_000
    assert settings.max_leads == 10
    assert settings.search_provider == "bing_maps"


def test_from_env_normalizes_provider_and_level(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("SEARCH_PROVIDER", "Google_Maps")
    monkeypatch.setenv("LOG_LEVEL", "debug")

    settings = Settings.from_env(env_file=tmp_path / "missing.env")

    assert settings.search_provider == "google_maps"
    assert settings.log_level == "DEBUG"


def test_from_env_rejects_invalid_boolean(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("PLAYWRIGHT_HEADLESS", raising=False)
    monkeypatch.setenv("HEADLESS", "maybe")

    with pytest.raises(ValueError, match="HEADLESS"):
        Settings.from_env(env_file=tmp_path / "missing.env")


def test_from_env_rejects_invalid_integer(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("PLAYWRIGHT_TIMEOUT", raising=False)
    monkeypatch.setenv("TIMEOUT", "not-a-number")

    with pytest.raises(ValueError, match="TIMEOUT"):
        Settings.from_env(env_file=tmp_path / "missing.env")


def test_get_settings_returns_settings_instance() -> None:
    assert isinstance(get_settings(), Settings)


def test_from_env_parses_relative_directories(tmp_path) -> None:
    settings = Settings.from_env(env_file=tmp_path / "missing.env")

    assert settings.output_dir.is_absolute()
    assert settings.log_dir.is_absolute()


def test_validate_accepts_defaults(tmp_path) -> None:
    settings = Settings.from_env(env_file=tmp_path / "missing.env")

    settings.validate()


def test_validate_rejects_invalid_timeout(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("PLAYWRIGHT_TIMEOUT", raising=False)
    monkeypatch.setenv("TIMEOUT", "0")
    settings = Settings.from_env(env_file=tmp_path / "missing.env")

    with pytest.raises(ValueError, match="TIMEOUT"):
        settings.validate()


def test_validate_rejects_invalid_max_leads(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("LEAD_MAX_RESULTS", raising=False)
    monkeypatch.setenv("MAX_LEADS", "-1")
    settings = Settings.from_env(env_file=tmp_path / "missing.env")

    with pytest.raises(ValueError, match="MAX_LEADS"):
        settings.validate()


def test_validate_rejects_unsupported_provider(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("SEARCH_PROVIDER", "unknown_provider")
    settings = Settings.from_env(env_file=tmp_path / "missing.env")

    with pytest.raises(ValueError, match="SEARCH_PROVIDER"):
        settings.validate()


def test_validate_rejects_invalid_log_level(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("LOG_LEVEL", "VERBOSE")
    settings = Settings.from_env(env_file=tmp_path / "missing.env")

    with pytest.raises(ValueError, match="LOG_LEVEL"):
        settings.validate()


def test_prepare_creates_configured_directories(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "out"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    settings = Settings.from_env(env_file=tmp_path / "missing.env")

    settings.prepare()

    assert (tmp_path / "out").is_dir()
    assert (tmp_path / "logs").is_dir()


def test_from_env_supports_playwright_env_aliases(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    for name in (
        "PLAYWRIGHT_HEADLESS",
        "HEADLESS",
        "PLAYWRIGHT_TIMEOUT",
        "TIMEOUT",
        "LEAD_MAX_RESULTS",
        "MAX_LEADS",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PLAYWRIGHT_HEADLESS", "false")
    monkeypatch.setenv("PLAYWRIGHT_TIMEOUT", "45000")
    monkeypatch.setenv("LEAD_MAX_RESULTS", "50")

    settings = Settings.from_env(env_file=tmp_path / "missing.env")

    assert settings.headless is False
    assert settings.timeout == 45_000
    assert settings.max_leads == 50


def test_from_env_falls_back_to_legacy_browser_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    for name in (
        "PLAYWRIGHT_HEADLESS",
        "PLAYWRIGHT_TIMEOUT",
        "LEAD_MAX_RESULTS",
        "HEADLESS",
        "TIMEOUT",
        "MAX_LEADS",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HEADLESS", "false")
    monkeypatch.setenv("TIMEOUT", "12000")
    monkeypatch.setenv("MAX_LEADS", "8")

    settings = Settings.from_env(env_file=tmp_path / "missing.env")

    assert settings.headless is False
    assert settings.timeout == 12_000
    assert settings.max_leads == 8


def test_reads_freellm_env_vars(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("FREELLM_API_KEY", "freellm-key")
    monkeypatch.setenv("FREELLM_BASE_URL", "http://freellm.test/v1")
    monkeypatch.setenv("LLM_API_KEY", "primary-key")
    monkeypatch.setenv("LLM_BASE_URL", "http://primary.test/v1")

    settings = Settings.from_env(env_file=tmp_path / "missing.env")

    assert settings.llm_api_key == "freellm-key"
    assert settings.llm_base_url == "http://freellm.test/v1"


def test_reads_legacy_llm_api_key_aliases(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("FREELLM_API_KEY", raising=False)
    monkeypatch.delenv("FREELLM_BASE_URL", raising=False)
    monkeypatch.setenv("LLM_API_KEY", "primary-key")
    monkeypatch.setenv("LLM_BASE_URL", "http://primary.test/v1")
    monkeypatch.setenv("FREE_LLM_ROUTER_API_KEY", "legacy-key")
    monkeypatch.setenv("FREE_LLM_ROUTER_BASE_URL", "http://legacy.test/v1")

    settings = Settings.from_env(env_file=tmp_path / "missing.env")

    assert settings.llm_api_key == "primary-key"
    assert settings.llm_base_url == "http://primary.test/v1"


def test_reads_legacy_router_env_vars(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("FREELLM_API_KEY", raising=False)
    monkeypatch.delenv("FREELLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.setenv("FREE_LLM_ROUTER_API_KEY", "legacy-key")
    monkeypatch.setenv("FREE_LLM_ROUTER_BASE_URL", "http://legacy.test/v1")

    settings = Settings.from_env(env_file=tmp_path / "missing.env")

    assert settings.llm_api_key == "legacy-key"
    assert settings.llm_base_url == "http://legacy.test/v1"


def test_default_base_url_is_free_llm_router(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    for name in ("FREELLM_BASE_URL", "LLM_BASE_URL", "FREE_LLM_ROUTER_BASE_URL"):
        monkeypatch.delenv(name, raising=False)
    settings = Settings.from_env(env_file=tmp_path / "missing.env")

    assert settings.llm_base_url == "http://localhost:3001/v1"


def test_blank_llm_model_defaults_to_auto(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("LLM_MODEL", "  ")

    settings = Settings.from_env(env_file=tmp_path / "missing.env")

    assert settings.llm_model == "auto"


def test_provider_aliases_normalize_to_freellm(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    for value in ("freellmrouter", "free_llm_router", " Freellm "):
        monkeypatch.setenv("LLM_PROVIDER", value)
        settings = Settings.from_env(env_file=tmp_path / "missing.env")
        assert settings.llm_provider == "freellm"


def test_validate_rejects_non_auto_llm_model(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("LLM_MODEL", "codestral")
    settings = Settings.from_env(env_file=tmp_path / "missing.env")

    with pytest.raises(ValueError, match="LLM_MODEL"):
        settings.validate()
