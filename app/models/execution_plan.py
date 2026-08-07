"""Execution plan data model.

The ExecutionPlan is the user-facing view of what the agent decided to do: the
business type, location, provider, expected number of results, whether website
crawling is needed, and the ordered tool steps. It is what the GUI renders
before a run starts.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    """A structured, displayable view of a planned run."""

    original_prompt: str
    business_type: str
    location: str
    provider: str
    expected_results: int
    needs_website_crawl: bool = False
    export: bool = True
    steps: tuple[str, ...] = ()

    @property
    def step_count(self) -> int:
        """Return the number of planned tool steps."""
        return len(self.steps)
