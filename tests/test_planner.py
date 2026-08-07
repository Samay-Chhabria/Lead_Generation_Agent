"""Tests for the intent-aware planner."""

import json

import pytest

from app.agent.planner import Planner
from app.config.settings import Settings
from app.exceptions.llm_exception import PlanningError
from app.llm.base import LLMProvider


@pytest.fixture
def settings(tmp_path):
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


class _ScriptedLLM(LLMProvider):
    """LLM that returns a fixed tool selection."""

    name = "fake"

    def __init__(self, text: str = "") -> None:
        self._text = text or (
            '{"thought": "pick tools", '
            '"tool_calls": ["google_maps_search", "email_extractor", "lead_exporter"]}'
        )

    def complete(self, messages, **kwargs) -> str:
        return self._text


def _planner(settings) -> Planner:
    return Planner(settings=settings)


class _StaleLLM(LLMProvider):
    """LLM that keeps proposing a stale plan unrelated to the current query.

    This reproduces a weak router model that echoes the old planning example
    (dentists / Clifton, Karachi) no matter what the current query is.
    """

    name = "stale"

    def complete(self, messages, **kwargs) -> str:
        return json.dumps(
            {
                "business_type": "dentists",
                "location": "Clifton, Karachi",
                "provider": "google",
                "wants_emails": False,
                "wants_websites": False,
                "wants_phones": False,
                "min_rating": None,
                "tool_calls": ["google_maps_search", "lead_exporter"],
            }
        )


class _CapturingLLM(LLMProvider):
    """LLM that records every prompt it sees and returns a scripted answer."""

    name = "capturing"

    def __init__(self, answer: str = "") -> None:
        self._answer = answer or (
            '{"thought": "pick tools", '
            '"tool_calls": ["google_maps_search", "email_extractor", "lead_exporter"]}'
        )
        self.prompts: list[str] = []

    def complete(self, messages, **kwargs) -> str:
        prompt = messages[0].content
        self.prompts.append(prompt)
        if "tool_calls" in prompt and "business_type" not in prompt:
            return self._answer
        return json.dumps(
            {
                "business_type": "skin specialist",
                "location": "Karachi",
                "provider": "google",
                "wants_emails": True,
                "wants_websites": False,
                "wants_phones": False,
                "min_rating": None,
                "tool_calls": ["google_maps_search", "email_extractor", "lead_exporter"],
            }
        )


class _FakeRegistry:
    """Minimal registry exposing a catalog and tool membership for planning."""

    _TOOLS = {
        "google_maps_search",
        "business_details",
        "email_extractor",
        "lead_exporter",
    }

    def catalog(self) -> str:
        return "\n".join(f"{name}: {name}" for name in sorted(self._TOOLS))

    def has(self, name: str) -> bool:
        return name in self._TOOLS

    def get(self, name: str):
        class _Tool:
            def __init__(self, tool_name: str) -> None:
                self.name = tool_name
                self.description = tool_name

        return _Tool(name)


def test_parses_basic_task(settings) -> None:
    intent = _planner(settings).parse_task("dentists near Clifton Karachi")
    assert intent.business_type == "dentists"
    assert intent.location == "Clifton Karachi"


def test_parses_task_with_filler_words(settings) -> None:
    intent = _planner(settings).parse_task("I need restaurants in Islamabad")
    assert intent.business_type == "restaurants"
    assert intent.location == "Islamabad"


def test_parses_email_intent(settings) -> None:
    intent = _planner(settings).parse_task("Find dentists near Clifton Karachi with emails.")
    assert intent.business_type == "dentists"
    assert intent.location == "Clifton Karachi"
    assert intent.wants_emails is True


def test_parses_website_intent(settings) -> None:
    intent = _planner(settings).parse_task("Find software houses in Lahore having websites.")
    assert intent.business_type == "software houses"
    assert intent.location == "Lahore"
    assert intent.wants_websites is True


def test_parses_minimum_rating(settings) -> None:
    intent = _planner(settings).parse_task(
        "I need restaurants in Islamabad with more than 4.5 rating."
    )
    assert intent.business_type == "restaurants"
    assert intent.location == "Islamabad"
    assert intent.min_rating == 4.5


def test_parses_phone_intent(settings) -> None:
    intent = _planner(settings).parse_task("Find clinics with phone numbers in Karachi")
    assert intent.wants_phones is True


def test_empty_task_raises(settings) -> None:
    with pytest.raises(PlanningError):
        _planner(settings).parse_task("   ")


def test_task_without_location_raises(settings) -> None:
    with pytest.raises(PlanningError):
        _planner(settings).parse_task("garbage without location")


