from __future__ import annotations

from typing import Any

from .optional_deps import fitz


class SignalLike:
    def connect(self, slot: object) -> object:
        ...

    def emit(self, *args: object) -> object:
        ...


class WorkerHost:
    mode: str
    kwargs: dict[str, Any]
    _cancel_requested: bool
    _last_progress_value: int | None
    _last_progress_emit_ts_ms: float
    progress_signal: Any
    finished_signal: Any
    error_signal: Any
    cancelled_signal: Any

    def isInterruptionRequested(self) -> bool:
        ...

    def _atomic_pdf_save(self, doc: Any, output_path: str, **save_kwargs: Any) -> None:
        ...

    def _build_safe_attachment_output_path(
        self,
        output_dir: str,
        raw_name: str,
        index: int,
        used_names: set[str],
    ) -> tuple[str, str]:
        ...

    def _build_unique_output_stem(
        self,
        output_dir: str,
        preferred_stem: str,
        reserved_suffix: str,
        used_stems: set[str],
    ) -> str:
        ...

    def _check_cancelled(self) -> None:
        ...

    def _resolve_page_index(
        self,
        raw_page_index: object,
        total_pages: int,
        allow_last_page_sentinel: bool = False,
    ) -> int | None:
        ...

    def _emit_progress_if_due(
        self,
        value: int | float | str,
        min_step: int = 1,
        min_interval_ms: int = 50,
    ) -> None:
        ...

    def _get_msg(self, key: str, *args: object) -> str:
        ...

    def _record_created_output_path(self, path: str) -> None:
        ...

    def _is_pdf_encrypted(self, file_path: str) -> bool:
        ...

    def _normalize_mode_kwargs(self) -> None:
        ...

    def _parse_page_range(self, page_range_str: str, total_pages: int) -> list[int]:
        ...
