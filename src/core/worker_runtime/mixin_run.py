"""작업 생명주기 (dispatch → preflight → handler → 에러 매핑)."""
from __future__ import annotations

import logging
from typing import Any, cast

from .._typing import WorkerHost
from ..optional_deps import fitz
from .dispatch import get_handler_method_name, get_operation_spec

logger = logging.getLogger(__name__)


class _PerfTimerFallback:
    def __init__(self, *_args: object, **_kwargs: object):
        pass

    def __enter__(self):
        return self

    def __exit__(self, _exc_type: object, _exc_val: object, _exc_tb: object):
        return False


try:
    from ..perf import PerfTimer
except ImportError:
    PerfTimer = cast(Any, _PerfTimerFallback)


class WorkerRuntimeRunMixin(WorkerHost):
    def run(self) -> None:
        logger.info("Starting task: %s", self.mode)
        try:
            self._normalize_mode_kwargs()
            spec = get_operation_spec(self.mode)
            handler_name = spec.handler if spec is not None else get_handler_method_name(self.mode)
            method = getattr(self, handler_name, None) if handler_name else None
            if method:
                if not self._preflight_inputs():
                    logger.info("Preflight validation failed: %s", self.mode)
                    return
                self.result_payload = {}
                self._last_progress_value = None
                self._last_progress_emit_ts_ms = 0.0
                with PerfTimer(f"core.worker.{self.mode}", logger=logger, extra={"mode": self.mode}):
                    method()
                if not self._cancel_requested:
                    logger.info("Task completed: %s", self.mode)
            else:
                error_msg = self._get_msg("err_unknown_task", self.mode)
                logger.error(error_msg)
                self.error_signal.emit(error_msg)
        except Exception as exc:
            from ..worker import CancelledError

            if isinstance(exc, CancelledError):
                logger.info("Task cancelled: %s", self.mode)
                self.cancelled_signal.emit(self._get_msg("err_cancelled"))
            elif isinstance(exc, FileNotFoundError):
                error_msg = self._get_msg("err_pdf_not_found")
                logger.error("FileNotFoundError in %s: %s", self.mode, exc)
                self.error_signal.emit(error_msg)
            elif isinstance(exc, PermissionError):
                error_msg = self._get_msg("err_file_access_denied", exc.filename or "")
                logger.error("PermissionError in %s: %s", self.mode, exc)
                self.error_signal.emit(error_msg)
            elif isinstance(exc, fitz.FileDataError):
                error_msg = self._get_msg("err_pdf_corrupted")
                logger.error("PDF FileDataError in %s: %s", self.mode, exc)
                self.error_signal.emit(error_msg)
            else:
                logger.error("Unexpected error in %s: %s", self.mode, exc, exc_info=True)
                self.error_signal.emit(self._get_msg("err_operation_failed", str(exc)))


__all__ = ["WorkerRuntimeRunMixin"]
