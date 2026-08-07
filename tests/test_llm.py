"""Tests for the LLM provider abstraction and factory.

The application uses exactly one OpenAI-compatible gateway (FreeLLM Router) and
asks for ``model="auto"`` on every request; the router performs all model
selection and fallback. These tests cover the client, the factory mode
switching, and the environment configuration.
"""

import json

import pytest

from app.config.constants import (
    DEFAULT_FREELLM_BASE_URL,
    DEFAULT_LLM_PROVIDER,
    SUPPORTED_LLM_PROVIDERS,
)
from app.config.settings import Settings
from app.llm.base import (
    LLMError,
    LLMNetworkError,
    LLMStatusError,
    ToolMessage,
    parse_json_objects,
)
from app.llm.factory import create_llm_provider
from app.llm.mock_provider import MockProvider
from app.llm.providers.freellmrouter import FreeLLMRouterProvider


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        headless=True,
        timeout=5_000,
        max_leads=10,
        search_provider="google",
        browser_type="chromium",
        output_dir=tmp_path / "outputs",
        log_dir=tmp_path / "logs",
        log_level="INFO",
        llm_provider="mock",
    )


def test_mock_provider_returns_json_with_tool_calls() -> None:
    completion = MockProvider().complete([ToolMessage(role="user", content="hi")])
    payload = json.loads(completion)
    assert isinstance(payload["tool_calls"], list)
    assert payload["tool_calls"][0] == "google_maps_search"
    assert "lead_exporter" in payload["tool_calls"]


def test_parse_json_objects_handles_code_blocks() -> None:
    text = 'Sure, here:\n```json\n{"tool_calls": ["a"]}\n```\nHope that helps.'
    parsed = parse_json_objects(text)
    assert parsed == [{"tool_calls": ["a"]}]


def test_parse_json_objects_rejects_garbage() -> None:
    from app.llm.base import LLMResponseError

    with pytest.raises(LLMResponseError):
        parse_json_objects("no json here")


def test_parse_json_objects_finds_object_in_prose() -> None:
    parsed = parse_json_objects('The answer is {"thought": "x", "tool_calls": ["a"]}.')
    assert parsed[0]["tool_calls"] == ["a"]


def test_mock_provider_is_the_offline_default() -> None:
    assert DEFAULT_LLM_PROVIDER == "freellm"
    assert "mock" in SUPPORTED_LLM_PROVIDERS
    assert "freellm" in SUPPORTED_LLM_PROVIDERS


def test_offline_mode_when_llm_disabled(tmp_path) -> None:
    from dataclasses import replace

    settings = replace(_router_settings(tmp_path), enable_llm=False, llm_api_key="router-key")
    provider = create_llm_provider(settings)
    assert isinstance(provider, MockProvider)


def test_offline_mode_when_router_key_missing(tmp_path) -> None:
    provider = create_llm_provider(_router_settings(tmp_path))
    assert isinstance(provider, MockProvider)


def test_ai_mode_creates_single_auto_provider(tmp_path) -> None:
    from dataclasses import replace

    settings = replace(_router_settings(tmp_path), llm_api_key="router-key")
    provider = create_llm_provider(settings)
    assert isinstance(provider, FreeLLMRouterProvider)
    assert provider.model == "auto"
    assert provider.base_url == DEFAULT_FREELLM_BASE_URL


def test_ai_mode_uses_settings_base_url(tmp_path) -> None:
    from dataclasses import replace

    settings = replace(
        _router_settings(tmp_path),
        llm_api_key="router-key",
        llm_base_url="http://router.test/v1",
    )
    provider = create_llm_provider(settings)
    assert isinstance(provider, FreeLLMRouterProvider)
    assert provider.base_url == "http://router.test/v1"


def test_provider_requires_api_key() -> None:
    with pytest.raises(LLMError):
        FreeLLMRouterProvider(base_url="http://router.test/v1")


def test_provider_requires_base_url() -> None:
    with pytest.raises(LLMError):
        FreeLLMRouterProvider(api_key="router-key")


def test_provider_sends_openai_compatible_request_with_model_auto(monkeypatch) -> None:
    captured: dict = {}

    def fake_post(url, payload, headers=None, timeout=60):
        captured["url"] = url
        captured["payload"] = payload
        captured["headers"] = headers
        captured["timeout"] = timeout
        return {"choices": [{"message": {"content": "hello back"}}]}

    monkeypatch.setattr("app.llm.providers.freellmrouter.post_json", fake_post)
    provider = FreeLLMRouterProvider(api_key="router-key", base_url="http://router.test/v1/")
    output = provider.complete([ToolMessage(role="user", content="hello")])

    assert output == "hello back"
    assert captured["url"] == "http://router.test/v1/chat/completions"
    assert captured["payload"]["model"] == "auto"
    assert captured["headers"]["Authorization"] == "Bearer router-key"
    assert captured["timeout"] == 30


def test_provider_maps_http_error_to_status_error(monkeypatch) -> None:
    def fake_post(url, payload, headers=None, timeout=60):
        raise LLMStatusError(f"HTTP 429 from LLM endpoint {url}", status_code=429)

    monkeypatch.setattr("app.llm.providers.freellmrouter.post_json", fake_post)
    provider = FreeLLMRouterProvider(api_key="router-key", base_url="http://router.test/v1")

    with pytest.raises(LLMStatusError) as exc_info:
        provider.complete([ToolMessage(role="user", content="hello")])

    assert exc_info.value.status_code == 429


def test_provider_rejects_bad_response_shape(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.llm.providers.freellmrouter.post_json",
        lambda *args, **kwargs: {"choices": []},
    )
    provider = FreeLLMRouterProvider(api_key="router-key", base_url="http://router.test/v1")

    with pytest.raises(LLMError):
        provider.complete([ToolMessage(role="user", content="hello")])


