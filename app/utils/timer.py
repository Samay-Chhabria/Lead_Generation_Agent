"""Timing utilities."""

import logging
import time
from types import TracebackType

logger = logging.getLogger(__name__)


class Timer:
    """Context manager that measures elapsed time and logs the result.

    Usage:
        with Timer("search") as timer:
            ...
        print(timer.elapsed)
    """

    def __init__(self, name: str, log: logging.Logger | None = None) -> None:
        self._name = name
        self._logger = log or logger
        self.elapsed: float = 0.0
        self._started: float | None = None

    def __enter__(self) -> "Timer":
        self._started = time.perf_counter()
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_value: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        start = self._started if self._started is not None else time.perf_counter()
        self.elapsed = time.perf_counter() - start
        self._logger.info("Timer '%s' completed in %.3f seconds.", self._name, self.elapsed)
