"""Retry decorator with exponential backoff."""

import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Retry a callable on failure with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts before giving up.
        delay: Initial delay in seconds between attempts.
        backoff: Factor by which the delay grows after each attempt.
        exceptions: Exception types that trigger a retry.

    Returns:
        A decorator wrapping the callable with retry behaviour.

    Raises:
        The last exception raised by the wrapped callable.
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            wait = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == max_attempts:
                        raise
                    logger.warning(
                        "Attempt %d/%d failed for '%s': %s. Retrying in %.1fs.",
                        attempt,
                        max_attempts,
                        func.__name__,
                        exc,
                        wait,
                    )
                    time.sleep(wait)
                    wait *= backoff
            raise RuntimeError("Unreachable retry state")

        return wrapper

    return decorator
