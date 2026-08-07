"""Planner: turns a natural-language task into an executable plan.

The planner is the agent's reasoning layer. It is LLM-first: when a real LLM
provider is configured it asks the model to produce the full plan — business
type, location, and the tool sequence — and validates the reply against the
tool registry. Any failure (unparseable output, unknown tools, missing API key)
falls back to the deterministic parser and default tool steps, so planning
always works, including fully offline with the default MockProvider.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from app.agent.state import AgentStep
from app.config.logging_config import get_logger
from app.config.settings import Settings, get_settings
from app.exceptions.llm_exception import PlanningError
from app.llm.base import LLMProvider, ToolMessage, parse_json_objects
from app.models.execution_plan import ExecutionPlan

_SEPARATOR_PATTERN = re.compile(r"\b(in|near|around|at)\b", re.IGNORECASE)
_EMAIL_CLAUSE = re.compile(r"\b(with\s+|having\s+|that\s+have\s+)?emails?\b", re.IGNORECASE)
_WEBSITE_CLAUSE = re.compile(r"\b(having\s+|with\s+|that\s+have\s+)?websites?\b", re.IGNORECASE)
_PHONE_CLAUSE = re.compile(
    r"\b(with\s+|having\s+|and\s+)?(phone|contact\s+numbers?|telephone)\b", re.IGNORECASE
)
_RATING_CLAUSE = re.compile(
    r"\bwith\s+(?:(?:more\s+than|above|greater\s+than|over|at\s+least|min(?:imum)?)\s+)?"
    r"(\d+(?:\.\d+)?)\s*(?:stars?\s*)?(?:rating|out\s+of)\b",
    re.IGNORECASE,
)
_LEADING_FILLERS = {
    "a",
    "an",
    "any",
    "best",
    "find",
    "for",
    "get",
    "give",
    "good",
    "great",
    "i",
    "i'd",
    "i'm",
    "list",
    "me",
    "need",
    "please",
    "search",
    "show",
    "some",
    "the",
    "to",
    "top",
    "want",
    "looking",
}

# LLM mode is skipped for the default offline provider.
_LLM_SKIPPED_PROVIDERS = {"mock"}


@dataclass(frozen=True, slots=True)
class TaskIntent:
    """Structured understanding of the user's request."""

    original: str
    business_type: str
    location: str
    wants_emails: bool = False
    wants_websites: bool = False
    wants_phones: bool = False
    min_rating: float | None = None

    def __str__(self) -> str:
        return (
            f"TaskIntent(business_type={self.business_type!r}, location={self.location!r}, "
            f"emails={self.wants_emails}, websites={self.wants_websites}, "
            f"phones={self.wants_phones}, min_rating={self.min_rating})"
        )


@dataclass(slots=True)
class TaskPlan:
    """An intent plus the ordered steps that will satisfy it."""

    intent: TaskIntent
    steps: list[AgentStep] = field(default_factory=list)

    @property
    def tool_sequence(self) -> list[str]:
        """Return the ordered tool names in this plan."""
        return [step.tool for step in self.steps]


