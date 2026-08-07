"""Tests for the agent's failure-recovery behaviour.

The agent is expected to recover from flaky infrastructure instead of dying: a
failed navigation is retried once, consent dialogs are dismissed after load, and
a business listing that cannot be opened is skipped so the remaining businesses
still get processed. These tests exercise that behaviour with the Playwright
fakes, no browser or network required.
"""

import pytest

from app.browser.page_manager import PageManager
from app.config.settings import Settings
from app.exceptions import ExtractionException
from app.exceptions.browser_exception import BrowserException
from app.extractor.business_navigator import OPEN_ATTEMPTS, BusinessNavigator
from app.models.business_reference import BusinessReference
from app.models.lead import Lead
from app.tools.base import ToolContext
from app.tools.business_details_tool import BusinessDetailsTool
from tests.fakes import FakeBrowser, FakePage

PROMPT = "coffee shops in Karachi"


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
    )


class _FakeSession:
    """A BrowserSession stand-in exposing just the page the PageManager needs."""

    def __init__(self, page: FakePage) -> None:
        self.page = page

    def close_page(self) -> None:
        self.page = None


class _FlakyPage(FakePage):
    """A page whose navigation fails the first N times, then succeeds."""

    def __init__(self, failures: int = 1, **kwargs) -> None:
        super().__init__(**kwargs)
        self._failures = failures
        self.goto_calls = 0

    def goto(self, url, wait_until="load", timeout=None):
        self.goto_calls += 1
        if self.goto_calls <= self._failures:
            raise TimeoutError(f"first {self._failures} navigations fail")
        super().goto(url, wait_until=wait_until, timeout=timeout)


def _reference(name: str = "Alpha Cafe", url: str = "https://maps.example/1") -> BusinessReference:
    return BusinessReference(
        business_id=url,
        business_name=name,
        listing_url=url,
        listing_index=0,
        provider="google",
    )


def _lead(name: str = "Alpha Cafe") -> Lead:
    return Lead(
        business_name=name,
        source_url="https://maps.example/1",
        provider="fixed",
        search_query=PROMPT,
    )


def test_page_manager_navigate_retries_then_succeeds(settings) -> None:
    page = _FlakyPage(failures=1)
    manager = PageManager(_FakeSession(page), settings)

    manager.navigate("https://example.com")

    assert page.visited_url == "https://example.com"
    assert page.goto_calls == 2


def test_page_manager_navigate_fails_after_exhausting_attempts(settings) -> None:
    page = FakePage(goto_error=RuntimeError("network down"))
    manager = PageManager(_FakeSession(page), settings)

    with pytest.raises(BrowserException, match="failed"):
        manager.navigate("https://example.com")


def test_page_manager_dismisses_consent_dialog_after_load(settings) -> None:
    page = FakePage()
    page.semantic.add('role=button:name="Accept all"')
    manager = PageManager(_FakeSession(page), settings)

    dismissed = manager.dismiss_consent_popups(page)

    assert dismissed is True
    assert page.clicks


def test_page_manager_reports_no_consent_dialog(settings) -> None:
    page = FakePage()
    for text in ("Accept all", "Accept", "I agree", "Agree", "Accept cookies"):
        page.missing.update(
            {
                f'button:has-text("{text}")',
                f'[role="button"]:has-text("{text}")',
            }
        )
    manager = PageManager(_FakeSession(page), settings)

    assert manager.dismiss_consent_popups(page) is False


def test_navigator_open_retries_then_succeeds(settings) -> None:
    page = _FlakyPage(failures=1)
    navigator = BusinessNavigator(settings=settings)

    navigator.open(_reference(), page)

    assert page.visited_url == "https://maps.example/1"
    assert page.goto_calls == 2


def test_navigator_open_raises_when_always_failing(settings) -> None:
    page = FakePage(goto_error=RuntimeError("network down"))
    navigator = BusinessNavigator(settings=settings)

    with pytest.raises(Exception, match="Failed to open"):
        navigator.open(_reference(), page)


def test_navigator_open_uses_two_attempts(settings) -> None:
    page = FakePage(goto_error=RuntimeError("network down"))
    navigator = BusinessNavigator(settings=settings)

    with pytest.raises(ExtractionException):
        navigator.open(_reference(), page)

    assert OPEN_ATTEMPTS == 2


def test_business_details_skips_unreachable_business(fixed_settings) -> None:
    page = FakePage(goto_error=RuntimeError("network down"))
    browser = FakeBrowser(page=page)
    context = ToolContext(browser=browser, settings=fixed_settings)
    tool = BusinessDetailsTool(context)

    result = tool.run(leads=[_lead()])

    assert result.success
    assert result.data["leads"] == []
    assert browser.close_count == 0


def test_business_details_keeps_processing_after_one_skip(fixed_settings) -> None:
    page = FakePage(goto_error=RuntimeError("network down"))
    browser = FakeBrowser(page=page)
    context = ToolContext(browser=browser, settings=fixed_settings)
    tool = BusinessDetailsTool(context)

    result = tool.run(leads=[_lead("Unreachable"), _lead("Also Unreachable")])

    assert result.success
    assert result.data["leads"] == []
