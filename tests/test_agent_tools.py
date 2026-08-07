"""Tests for the agent-facing tools and the ToolManager coordination layer.

These tests exercise the spec-named wrappers (search, business_collection,
business_extraction, export, navigation, pipeline, summary) that delegate to the
existing pipeline tools, plus the ToolManager's guarded ``execute``. The fixed
test provider keeps everything deterministic and offline.
"""

from app.agent.executor import AgentExecutor
from app.agent.planner import Planner
from app.agent.tool_manager import PIPELINE_TOOL_NAME, ToolManager
from app.models.execution_result import ExecutionResult
from app.models.lead import Lead
from app.tools.base import Tool, ToolContext, ToolResult
from app.tools.google_maps_tool import GoogleMapsSearchTool
from app.tools.registry import ToolRegistry, build_default_registry
from tests.conftest import make_settings
from tests.fakes import FakeBrowser

PROMPT = "coffee shops in Karachi"


class _RaisingTool(Tool):
    name = "raising"

    def run(self, **kwargs) -> ToolResult:
        raise RuntimeError("boom")


class _OkTool(Tool):
    name = "ok"

    def run(self, **kwargs) -> ToolResult:
        return ToolResult.ok(value=42)


def _lead(name: str = "Alpha Cafe") -> Lead:
    return Lead(
        business_name=name,
        phone_number="+92 300 1234567",
        website="https://alpha.example",
        provider="fixed",
        search_query=PROMPT,
    )


def _context(settings, browser):
    return ToolContext(browser=browser, settings=settings)


# ---------------------------------------------------------------------------
# ToolManager
# ---------------------------------------------------------------------------


def test_manager_executes_known_tool() -> None:
    registry = ToolRegistry()
    registry.register(_OkTool())
    manager = ToolManager(registry=registry)

    result = manager.execute("ok")

    assert result.success
    assert result.data == {"value": 42}


def test_manager_returns_failed_result_for_unknown_tool() -> None:
    manager = ToolManager(registry=ToolRegistry())

    result = manager.execute("missing")

    assert not result.success
    assert "Unknown tool" in result.error


def test_manager_returns_failed_result_when_tool_raises(caplog) -> None:
    registry = ToolRegistry()
    registry.register(_RaisingTool())
    manager = ToolManager(registry=registry)

    result = manager.execute("raising")

    assert not result.success
    assert "failed" in result.error


def test_manager_get_returns_none_for_unknown_tool() -> None:
    manager = ToolManager(registry=ToolRegistry())

    assert manager.get("missing") is None
    assert not manager.has("missing")


def test_manager_mirrors_registry_api() -> None:
    registry = ToolRegistry()
    registry.register(_OkTool())
    manager = ToolManager(registry=registry)

    assert manager.names() == ["ok"]
    assert manager.has("ok")
    assert "ok:" in manager.catalog()
    assert "ok" in manager.all()


def test_manager_has_pipeline_when_registered() -> None:
    class PipelineLookalike(_OkTool):
        name = PIPELINE_TOOL_NAME

    registry = ToolRegistry()
    manager = ToolManager(registry=registry)
    assert not manager.has_pipeline()
    registry.register(PipelineLookalike())
    assert manager.has_pipeline()


# ---------------------------------------------------------------------------
# Search wrappers
# ---------------------------------------------------------------------------


def test_search_tool_collects_leads(fixed_settings, browser, fixed_factory) -> None:
    context = _context(fixed_settings, browser)
    registry = build_default_registry(context, factory=fixed_factory([_lead()]))

    result = registry.get("search").run(business_type="coffee shops", location="Karachi")

    assert result.success
    assert len(result.data["leads"]) == 1
    assert result.data["provider"] == "fixed"
    assert result.data["query"].startswith("coffee shops")


# ---------------------------------------------------------------------------
# Result limit resolution
# ---------------------------------------------------------------------------


def test_search_tool_limit_prefers_explicit_count_in_business_type(fixed_settings, browser) -> None:
    tool = GoogleMapsSearchTool(context=_context(fixed_settings, browser))

    assert tool._resolve_limit("find 3 coffee shops", 0) == 3
    assert tool._resolve_limit("collect 50 software companies", 0) == 50


def test_search_tool_limit_honours_explicit_override(fixed_settings, browser) -> None:
    tool = GoogleMapsSearchTool(context=_context(fixed_settings, browser))

    assert tool._resolve_limit("coffee shops", 7) == 7
    assert tool._resolve_limit("coffee shops", 50) == 50


