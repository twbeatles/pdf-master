import json
import logging
import time
from contextlib import AbstractContextManager
from typing import Any


def perf_log(stage: str, elapsed_ms: float, extra: dict[str, Any] | None = None, logger: logging.Logger | None = None):
    """Emit a standardized performance log line."""
    target_logger = logger or logging.getLogger(__name__)
    meta = "{}"
    if extra:
        try:
            meta = json.dumps(extra, ensure_ascii=False, sort_keys=True)
        except Exception:
            meta = str(extra)
    target_logger.info("PERF|stage=%s|ms=%.3f|meta=%s", stage, elapsed_ms, meta)


class PerfTimer(AbstractContextManager):
    """Simple context manager for timing code blocks."""

    def __init__(self, name: str, logger: logging.Logger | None = None, extra: dict[str, Any] | None = None):
        self.name = name
        self.logger = logger or logging.getLogger(__name__)
        self.extra = extra or {}
        self._start = 0.0

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed_ms = (time.perf_counter() - self._start) * 1000.0
        extra = dict(self.extra)
        if exc_type is not None:
            extra["error"] = getattr(exc_type, "__name__", str(exc_type))
        perf_log(self.name, elapsed_ms, extra=extra, logger=self.logger)
        return False