class Planner:
    """Analyze a task and produce an executable plan."""

    def __init__(
        self,
        settings: Settings | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._logger = logger or get_logger("agent.planner")

    def plan(
        self,
        task: str,
        llm: LLMProvider | None = None,
        registry: Any | None = None,
    ) -> TaskPlan:
        """Turn a task into a plan of tool steps.

        The intent is always parsed deterministically. Tool selection is then
        delegated to the LLM when one is provided and it is not the offline
        mock; any failure silently falls back to the deterministic steps.

        Args:
            task: The user's natural-language request.
            llm: Optional LLM provider used for tool selection.
            registry: Optional tool registry used to validate tool names.

        Returns:
            The TaskPlan to execute.

        Raises:
            PlanningError: When the task cannot be parsed into an intent.
        """
        if llm is not None and getattr(llm, "name", "") not in _LLM_SKIPPED_PROVIDERS:
            try:
                plan = self._plan_from_llm(task, llm, registry)
                if plan is not None:
                    self._logger.info(
                        "LLM produced the plan: %s",
                        " -> ".join(step.tool for step in plan.steps),
                    )
                    return plan
            except Exception as exc:
                self._logger.warning("LLM planning failed (%s); using deterministic plan.", exc)
        intent = self.parse_task(task)
        self._logger.info("Task understood: %s", intent)
        steps = self._select_steps(intent, llm, registry)
        self._logger.info("Plan created: %s", " -> ".join(step.tool for step in steps))
        return TaskPlan(intent=intent, steps=steps)

    def to_execution_plan(self, plan: TaskPlan) -> ExecutionPlan:
        """Build the displayable ExecutionPlan from a TaskPlan.

        Args:
            plan: The executable plan produced by ``plan``.

        Returns:
            An ExecutionPlan with the fields the GUI renders.
        """
        intent = plan.intent
        steps = plan.tool_sequence
        needs_crawl = intent.wants_emails or intent.wants_websites
        needs_crawl = needs_crawl or "website_crawler" in steps
        return ExecutionPlan(
            original_prompt=intent.original,
            business_type=intent.business_type,
            location=intent.location,
            provider=self._settings.search_provider,
            expected_results=self._settings.max_leads,
            needs_website_crawl=needs_crawl,
            export=True,
            steps=tuple(steps),
        )

    def parse_task(self, task: str) -> TaskIntent:
        """Parse a task into a structured intent.

        Raises:
            PlanningError: When the task is empty or has no location.
        """
        normalized = " ".join(str(task or "").split())
        if not normalized:
            raise PlanningError("Task is empty.")
        lowered = normalized.lower()

        wants_emails = bool(_EMAIL_CLAUSE.search(lowered))
        wants_websites = bool(_WEBSITE_CLAUSE.search(lowered))
        wants_phones = bool(_PHONE_CLAUSE.search(lowered))
        min_rating = self._extract_min_rating(lowered)

        text = normalized
        text = _RATING_CLAUSE.sub(" ", text)
        text = _EMAIL_CLAUSE.sub(" ", text)
        text = _WEBSITE_CLAUSE.sub(" ", text)
        text = _PHONE_CLAUSE.sub(" ", text)

        match = _SEPARATOR_PATTERN.search(text)
        if match is None:
            raise PlanningError(
                f"Could not understand task '{task}'. Use a phrase like "
                "'Find dentists near Clifton Karachi'."
            )
        business_type = self._clean_fillers(text[: match.start()])
        location = " ".join(text[match.end() :].strip().strip(".,;:!?").split())
        if not business_type:
            raise PlanningError(f"Could not determine the business type from '{task}'.")
        if not location:
            raise PlanningError(f"Could not determine the location from '{task}'.")

        return TaskIntent(
            original=normalized,
            business_type=business_type,
            location=location,
            wants_emails=wants_emails,
            wants_websites=wants_websites,
            wants_phones=wants_phones,
            min_rating=min_rating,
        )

    def build_steps(self, intent: TaskIntent, max_results: int | None = None) -> list[AgentStep]:
        """Build the deterministic default steps for an intent."""
        limit = max_results or self._settings.max_leads
        steps = [
            AgentStep(
                tool="google_maps_search",
                description=f"Search Google Maps for {intent.business_type} in {intent.location}.",
                arguments={
                    "business_type": intent.business_type,
                    "location": intent.location,
                    "max_results": limit,
                },
                reason="The search finds the candidate businesses for the task.",
            )
        ]
        if intent.min_rating is not None:
            steps.append(
                AgentStep(
                    tool="business_details",
                    description="Open each business and extract detailed information.",
                    arguments={"search_query": f"{intent.business_type} in {intent.location}"},
                    reason=(
                        f"The user wants businesses rated above {intent.min_rating}, "
                        "so each listing is reopened to read its rating."
                    ),
                )
            )
        if intent.wants_websites:
            steps.append(
                AgentStep(
                    tool="website_crawler",
                    description="Crawl each business website for contact emails.",
                    arguments={},
                    reason="The user asked for businesses with websites.",
                )
            )
        if intent.wants_emails:
            steps.append(
                AgentStep(
                    tool="email_extractor",
                    description="Extract email addresses from business pages.",
                    arguments={},
                    reason="The user asked for businesses with emails.",
                )
            )
        if intent.wants_phones:
            steps.append(
                AgentStep(
                    tool="phone_extractor",
                    description="Extract phone numbers for each business.",
                    arguments={},
                    reason="The user asked for phone numbers.",
                )
            )
        steps.append(
            AgentStep(
                tool="lead_exporter",
                description="Export the collected leads to an Excel workbook.",
                arguments={
                    "business_type": intent.business_type,
                    "location": intent.location,
                },
                reason="Export is the final deliverable of every task.",
            )
        )
        return steps

    def _select_steps(
        self,
        intent: TaskIntent,
        llm: LLMProvider | None,
        registry: Any | None,
    ) -> list[AgentStep]:
        """Choose the step list, preferring LLM-selected tools when possible."""
        default = self.build_steps(intent)
        if llm is None or getattr(llm, "name", "") in _LLM_SKIPPED_PROVIDERS:
            return default
        try:
            return self._steps_from_llm(intent, llm, registry, default)
        except Exception as exc:
            self._logger.warning("LLM planning failed (%s); using deterministic plan.", exc)
            return default

    def _plan_from_llm(
        self,
        task: str,
        llm: LLMProvider,
        registry: Any | None,
    ) -> TaskPlan | None:
        """Ask the LLM to produce the full plan; return None when unusable.

        The model is expected to reply with business type, location, wanted
        data flags, and a tool sequence. The intent and tool names are
        validated; a missing business type or location makes the reply
        unusable so the caller falls back to the deterministic parser. The
        prompt never embeds concrete example values — a model that echoes
        example business types or locations would otherwise surface stale
        values from a previous search as this run's plan. As a second guard,
        the reply is only accepted when its business type and location words
        actually come from the user's own request.

        Args:
            task: The user's natural-language request.
            llm: The real LLM provider.
            registry: The tool registry used to validate tool names.

        Returns:
            A TaskPlan, or None when the reply cannot be used.
        """
        if registry is None:
            return None
        catalog = registry.catalog()
        prompt = (
            "You are a lead generation agent. Your tools are:\n"
            f"{catalog}\n\n"
            f"The user wants: {task}\n\n"
            "Reply with ONLY a JSON object with these keys:\n"
            "- business_type: the business category, using the user's own wording\n"
            "- location: the place, using the user's own wording\n"
            '- provider: "google"\n'
            "- wants_emails, wants_websites, wants_phones: true only when the "
            "user asked for them\n"
            "- min_rating: a number, or null\n"
            "- tool_calls: an array of tool names from the list above, ending "
            'with "lead_exporter"\n'
            "For business_type and location use ONLY words that appear in the "
            "user's request. Every tool_calls entry must be a tool name from "
            "the list above."
        )
        self._logger.debug("LLM planning prompt:\n%s", prompt)
        completion = llm.generate([ToolMessage(role="user", content=prompt)])
        self._logger.debug("LLM planning response:\n%s", completion)
        payload = parse_json_objects(completion)[0]
        business_type = str(payload.get("business_type") or "").strip()
        location = str(payload.get("location") or "").strip()
        if not business_type or not location:
            return None
        intent = TaskIntent(
            original=" ".join(str(task or "").split()),
            business_type=business_type,
            location=location,
            wants_emails=bool(payload.get("wants_emails")),
            wants_websites=bool(payload.get("wants_websites")),
            wants_phones=bool(payload.get("wants_phones")),
            min_rating=_as_optional_float(payload.get("min_rating")),
        )
        if not _reflects_task(intent, task):
            self._logger.warning(
                "LLM plan does not reflect the user's request (%r); using the "
                "deterministic parser instead.",
                task,
            )
            return None
        default = self.build_steps(intent)
        tool_names = payload.get("tool_calls")
        if isinstance(tool_names, list) and tool_names:
            steps = self._steps_from_names(intent, tool_names, registry, default)
        else:
            steps = default
        self._logger.info("LLM produced intent: %s", intent)
        return TaskPlan(intent=intent, steps=steps)

    def _steps_from_llm(
        self,
        intent: TaskIntent,
        llm: LLMProvider,
        registry: Any,
        default: list[AgentStep],
    ) -> list[AgentStep]:
        """Ask the LLM to pick a tool sequence and map it to steps."""
        if registry is None:
            return default
        catalog = registry.catalog()
        prompt = (
            "You are a lead generation agent. Your tools are:\n"
            f"{catalog}\n\n"
            f"The user wants: {intent.original}\n\n"
            "Reply with ONLY a JSON object like "
            '{"thought": "short reason", "tool_calls": ["tool_a", "tool_b"]} '
            "choosing tool names from the list above. Always end with "
            '"lead_exporter".'
        )
        self._logger.debug("LLM tool-selection prompt:\n%s", prompt)
        completion = llm.generate([ToolMessage(role="user", content=prompt)])
        self._logger.debug("LLM tool-selection response:\n%s", completion)
        parsed = parse_json_objects(completion)
        tool_names = parsed[0].get("tool_calls") if parsed else []
        if not isinstance(tool_names, list) or not tool_names:
            return default
        self._logger.info("LLM selected tools: %s", tool_names)
        return self._steps_from_names(intent, tool_names, registry, default)

    def _steps_from_names(
        self,
        intent: TaskIntent,
        tool_names: list[str],
        registry: Any,
        default: list[AgentStep],
    ) -> list[AgentStep]:
        """Map LLM tool names to steps, validating against the registry."""
        by_tool = {step.tool: step for step in default}
        steps: list[AgentStep] = []
        for name in tool_names:
            if not registry.has(name):
                self._logger.debug("Ignoring unknown tool '%s' from LLM.", name)
                continue
            if name in by_tool:
                steps.append(by_tool[name])
                continue
            tool = registry.get(name)
            steps.append(
                AgentStep(
                    tool=name,
                    description=tool.description,
                    arguments={},
                    reason="Selected by the LLM for this task.",
                )
            )
        if not steps:
            return default
        if "lead_exporter" not in {step.tool for step in steps}:
            steps.append(by_tool["lead_exporter"])
        return steps

    @staticmethod
    def _extract_min_rating(lowered: str) -> float | None:
        """Extract a minimum rating threshold from the task text, if any."""
        match = _RATING_CLAUSE.search(lowered)
        if not match:
            return None
        try:
            return float(match.group(1))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _clean_fillers(phrase: str) -> str:
        """Strip leading filler words from a phrase."""
        words = (phrase or "").split()
        while words and words[0].strip("'\"").lower() in _LEADING_FILLERS:
            words = words[1:]
        cleaned = " ".join(words).strip().strip(".,;:!?")
        return cleaned or phrase.strip()


def _as_optional_float(value: Any) -> float | None:
    """Coerce an unknown value to a float, returning None when unusable."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _reflects_task(intent: TaskIntent, task: str) -> bool:
    """Return True when every intent word appears in the user's request.

    The LLM is instructed to use the user's own wording for ``business_type``
    and ``location``, so a reply that introduces words absent from the current
    request cannot describe this query. Rejecting it lets the planner fall back
    to the deterministic parser, which always parses only the task it is given
    and therefore can never reuse a previous search's values.
    """
    task_words = set(_words(task))
    for value in (intent.business_type, intent.location):
        for word in _words(value):
            if word.isdigit():
                continue
            if word not in task_words:
                return False
    return True


def _words(text: str) -> list[str]:
    """Return the lowercased alphanumeric words of a phrase."""
    return re.findall(r"[a-z0-9]+", (text or "").lower())
