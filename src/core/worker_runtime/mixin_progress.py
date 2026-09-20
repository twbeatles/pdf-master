"""취소·진행률·페이지 인덱스 믹스인."""
from __future__ import annotations

import time
from typing import Any, cast

from .._typing import WorkerHost
from .preflight import parse_page_range


class WorkerRuntimeProgressMixin(WorkerHost):
    def _parse_page_range(self, page_range_str: str, total_pages: int) -> list[int]:
        return parse_page_range(self, page_range_str, total_pages)

    def _check_cancelled(self) -> None:
        if self._cancel_requested or self.isInterruptionRequested():
            from ..worker import CancelledError

            raise CancelledError("작업이 사용자에 의해 취소되었습니다.")

    def _emit_progress_if_due(
        self,
        value: int | float | str,
        min_step: int = 1,
        min_interval_ms: int = 50,
    ) -> None:
        try:
            value = int(value)
        except Exception:
            return
        value = max(0, min(100, value))

        now_ms = time.monotonic() * 1000.0
        last_value = self._last_progress_value

        should_emit = False
        if last_value is None:
            should_emit = True
        elif value == 100:
            should_emit = True
        elif abs(value - last_value) >= max(1, int(min_step)):
            should_emit = True
        elif (now_ms - self._last_progress_emit_ts_ms) >= max(0, int(min_interval_ms)):
            should_emit = True

        if should_emit:
            self.progress_signal.emit(value)
            self._last_progress_value = value
            self._last_progress_emit_ts_ms = now_ms

    def _resolve_page_index(
        self,
        raw_page_index: object,
        total_pages: int,
        allow_last_page_sentinel: bool = False,
    ) -> int | None:
        if total_pages <= 0:
            self.error_signal.emit(self._get_msg("err_pdf_has_no_pages"))
            return None

        try:
            page_index = int(cast(Any, raw_page_index))
        except (TypeError, ValueError):
            self.error_signal.emit(self._get_msg("err_page_number_numeric", str(raw_page_index)))
            return None

        if allow_last_page_sentinel and page_index == -1:
            return total_pages - 1

        if page_index < 0 or page_index >= total_pages:
            display_page = page_index + 1 if page_index >= 0 else page_index
            self.error_signal.emit(
                self._get_msg("err_page_out_of_range", str(display_page), str(total_pages))
            )
            return None

        return page_index


__all__ = ["WorkerRuntimeProgressMixin"]
