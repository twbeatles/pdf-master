from __future__ import annotations

import logging
import time
from functools import wraps
from typing import Callable, ParamSpec, TypeVar

from .config import AI_BASE_DELAY, AI_MAX_DELAY, AI_MAX_RETRIES

logger = logging.getLogger(__name__)
P = ParamSpec("P")
T = TypeVar("T")


class AIServiceError(Exception):
    pass


class APIKeyError(AIServiceError):
    pass


class APITimeoutError(AIServiceError):
    pass


class APIRateLimitError(AIServiceError):
    pass


def retry_with_backoff(
    max_retries: int = AI_MAX_RETRIES,
    base_delay: float = AI_BASE_DELAY,
    max_delay: float = AI_MAX_DELAY,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    import random

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_error: Exception | None = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_error = exc
                    error_text = str(exc).lower()
                    if any(token in error_text for token in ("api key", "authentication", "invalid api key")):
                        raise APIKeyError(str(exc)) from exc
                    if any(token in error_text for token in ("rate limit", "quota", "429")):
                        if attempt >= max_retries:
                            raise APIRateLimitError(str(exc)) from exc
                    if attempt >= max_retries:
                        raise
                    delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
                    logger.warning("AI call failed, retrying in %.1fs: %s", delay, exc)
                    time.sleep(delay)
            if last_error is not None:
                raise last_error
            raise RuntimeError("retry loop exited without returning")

        return wrapper

    return decorator


__all__ = [
    "AIServiceError",
    "APIKeyError",
    "APITimeoutError",
    "APIRateLimitError",
    "retry_with_backoff",
]
