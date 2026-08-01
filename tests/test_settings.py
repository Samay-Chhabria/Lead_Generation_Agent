"""Tests for the configuration system."""

import pytest

from app.config.settings import Settings, get_settings


def test_from_env_uses_defaults(tmp_path: pytest.TempPathFactory) -> None:
    settings = Settings.from_env(env_file=tmp_path / "missing.env")

    assert settings.headless is True
    assert settings.timeout == 30_000
    assert settings.max_leads == 25
    assert settings.search_provider == "google"
    assert settings.log_level == "INFO"
    assert settings.output_dir.is_absolute()
    assert settings.log_dir.is_absolute()


def test_from_env_reads_environment_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
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
    monkeypatch.setenv("HEADLESS", "maybe")

    with pytest.raises(ValueError, match="HEADLESS"):
        Settings.from_env(env_file=tmp_path / "missing.env")


def test_from_env_rejects_invalid_integer(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
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
    monkeypatch.setenv("TIMEOUT", "0")
    settings = Settings.from_env(env_file=tmp_path / "missing.env")

    with pytest.raises(ValueError, match="TIMEOUT"):
        settings.validate()


def test_validate_rejects_invalid_max_leads(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
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