def test_default_plan_includes_search_and_export(settings) -> None:
    plan = _planner(settings).plan("dentists near Clifton Karachi")
    assert plan.tool_sequence[-1] == "lead_exporter"
    assert plan.tool_sequence[0] == "google_maps_search"


def test_email_plan_includes_email_extractor(settings) -> None:
    plan = _planner(settings).plan("dentists near Clifton Karachi with emails")
    assert "email_extractor" in plan.tool_sequence


def test_rating_plan_includes_business_details(settings) -> None:
    plan = _planner(settings).plan("restaurants in Islamabad with more than 4.5 rating")
    assert "business_details" in plan.tool_sequence


def test_default_plan_does_not_include_unrequested_extractors(settings) -> None:
    plan = _planner(settings).plan("dentists near Clifton Karachi")
    assert "email_extractor" not in plan.tool_sequence
    assert "website_crawler" not in plan.tool_sequence


def test_plan_uses_llm_tool_selection_when_registry_available(settings) -> None:
    from app.tools.base import ToolContext
    from app.tools.registry import build_default_registry

    registry = build_default_registry(ToolContext(settings=settings))
    llm = _ScriptedLLM()
    plan = _planner(settings).plan("dentists near Karachi", llm=llm, registry=registry)
    assert plan.tool_sequence[0] == "google_maps_search"
    assert "email_extractor" in plan.tool_sequence


def test_plan_skips_llm_for_mock_provider(settings) -> None:
    from app.llm.mock_provider import MockProvider

    plan = _planner(settings).plan("dentists near Karachi", llm=MockProvider())
    assert "email_extractor" not in plan.tool_sequence


def test_plan_falls_back_when_llm_output_is_garbage(settings) -> None:
    from app.tools.base import ToolContext
    from app.tools.registry import build_default_registry

    registry = build_default_registry(ToolContext(settings=settings))
    plan = _planner(settings).plan(
        "dentists near Karachi", llm=_ScriptedLLM("this is not json"), registry=registry
    )
    assert plan.tool_sequence[-1] == "lead_exporter"


def test_plan_falls_back_when_llm_names_unknown_tools(settings) -> None:
    from app.tools.base import ToolContext
    from app.tools.registry import build_default_registry

    registry = build_default_registry(ToolContext(settings=settings))
    llm = _ScriptedLLM('{"tool_calls": ["not_a_tool", "also_missing"]}')
    plan = _planner(settings).plan("dentists near Karachi", llm=llm, registry=registry)
    assert plan.tool_sequence[0] == "google_maps_search"
    assert plan.tool_sequence[-1] == "lead_exporter"


def test_intent_keeps_original_text(settings) -> None:
    intent = _planner(settings).parse_task("  Find dentists near Clifton  ")
    assert intent.original == "Find dentists near Clifton"


def test_to_execution_plan_maps_basic_task(settings) -> None:
    plan = _planner(settings).plan("dentists near Clifton Karachi")
    view = _planner(settings).to_execution_plan(plan)

    assert view.original_prompt == "dentists near Clifton Karachi"
    assert view.business_type == "dentists"
    assert view.location == "Clifton Karachi"
    assert view.provider == "google"
    assert view.export is True
    assert view.needs_website_crawl is False
    assert view.step_count == len(plan.steps)
    assert view.steps


def test_to_execution_plan_marks_website_crawl_when_requested(settings) -> None:
    plan = _planner(settings).plan("dentists near Karachi with emails and websites")
    view = _planner(settings).to_execution_plan(plan)

    assert view.needs_website_crawl is True


def test_agent_facade_plan_methods(settings) -> None:
    from app.agent.lead_generation_agent import LeadGenerationAgent

    agent = LeadGenerationAgent(settings=settings)
    plan = agent.plan("dentists near Clifton Karachi")

    assert plan is not None
    view = agent.to_execution_plan(plan)
    assert view.business_type == "dentists"
    assert view.step_count >= 2


def test_agent_facade_run_accepts_precomputed_plan(fixed_settings, browser, caplog) -> None:
    from app.agent.lead_generation_agent import LeadGenerationAgent
    from app.models.lead import Lead
    from tests.fakes import build_fixed_factory

    leads = [
        Lead(
            business_name="Alpha Cafe",
            phone_number="+92 300 1234567",
            website="https://alpha.example",
            provider="fixed",
            search_query="coffee shops in Karachi",
        )
    ]
    factory = build_fixed_factory(fixed_settings, browser, leads)
    agent = LeadGenerationAgent(settings=fixed_settings, factory=factory)
    plan = agent.plan("coffee shops in Karachi")

    with caplog.at_level("INFO"):
        result = agent.run("coffee shops in Karachi", plan=plan)

    assert result.success
    assert result.processed_leads == 1
    assert "Starting agent loop" in " ".join(record.message for record in caplog.records)


