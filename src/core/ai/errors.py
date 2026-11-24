from __future__ import annotations

import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from .config import AI_BASE_DELAY, AI_MAX_DELAY, AI_MAX_RETRIES
from .models import is_model_not_found_error

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


def _response_status_code(exc: BaseException) -> int:
    """SDK API 에러의 HTTP 상태 코드 (없으면 0)."""
    for attr in ("status_code", "code"):
        try:
            value = getattr(exc, attr, None)
            if isinstance(value, bool):
                continue
            code = int(value) if value is not None else 0
        except (TypeError, ValueError):
            continue
        if code:
            return code
    return 0


def _is_request_error(exc: BaseException) -> bool:
    """재시도해도 해결되지 않는 요청 자체의 오류 (400 계열)."""
    if _response_status_code(exc) == 400:
        return True
    text = str(exc).lower()
    return any(
        token in text
        for token in (
            "invalid argument",
            "invalid_argument",
            "bad request",
            "badrequest",
        )
    )


def _is_non_retryable(exc: BaseException) -> bool:
    """재시도하면 안 되는 예외 (취소·인증·모델 ID·400 등)."""
    if isinstance(exc, (APIKeyError, APITimeoutError)):
        return True
    # 400 계열(잘못된 요청·컨텍스트 초과 등)은 재시도해도 같은 결과가 나온다.
    try:
        if _is_request_error(exc):
            return True
    except Exception:
        pass
    # 모델 ID 문제(퇴역·오타·v1 미지원)는 같은 모델로 재시도해도 소용없음.
    # 호출 측 폴백 루프가 다른 모델로 전환하므로 여기서 즉시 중단한다.
    try:
        if is_model_not_found_error(exc):
            return True
    except Exception:
        pass
    # worker.CancelledError 등 순환 import 없이 이름/속성으로 판별
    if exc.__class__.__name__ == "CancelledError":
        return True
    error_text = str(exc).lower()
    if any(
        token in error_text
        for token in ("api key", "authentication", "invalid api key")
    ):
        return True
    if "취소" in str(exc) or "cancelled" in error_text or "canceled" in error_text:
        return True
    return False


def _interruptible_sleep(
    delay: float,
    cancel_check: Callable[[], None] | None,
    *,
    slice_seconds: float = 0.2,
) -> None:
    """delay 동안 짧게 쪼개 sleep하며 cancel_check를 호출한다."""
    if delay <= 0:
        if cancel_check is not None:
            cancel_check()
        return
    deadline = time.monotonic() + delay
    while True:
        if cancel_check is not None:
            cancel_check()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(slice_seconds, remaining))


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
            # 래핑 대상이 cancel_check 키워드를 받으면 재시도 sleep에도 전달
            raw_cancel = kwargs.get("cancel_check")
            cancel_cb: Callable[[], None] | None = None
            if callable(raw_cancel):

                def _bound_cancel(cb: Callable[..., object] = raw_cancel) -> None:
                    cb()

                cancel_cb = _bound_cancel

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_error = exc
                    if _is_non_retryable(exc):
                        if any(
                            token in str(exc).lower()
                            for token in (
                                "api key",
                                "authentication",
                                "invalid api key",
                            )
                        ) and not isinstance(exc, APIKeyError):
                            raise APIKeyError(str(exc)) from exc
                        raise
                    error_text = str(exc).lower()
                    if any(
                        token in error_text for token in ("rate limit", "quota", "429")
                    ):
                        if attempt >= max_retries:
                            raise APIRateLimitError(str(exc)) from exc
                    if attempt >= max_retries:
                        raise
                    delay = min(
                        base_delay * (2**attempt) + random.uniform(0, 1), max_delay
                    )
                    logger.warning("AI call failed, retrying in %.1fs: %s", delay, exc)
                    _interruptible_sleep(delay, cancel_cb)
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
