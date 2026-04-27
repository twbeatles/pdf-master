from __future__ import annotations

import logging
import os
import time
from typing import Any, cast

from .._typing import WorkerHost
from ..optional_deps import fitz
from .dispatch import get_handler_method_name, get_operation_spec
from .io import (
    atomic_binary_save,
    atomic_text_save,
    atomic_pdf_save,
    build_safe_attachment_output_path,
    build_unique_output_stem,
    record_created_output_path,
    sanitize_attachment_filename,
)
from .messages import get_message
from .normalize import normalize_mode_kwargs
from .preflight import is_pdf_encrypted, parse_page_range, preflight_inputs, validate_file_size, validate_non_pdf_size
from ..path_utils import normalize_path_key

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


class WorkerRuntimeMixin(WorkerHost):
    def _set_result_payload(self, payload: dict[str, Any] | None = None, **extra: Any) -> None:
        merged: dict[str, Any] = {}
        if isinstance(payload, dict):
            merged.update(payload)
        if extra:
            merged.update(extra)
        self.result_payload = merged

    def _update_result_payload(self, **payload: Any) -> None:
        if not isinstance(getattr(self, "result_payload", None), dict):
            self.result_payload = {}
        self.result_payload.update(payload)

    def _emit_partial_result(self, **payload: Any) -> None:
        if not payload:
            return
        payload.setdefault("mode", self.mode)
        spec = get_operation_spec(self.mode)
        if spec is not None:
            payload.setdefault("result_kind", spec.result_kind)
        self.partial_result_signal.emit(payload)

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

    def _sanitize_attachment_filename(self, raw_name: str, fallback: str) -> str:
        return sanitize_attachment_filename(raw_name, fallback)

    def _build_safe_attachment_output_path(
        self,
        output_dir: str,
        raw_name: str,
        index: int,
        used_names: set[str],
    ) -> tuple[str, str]:
        return build_safe_attachment_output_path(self, output_dir, raw_name, index, used_names)

    def _build_unique_output_stem(
        self,
        output_dir: str,
        preferred_stem: str,
        reserved_suffix: str,
        used_stems: set[str],
    ) -> str:
        return build_unique_output_stem(output_dir, preferred_stem, reserved_suffix, used_stems)

    def _atomic_pdf_save(self, doc: Any, output_path: str, **save_kwargs: Any) -> None:
        atomic_pdf_save(self, doc, output_path, **save_kwargs)

    def _atomic_text_save(
        self,
        output_path: str,
        text: str,
        *,
        encoding: str = "utf-8",
        newline: str | None = None,
    ) -> None:
        atomic_text_save(self, output_path, text, encoding=encoding, newline=newline)

    def _atomic_binary_save(self, output_path: str, data: bytes) -> None:
        atomic_binary_save(self, output_path, data)

    def _password_for_pdf_path(self, file_path: str) -> str:
        passwords = self.kwargs.get("passwords")
        if not isinstance(passwords, dict):
            return ""
        path_key = normalize_path_key(file_path)
        for key in (path_key, file_path):
            value = passwords.get(key)
            if isinstance(value, str) and value:
                return value
        return ""

    def _open_pdf_document(self, file_path: str, password: str | None = None):
        doc = fitz.open(file_path)
        if not getattr(doc, "is_encrypted", False):
            return doc

        candidates: list[str] = []
        if isinstance(password, str) and password:
            candidates.append(password)
        mapped_password = self._password_for_pdf_path(file_path)
        if mapped_password and mapped_password not in candidates:
            candidates.append(mapped_password)

        for candidate in candidates:
            try:
                if doc.authenticate(candidate):
                    return doc
            except Exception:
                logger.debug("PDF authentication attempt failed", exc_info=True)

        doc.close()
        raise ValueError(self._get_msg("err_wrong_password"))

    def _get_msg(self, key: str, *args: object) -> str:
        return get_message(key, *args)

    def _record_created_output_path(self, path: str) -> None:
        record_created_output_path(self, path)

    def _init_ai_service(self, require_api_key: bool = True):
        """v4.5: AI 서비스 초기화 헬퍼 - 코드 중복 제거."""
        try:
            from ..ai_service import AIService
        except ImportError:
            return None, self._get_msg("err_ai_module_not_found")

        file_path = self.kwargs.get("file_path")
        if not file_path or not os.path.exists(file_path):
            return None, self._get_msg("err_pdf_not_found")

        api_key = self.kwargs.get("api_key", "")
        if require_api_key and not api_key:
            return None, self._get_msg("err_api_key_required")

        ai_service = AIService(api_key=api_key)
        if not ai_service.is_available:
            return None, self._get_msg("err_ai_unavailable")

        return ai_service, None

    def _validate_file_size(self, file_path: str, emit_error: bool = True) -> bool:
        return validate_file_size(self, file_path, emit_error=emit_error)

    def _validate_non_pdf_size(self, file_path: str, emit_error: bool = True) -> bool:
        return validate_non_pdf_size(self, file_path, emit_error=emit_error)

    def _normalize_mode_kwargs(self) -> None:
        normalize_mode_kwargs(self.mode, self.kwargs, self._parse_page_range)

    def _preflight_inputs(self) -> bool:
        return preflight_inputs(self)

    def _is_pdf_encrypted(self, file_path: str) -> bool:
        return is_pdf_encrypted(file_path)

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
                error_msg = f"Unknown task: {self.mode}"
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