@pytest.mark.parametrize(
    ("query", "expected_type", "expected_location"),
    [
        ("find me best skin specialist in karachi", "skin specialist", "karachi"),
        ("software companies in islamabad", "software companies", "islamabad"),
        ("skin specialist in karachi", "skin specialist", "karachi"),
        ("coffee shops in california", "coffee shops", "california"),
        ("dentists in lahore", "dentists", "lahore"),
    ],
)
def test_regression_query_matrix(settings, query, expected_type, expected_location) -> None:
    """Every known query must yield its own plan, never a previous one."""
    plan = _planner(settings).plan(query)
    assert plan.intent.business_type == expected_type
    assert plan.intent.location == expected_location


def test_parses_quality_filler_words(settings) -> None:
    intent = _planner(settings).parse_task("find me best skin specialist in karachi")
    assert intent.business_type == "skin specialist"
    assert intent.location == "karachi"


def test_consecutive_searches_never_reuse_previous_plan(settings) -> None:
    """Running multiple searches in a row must produce independent plans."""
    queries = [
        ("software companies in islamabad", "software companies", "islamabad"),
        ("skin specialist in karachi", "skin specialist", "karachi"),
        ("coffee shops in california", "coffee shops", "california"),
        ("dentists in lahore", "dentists", "lahore"),
    ]
    planner = _planner(settings)
    previous = set()
    for query, expected_type, expected_location in queries:
        plan = planner.plan(query)
        assert (plan.intent.business_type, plan.intent.location) not in previous
        assert plan.intent.business_type == expected_type
        assert plan.intent.location == expected_location
        previous.add((plan.intent.business_type, plan.intent.location))


def test_stale_llm_plan_cannot_contaminate_consecutive_searches(settings) -> None:
    """A stale LLM reply must never override the current query's plan."""
    planner = _planner(settings)
    llm = _StaleLLM()
    for query, expected_type, expected_location in [
        ("find me best skin specialist in karachi", "skin specialist", "karachi"),
        ("software companies in islamabad", "software companies", "islamabad"),
        ("skin specialist in karachi", "skin specialist", "karachi"),
        ("coffee shops in california", "coffee shops", "california"),
        ("dentists in lahore", "dentists", "lahore"),
    ]:
        plan = planner.plan(query, llm=llm, registry=_FakeRegistry())
        assert plan.intent.business_type == expected_type
        assert plan.intent.location == expected_location


def test_llm_plan_reflecting_the_task_is_accepted(settings) -> None:
    """A genuine LLM plan matching the query is still honored."""
    llm = _CapturingLLM()
    plan = _planner(settings).plan(
        "find me best skin specialist in karachi", llm=llm, registry=_FakeRegistry()
    )
    assert plan.intent.business_type == "skin specialist"
    assert plan.intent.location == "Karachi"
    assert "email_extractor" in plan.tool_sequence


def test_planning_prompt_contains_no_previous_example_values(settings) -> None:
    """The planning prompt must be stateless and contain no example searches."""
    llm = _CapturingLLM()
    _planner(settings).plan(
        "find me best skin specialist in karachi", llm=llm, registry=_FakeRegistry()
    )
    planning_prompt = llm.prompts[0]
    assert "dentists" not in planning_prompt.lower()
    assert "clifton" not in planning_prompt.lower()


def test_planning_prompt_is_stateless_across_searches(settings) -> None:
    """Two different queries must produce different, history-free prompts."""
    llm = _CapturingLLM()
    planner = _planner(settings)
    registry = _FakeRegistry()
    planner.plan("dentists in lahore", llm=llm, registry=registry)
    planner.plan("coffee shops in california", llm=llm, registry=registry)
    planning_prompts = [llm.prompts[i] for i in range(0, len(llm.prompts), 2)]
    assert len(planning_prompts) == 2
    assert planning_prompts[0] != planning_prompts[1]


def test_agent_facade_plan_ignores_stale_llm_output(settings) -> None:
    from app.agent.lead_generation_agent import LeadGenerationAgent

    agent = LeadGenerationAgent(settings=settings, llm=_StaleLLM())
    plan = agent.plan("find me best skin specialist in karachi")
    assert plan is not None
    assert plan.intent.business_type == "skin specialist"
    assert plan.intent.location == "karachi"