def test_search_tool_limit_caps_configured_default_at_ten(fixed_settings, browser) -> None:
    tool = GoogleMapsSearchTool(context=_context(fixed_settings, browser))

    assert tool._resolve_limit("coffee shops", 0) == 10


def test_search_tool_limit_uses_default_when_within_ceiling(tmp_path) -> None:
    settings = make_settings(tmp_path, search_provider="fixed", max_leads=5)
    tool = GoogleMapsSearchTool(context=_context(settings, FakeBrowser()))

    assert tool._resolve_limit("coffee shops", 0) == 5


def test_business_collection_tool_collects_leads(fixed_settings, browser, fixed_factory) -> None:
    context = _context(fixed_settings, browser)
    registry = build_default_registry(context, factory=fixed_factory([_lead()]))

    result = registry.get("business_collection").run(
        business_type="coffee shops", location="Karachi"
    )

    assert result.success
    assert len(result.data["leads"]) == 1


def test_business_extraction_tool_handles_empty_run(fixed_settings, browser) -> None:
    context = _context(fixed_settings, browser)
    registry = build_default_registry(context)

    result = registry.get("business_extraction").run(leads=[])

    assert result.success
    assert result.data["leads"] == []


def test_export_tool_writes_workbook(fixed_settings, browser) -> None:
    context = _context(fixed_settings, browser)
    registry = build_default_registry(context)

    result = registry.get("export").run(
        leads=[_lead()], business_type="coffee shops", location="Karachi"
    )

    assert result.success
    path = result.data["path"]
    assert path is not None
    assert path.exists()
    assert result.data["exported_count"] == 1


def test_navigation_tool_moves_the_page(fixed_settings, browser) -> None:
    context = _context(fixed_settings, browser)
    registry = build_default_registry(context)

    result = registry.get("navigation").run(url="https://example.com")

    assert result.success
    assert result.data["url"] == "https://example.com"
    assert browser.page.visited_url == "https://example.com"


def test_navigation_tool_requires_url(fixed_settings, browser) -> None:
    context = _context(fixed_settings, browser)
    registry = build_default_registry(context)

    result = registry.get("navigation").run(url="   ")

    assert not result.success


# ---------------------------------------------------------------------------
# Pipeline + summary
# ---------------------------------------------------------------------------


def test_pipeline_tool_runs_end_to_end(fixed_settings, browser, fixed_factory) -> None:
    context = _context(fixed_settings, browser)
    registry = build_default_registry(context, factory=fixed_factory([_lead()]))

    result = registry.get("pipeline").run(prompt=PROMPT)

    assert result.success
    assert result.data["metrics"]["processed_leads"] == 1
    assert result.data["path"] is not None
    assert result.data["business_type"] == "coffee shops"


def test_pipeline_tool_requires_prompt(fixed_settings, browser) -> None:
    context = _context(fixed_settings, browser)
    registry = build_default_registry(context)

    result = registry.get("pipeline").run(prompt="  ")

    assert not result.success


def test_summary_tool_builds_human_readable_text() -> None:
    result = ExecutionResult(
        search_query=PROMPT,
        business_type="coffee shops",
        location="Karachi",
        provider="fixed",
        collected_leads=2,
        processed_leads=1,
        duplicates_removed=1,
        execution_time=1.25,
        success=True,
    )
    summary = SummaryToolProxy()

    outcome = summary.run(result=result, leads=[_lead(), _lead("Beta Cafe")])

    assert outcome.success
    text = outcome.data["summary"]
    assert "Lead generation completed successfully." in text
    assert "Businesses found: 2" in text
    assert "Businesses processed: 1" in text
    assert "Duplicates removed: 1" in text
    assert outcome.data["metrics"]["success"] is True


class SummaryToolProxy:
    """Thin proxy so the summary tool test stays decoupled from the registry."""

    def __init__(self) -> None:
        from app.tools.summary_tool import SummaryTool

        self._delegate = SummaryTool()

    def run(self, **kwargs) -> ToolResult:
        return self._delegate.run(**kwargs)


def test_executor_fills_result_summary(fixed_settings, browser, fixed_factory) -> None:
    leads = [_lead()]
    context = _context(fixed_settings, browser)
    registry = build_default_registry(context, factory=fixed_factory(leads))
    plan = Planner(settings=fixed_settings).plan(PROMPT)
    executor = AgentExecutor(registry=registry, context=context, settings=fixed_settings)

    result = executor.run(PROMPT, plan)

    assert result.success
    assert result.summary
    assert "Lead generation completed successfully." in result.summary
    assert result.summary.strip().splitlines()[0].startswith("Lead generation")
