"""Tests for the command-line entry point (app/main.py).

Two layers are covered: the argument forwarding logic in ``main()`` is tested
in-process with a stubbed application, and the real process behaviour (exit
codes, interactive prompt, console output) is tested through the subprocess
helper in ``tests/conftest.py``. Subprocess runs use the placeholder provider
so no browser or network is ever involved.
"""

import sys

import pytest

from app import main as app_main
from tests.conftest import run_cli

# --- main() argument forwarding ---------------------------------------------


class _FakeApplication:
    def __init__(self) -> None:
        self.prompts: list[str | None] = []

    def run(self, prompt: str | None) -> int:
        self.prompts.append(prompt)
        return 0


def test_main_forwards_first_argument(monkeypatch: pytest.MonkeyPatch) -> None:
    application = _FakeApplication()
    monkeypatch.setattr(app_main, "LeadGenerationApplication", lambda: application)
    monkeypatch.setattr(sys, "argv", ["app/main.py", "coffee shops in America"])

    exit_code = app_main.main()

    assert exit_code == 0
    assert application.prompts == ["coffee shops in America"]


def test_main_passes_none_when_no_argument(monkeypatch: pytest.MonkeyPatch) -> None:
    application = _FakeApplication()
    monkeypatch.setattr(app_main, "LeadGenerationApplication", lambda: application)
    monkeypatch.setattr(sys, "argv", ["app/main.py"])

    app_main.main()

    assert application.prompts == [None]


def test_main_returns_application_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingApplication:
        def run(self, prompt: str | None) -> int:
            return 7

    monkeypatch.setattr(app_main, "LeadGenerationApplication", FailingApplication)
    monkeypatch.setattr(sys, "argv", ["app/main.py", "software companies in Karachi"])

    assert app_main.main() == 7


# --- Real process behaviour --------------------------------------------------


def test_cli_returns_zero_on_successful_run() -> None:
    result = run_cli(
        "software companies in Karachi",
        SEARCH_PROVIDER="yelp",
    )

    assert result.returncode == 0
    assert "Lead Generation Completed Successfully" in result.stdout
    assert "Search Query: software companies in Karachi" in result.stdout
    assert "Business Type: software companies" in result.stdout


def test_cli_returns_nonzero_on_unparseable_prompt() -> None:
    result = run_cli("garbage without location")

    assert result.returncode == 1
    assert "Lead Generation Failed" in result.stdout


def test_cli_reads_prompt_from_console_when_no_argument() -> None:
    result = run_cli(input="no location here\n", SEARCH_PROVIDER="yelp")

    assert result.returncode == 1
    assert "Lead Generation Failed" in result.stdout
