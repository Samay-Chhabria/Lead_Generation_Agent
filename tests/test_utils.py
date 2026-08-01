"""Tests for shared utility helpers."""

import logging

import pytest

from app.utils.helpers import ensure_directory
from app.utils.retry import retry
from app.utils.timer import Timer


def test_retry_succeeds_after_failures() -> None:
    calls = {"count": 0}

    @retry(max_attempts=3, delay=0.0, exceptions=(ValueError,))
    def flaky() -> str:
        calls["count"] += 1
        if calls["count"] < 3:
            raise ValueError("boom")
        return "ok"

    assert flaky() == "ok"
    assert calls["count"] == 3


def test_retry_raises_after_exhaustion() -> None:
    @retry(max_attempts=2, delay=0.0)
    def always_fails() -> None:
        raise ValueError("boom")

    with pytest.raises(ValueError):
        always_fails()


def test_timer_measures_elapsed() -> None:
    with Timer("sample", log=logging.getLogger("tests")) as timer:
        pass
    assert timer.elapsed >= 0.0


def test_ensure_directory_creates_nested_paths(tmp_path) -> None:
    target = tmp_path / "a" / "b"
    result = ensure_directory(target)

    assert result == target
    assert target.is_dir()


def test_ensure_directory_is_idempotent(tmp_path) -> None:
    target = tmp_path / "existing"
    target.mkdir()

    assert ensure_directory(target) == target
