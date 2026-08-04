"""Tests for the Playwright browser infrastructure."""

from pathlib import Path

import pytest

from app.browser.browser_factory import BrowserFactory
from app.browser.browser_manager import BrowserManager
from app.browser.browser_session import BrowserSession
from app.browser.page_manager import PageManager
from app.config.settings import Settings
from app.exceptions.browser_exception import BrowserException


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        headless=True,
        timeout=30_000,
        max_leads=25,
        search_provider="google",
        browser_type="chromium",
        output_dir=tmp_path / "outputs",
        log_dir=tmp_path / "logs",
        log_level="INFO",
    )


def test_browser_launches_and_tracks_state(settings: Settings) -> None:
    manager = BrowserManager(settings=settings)
    assert not manager.is_running()
    try:
        page = manager.launch()
        assert manager.is_running()
        assert page is not None
        assert page.url == "about:blank"
    finally:
        manager.close()
    assert not manager.is_running()


def test_browser_closes_and_releases_state(settings: Settings) -> None:
    manager = BrowserManager(settings=settings)
    manager.launch()
    assert manager.is_running()
    manager.close()
    assert not manager.is_running()


def test_multiple_launches_are_prevented(settings: Settings) -> None:
    manager = BrowserManager(settings=settings)
    try:
        manager.launch()
        with pytest.raises(BrowserException):
            manager.launch()
    finally:
        manager.close()


def test_multiple_closes_are_safe(settings: Settings) -> None:
    manager = BrowserManager(settings=settings)
    manager.close()
    manager.close()
    assert not manager.is_running()


def test_new_page_creation_works(settings: Settings) -> None:
    manager = BrowserManager(settings=settings)
    try:
        first = manager.launch()
        second = manager.new_page()
        assert first is not None
        assert second is not None
        assert not second.is_closed()
        assert manager.active_page() is second
    finally:
        manager.close()


def test_navigation_to_about_blank_works(settings: Settings) -> None:
    manager = BrowserManager(settings=settings)
    try:
        manager.launch()
        manager.navigate_to("about:blank")
        assert manager.active_page().url == "about:blank"
    finally:
        manager.close()


def test_repeated_open_close_cycles(settings: Settings) -> None:
    manager = BrowserManager(settings=settings)
    for _ in range(2):
        manager.launch()
        manager.navigate_to("about:blank")
        manager.close()
        assert not manager.is_running()


def test_session_creates_context_and_releases_resources(settings: Settings) -> None:
    session = BrowserSession(BrowserFactory(settings))
    page = session.open()
    assert session.browser is not None
    assert session.context is not None
    assert session.page is page
    assert session.is_open

    session.close()
    assert not session.is_open
    assert session.browser is None
    assert session.context is None
    assert session.page is None


def test_session_rejects_double_open(settings: Settings) -> None:
    session = BrowserSession(BrowserFactory(settings))
    try:
        session.open()
        with pytest.raises(BrowserException):
            session.open()
    finally:
        session.close()


def test_page_manager_waits_for_load_and_closes_page(settings: Settings) -> None:
    session = BrowserSession(BrowserFactory(settings))
    pages = PageManager(session, settings)
    try:
        session.open()
        pages.navigate("about:blank")
        pages.wait_for_load()
        assert session.page is not None
        pages.close_page()
        assert session.page is None
    finally:
        session.close()
    assert not session.is_open
