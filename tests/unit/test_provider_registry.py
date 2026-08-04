"""Tests for the provider registry."""

import pytest

from app.exceptions.provider_exception import DuplicateProviderError, UnknownProviderError
from app.providers.provider_registry import ProviderRegistry
from app.providers.search_provider import SearchProvider


class DummyProvider(SearchProvider):
    name = "dummy"


class OtherProvider(SearchProvider):
    name = "other"


class NotAProvider:
    pass


def test_register_and_get() -> None:
    registry = ProviderRegistry()
    registry.register(DummyProvider)

    assert registry.get("dummy") is DummyProvider
    assert registry.is_registered("dummy")


def test_register_with_explicit_name() -> None:
    registry = ProviderRegistry()
    registry.register(DummyProvider, name="custom")

    assert registry.get("custom") is DummyProvider


def test_duplicate_registration_is_rejected() -> None:
    registry = ProviderRegistry()
    registry.register(DummyProvider)

    with pytest.raises(DuplicateProviderError):
        registry.register(DummyProvider)


def test_duplicate_registration_with_explicit_name_is_rejected() -> None:
    registry = ProviderRegistry()
    registry.register(DummyProvider, name="custom")

    with pytest.raises(DuplicateProviderError):
        registry.register(OtherProvider, name="custom")


def test_get_unknown_provider_raises() -> None:
    registry = ProviderRegistry()

    with pytest.raises(UnknownProviderError):
        registry.get("missing")


def test_list_returns_sorted_names() -> None:
    registry = ProviderRegistry()
    registry.register(OtherProvider)
    registry.register(DummyProvider)

    assert registry.list() == ("dummy", "other")


def test_is_registered_is_case_insensitive() -> None:
    registry = ProviderRegistry()
    registry.register(DummyProvider)

    assert registry.is_registered("DUMMY")
    assert not registry.is_registered("missing")


def test_register_rejects_empty_name() -> None:
    registry = ProviderRegistry()

    with pytest.raises(ValueError):
        registry.register(DummyProvider, name="  ")


def test_register_rejects_non_provider_class() -> None:
    registry = ProviderRegistry()

    with pytest.raises(TypeError):
        registry.register(NotAProvider)  # type: ignore[arg-type]


def test_unregister_removes_provider() -> None:
    registry = ProviderRegistry()
    registry.register(DummyProvider)
    registry.unregister("dummy")

    assert not registry.is_registered("dummy")
    with pytest.raises(UnknownProviderError):
        registry.get("dummy")


def test_clear_removes_all_providers() -> None:
    registry = ProviderRegistry()
    registry.register(DummyProvider)
    registry.register(OtherProvider)

    registry.clear()

    assert registry.list() == ()
