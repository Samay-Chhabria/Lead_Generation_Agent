"""Tests for the tool registry and the built-in tool set."""

import pytest

from app.exceptions.tool_exception import DuplicateToolError, UnknownToolError
from app.tools.base import Tool, ToolContext, ToolResult
from app.tools.registry import ToolRegistry, build_default_registry


class _EchoTool(Tool):
    name = "echo"
    description = "Echo back the given text."

    def run(self, text: str = "", **kwargs) -> ToolResult:
        return ToolResult.ok(text=text)


class _OtherTool(_EchoTool):
    name = "other"


def test_register_and_get() -> None:
    registry = ToolRegistry()
    tool = _EchoTool()
    registry.register(tool)
    assert registry.get("echo") is tool


def test_duplicate_registration_raises() -> None:
    registry = ToolRegistry()
    registry.register(_EchoTool())
    with pytest.raises(DuplicateToolError):
        registry.register(_EchoTool())


def test_get_unknown_tool_raises() -> None:
    registry = ToolRegistry()
    with pytest.raises(UnknownToolError):
        registry.get("missing")


def test_names_are_sorted() -> None:
    registry = ToolRegistry()
    registry.register(_OtherTool())
    registry.register(_EchoTool())
    assert registry.names() == ["echo", "other"]


def test_has_and_unregister() -> None:
    registry = ToolRegistry()
    registry.register(_EchoTool())
    assert registry.has("echo")
    registry.unregister("echo")
    assert not registry.has("echo")


def test_catalog_lists_tools() -> None:
    registry = ToolRegistry()
    registry.register(_EchoTool())
    assert "echo" in registry.catalog()


def test_default_registry_has_all_builtin_tools(tmp_path) -> None:
    from app.config.settings import Settings

    settings = Settings(
        headless=True,
        timeout=5_000,
        max_leads=10,
        search_provider="google",
        browser_type="chromium",
        output_dir=tmp_path / "outputs",
        log_dir=tmp_path / "logs",
        log_level="INFO",
    )
    registry = build_default_registry(ToolContext(settings=settings))
    expected = {
        "google_maps_search",
        "website_crawler",
        "email_extractor",
        "phone_extractor",
        "business_details",
        "lead_exporter",
    }
    assert expected <= set(registry.names())


def test_default_registry_rejects_duplicate_names(tmp_path) -> None:
    from app.config.settings import Settings

    settings = Settings(
        headless=True,
        timeout=5_000,
        max_leads=10,
        search_provider="google",
        browser_type="chromium",
        output_dir=tmp_path / "outputs",
        log_dir=tmp_path / "logs",
        log_level="INFO",
    )
    registry = build_default_registry(ToolContext(settings=settings))
    duplicate = _EchoTool()
    duplicate.name = "google_maps_search"
    with pytest.raises(DuplicateToolError):
        registry.register(duplicate)