def test_provider_retries_network_errors_then_succeeds(monkeypatch) -> None:
    calls = {"count": 0}

    def fake_post(url, payload, headers=None, timeout=60):
        calls["count"] += 1
        if calls["count"] < 3:
            raise LLMNetworkError("connection refused")
        return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr("app.llm.providers.freellmrouter.post_json", fake_post)
    provider = FreeLLMRouterProvider(
        api_key="router-key",
        base_url="http://router.test/v1",
        backoff=(0, 0),
        sleep=lambda _seconds: None,
    )

    assert provider.complete([ToolMessage(role="user", content="hello")]) == "ok"
    assert calls["count"] == 3


def test_provider_raises_after_network_retries_exhausted(monkeypatch) -> None:
    calls = {"count": 0}

    def fake_post(url, payload, headers=None, timeout=60):
        calls["count"] += 1
        raise LLMNetworkError("connection refused")

    monkeypatch.setattr("app.llm.providers.freellmrouter.post_json", fake_post)
    provider = FreeLLMRouterProvider(
        api_key="router-key",
        base_url="http://router.test/v1",
        backoff=(0, 0),
        sleep=lambda _seconds: None,
    )

    with pytest.raises(LLMNetworkError):
        provider.complete([ToolMessage(role="user", content="hello")])
    assert calls["count"] == 3


def test_provider_uses_router_reported_model(monkeypatch) -> None:
    events: list[tuple[str, str]] = []

    def fake_post(url, payload, headers=None, timeout=60):
        return {
            "model": "gpt-oss-120b-groq",
            "choices": [{"message": {"content": "hi"}}],
        }

    monkeypatch.setattr("app.llm.providers.freellmrouter.post_json", fake_post)
    provider = FreeLLMRouterProvider(
        api_key="router-key",
        base_url="http://router.test/v1",
        event_sink=lambda model, reason: events.append((model, reason)),
    )

    output = provider.complete([ToolMessage(role="user", content="hello")])

    assert output == "hi"
    assert provider.last_model == "gpt-oss-120b-groq"
    assert events == [("gpt-oss-120b-groq", "Auto (Router Selected)")]


def test_provider_reports_auto_when_router_sends_no_model(monkeypatch) -> None:
    events: list[tuple[str, str]] = []

    def fake_post(url, payload, headers=None, timeout=60):
        return {"choices": [{"message": {"content": "hi"}}]}

    monkeypatch.setattr("app.llm.providers.freellmrouter.post_json", fake_post)
    provider = FreeLLMRouterProvider(
        api_key="router-key",
        base_url="http://router.test/v1",
        event_sink=lambda model, reason: events.append((model, reason)),
    )

    provider.complete([ToolMessage(role="user", content="hello")])

    assert provider.last_model == "auto"
    assert events == [("auto", "Auto (Router Selected)")]


def test_from_env_reads_freellm_vars(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ENABLE_LLM", "true")
    monkeypatch.setenv("FREELLM_API_KEY", "router-key")
    monkeypatch.setenv("FREELLM_BASE_URL", "http://router.test/v1")
    monkeypatch.setenv("LLM_PROVIDER", "freellm")

    settings = Settings.from_env(env_file=tmp_path / "missing.env")

    assert settings.enable_llm is True
    assert settings.llm_api_key == "router-key"
    assert settings.llm_base_url == "http://router.test/v1"
    assert settings.llm_provider == "freellm"
    assert settings.llm_model == "auto"
    assert settings.llm_enabled is True


def test_from_env_keeps_legacy_aliases(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("FREELLM_API_KEY", raising=False)
    monkeypatch.delenv("FREELLM_BASE_URL", raising=False)
    monkeypatch.setenv("LLM_API_KEY", "legacy-key")
    monkeypatch.setenv("LLM_BASE_URL", "http://legacy.test/v1")

    settings = Settings.from_env(env_file=tmp_path / "missing.env")

    assert settings.llm_api_key == "legacy-key"
    assert settings.llm_base_url == "http://legacy.test/v1"


def test_from_env_normalizes_provider_aliases(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "freellmrouter")

    settings = Settings.from_env(env_file=tmp_path / "missing.env")

    assert settings.llm_provider == "freellm"


def test_from_env_default_model_is_auto(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("LLM_MODEL", raising=False)

    settings = Settings.from_env(env_file=tmp_path / "missing.env")

    assert settings.llm_model == "auto"


def _router_settings(tmp_path) -> Settings:
    """Settings with the FreeLLM Router defaults."""
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


def test_ai_mode_requires_router_api_key(tmp_path) -> None:
    settings = _router_settings(tmp_path)
    assert settings.enable_llm is True
    assert settings.llm_api_key == ""
    assert settings.llm_enabled is False
    assert settings.llm_mode == "offline"


def test_ai_mode_active_with_router_api_key(tmp_path) -> None:
    from dataclasses import replace

    settings = replace(_router_settings(tmp_path), llm_api_key="router-key")
    assert settings.llm_enabled is True
    assert settings.llm_mode == "ai"


def test_validate_accepts_defaults(tmp_path) -> None:
    settings = _router_settings(tmp_path)

    settings.validate()


def test_validate_rejects_non_auto_model(tmp_path) -> None:
    from dataclasses import replace

    settings = replace(_router_settings(tmp_path), llm_model="codestral")

    with pytest.raises(ValueError, match="LLM_MODEL"):
        settings.validate()


def test_validate_rejects_unknown_provider(tmp_path) -> None:
    from dataclasses import replace

    settings = replace(_router_settings(tmp_path), llm_provider="corgi")

    with pytest.raises(ValueError, match="LLM_PROVIDER"):
        settings.validate()
