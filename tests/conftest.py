"""Shared fixtures and helpers for the whole test suite.

The fixtures here are deliberately reusable across unit, integration,
end-to-end, and requirement tests: a tmp-directory-based Settings, a
FakeBrowser, and a factory that serves a fixed set of leads through the
``fixed`` provider so full runs can be exercised without a browser or network.
"""

import os
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

import pytest

from app.config.settings import Settings
from app.models.lead import Lead
from app.providers.provider_factory import ProviderFactory
from tests.fakes import FakeBrowser, build_fixed_factory

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAIN_SCRIPT = PROJECT_ROOT / "app" / "main.py"


def make_settings(
    tmp_path: Path,
    *,
    headless: bool = True,
    timeout: int = 30_000,
    max_leads: int = 25,
    search_provider: str = "google",
    browser_type: str = "chromium",
    log_level: str = "INFO",
) -> Settings:
    """Build a Settings instance rooted in a temporary directory."""
    return Settings(
        headless=headless,
        timeout=timeout,
        max_leads=max_leads,
        search_provider=search_provider,
        browser_type=browser_type,
        output_dir=tmp_path / "outputs",
        log_dir=tmp_path / "logs",
        log_level=log_level,
    )


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Default settings isolated in a temporary directory."""
    return make_settings(tmp_path)


@pytest.fixture
def fixed_settings(tmp_path: Path) -> Settings:
    """Settings that select the 'fixed' test provider by default."""
    return make_settings(tmp_path, search_provider="fixed")


@pytest.fixture
def browser() -> FakeBrowser:
    """A fresh FakeBrowser that never touches a real browser."""
    return FakeBrowser()


@pytest.fixture
def fixed_factory(
    fixed_settings: Settings, browser: FakeBrowser
) -> Callable[[list[Lead]], ProviderFactory]:
    """Build a factory that serves the given leads through the 'fixed' provider."""

    def build(leads: list[Lead]) -> ProviderFactory:
        return build_fixed_factory(fixed_settings, browser, leads)

    return build


def run_cli(
    *args: str,
    timeout: int = 60,
    input: str | None = None,
    **env_overrides: str,
) -> subprocess.CompletedProcess[str]:
    """Run the real application entry point in a subprocess.

    Environment variables redirect output and logs into a fresh temporary
    directory so a run never writes inside the repository root. ``timeout`` is
    the subprocess wall-clock limit, not the browser timeout. Extra
    ``env_overrides`` are merged on top of the safe defaults.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        env = os.environ.copy()
        env["HEADLESS"] = "true"
        env["SEARCH_PROVIDER"] = "google"
        env["OUTPUT_DIR"] = os.path.join(temp_dir, "outputs")
        env["LOG_DIR"] = os.path.join(temp_dir, "logs")
        env.update(env_overrides)
        return subprocess.run(
            [sys.executable, str(MAIN_SCRIPT), *args],
            cwd=PROJECT_ROOT,
            env=env,
            input=input,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
