"""End-to-end tests for the agent executor loop."""

import logging

import pytest

from app.agent.executor import AgentExecutor
from app.agent.planner import Planner
from app.models.lead import Lead
from app.tools.base import Tool, ToolContext, ToolResult
from app.tools.registry import ToolRegistry, build_default_registry
from tests.fakes import FakeBrowser, FakePage

PROMPT = "software companies in Karachi"


class _FakeSearch(Tool):
    """Search tool serving a fixed set of leads."""

    name = "google_maps_search"

    def __init__(self, leads, query=PROMPT, fail=False):
        super().__init__()
        self._leads = leads
        self._query = query
        self._fail = fail

    def run(self, **kwargs):
        if self._fail:
            return ToolResult.fail("provider crashed unexpectedly")
        return ToolResult.ok(
            leads=list(self._leads),
            references=[],
            provider="fixed",
            query=self._query,
            business_links=[],
        )


class _FakeDetails(Tool):
    """Details tool serving a rating map."""

    name = "business_details"

    def run(self, **kwargs):
        return ToolResult.ok(
            leads=[],
            details=[
                {"business_name": "Good Cafe", "rating": "4.8 (120 reviews)"},
                {"business_name": "Mediocre Cafe", "rating": "3.9 (40 reviews)"},
            ],
        )


@pytest.fixture
def fixed_settings(tmp_path):
    from tests.conftest import make_settings

    return make_settings(tmp_path, search_provider="fixed")


def _executor(registry, settings, browser=None):
    context = ToolContext(browser=browser, settings=settings)
    return AgentExecutor(registry=registry, context=context, settings=settings)


def test_executor_runs_full_plan_and_exports(fixed_settings, browser, fixed_factory) -> None:
    leads = [
        Lead(
            business_name="Alpha Corp",
            phone_number="+92 300 1234567",
            website="https://alpha.example",
            provider="fixed",
            search_query=PROMPT,
        )
    ]
    factory = fixed_factory(leads)
    context = ToolContext(browser=browser, settings=fixed_settings)
    registry = build_default_registry(context, factory=factory)
    plan = Planner(settings=fixed_settings).plan(PROMPT)
    executor = AgentExecutor(registry=registry, context=context, settings=fixed_settings)

    result = executor.run(PROMPT, plan)

    assert result.success
    assert result.business_type == "software companies"
    assert result.location == "Karachi"
    assert result.collected_leads == 1
    assert result.processed_leads == 1
    assert result.excel_output_path is not None
    assert result.excel_output_path.exists()


def test_executor_search_failure_fails_the_run(fixed_settings, caplog) -> None:
    registry = ToolRegistry()
    registry.register(_FakeSearch([], fail=True))
    registry.register(_FakeDetails())
    from app.tools.exporter_tool import LeadExporterTool

    registry.register(LeadExporterTool(ToolContext(settings=fixed_settings)))
    plan = Planner(settings=fixed_settings).plan(PROMPT)
    executor = _executor(registry, fixed_settings)

    with caplog.at_level(logging.ERROR):
        result = executor.run(PROMPT, plan)

    assert result.success is False
    assert result.excel_output_path is None
    assert any("Pipeline failed" in record.message for record in caplog.records)


def test_executor_applies_minimum_rating_filter(fixed_settings) -> None:
    leads = [
        Lead(business_name="Good Cafe", provider="fixed", search_query=PROMPT),
        Lead(business_name="Mediocre Cafe", provider="fixed", search_query=PROMPT),
    ]
    registry = ToolRegistry()
    registry.register(_FakeSearch(leads))
    registry.register(_FakeDetails())
    from app.tools.exporter_tool import LeadExporterTool

    registry.register(LeadExporterTool(ToolContext(settings=fixed_settings)))
    plan = Planner(settings=fixed_settings).plan(
        "restaurants in Islamabad with more than 4.5 rating"
    )
    executor = _executor(registry, fixed_settings)

    result = executor.run("restaurants in Islamabad with more than 4.5 rating", plan)

    assert result.success
    assert result.collected_leads == 2
    assert result.processed_leads == 1


def test_executor_extracts_emails_when_requested(fixed_settings) -> None:
    page = FakePage(html="Welcome to our site. Contact hello@dental.com for details.")
    browser = FakeBrowser(page=page)
    leads = [
        Lead(
            business_name="Dental Studio",
            website="https://dental.example",
            provider="fixed",
            search_query="dentists near Karachi",
        )
    ]
    factory = None
    from tests.fakes import FixedLeadsProvider, ProviderFactory

    FixedLeadsProvider.current_leads = leads
    from app.providers.provider_registry import ProviderRegistry as AppRegistry

    registry_reg = AppRegistry()
    registry_reg.register(FixedLeadsProvider)
    factory = ProviderFactory(registry=registry_reg, settings=fixed_settings, browser=browser)

    context = ToolContext(browser=browser, settings=fixed_settings)
    registry = build_default_registry(context, factory=factory)
    plan = Planner(settings=fixed_settings).plan("dentists near Karachi with emails")
    executor = AgentExecutor(registry=registry, context=context, settings=fixed_settings)

    result = executor.run("dentists near Karachi with emails", plan)

    assert result.success
    assert result.collected_leads == 1
    assert result.processed_leads == 1
