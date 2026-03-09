from __future__ import annotations

from typing import Any

import fitz


class SignalLike:
    def connect(self, slot: object) -> object:
        ...

    def emit(self, *args: object) -> object:
        ...


class WorkerHost:
    mode: str
    kwargs: dict[str, Any]
    progress_signal: Any
    finished_signal: Any
    error_signal: Any
    cancelled_signal: Any

    def _atomic_pdf_save(self, doc: fitz.Document, output_path: str, **save_kwargs: Any) -> None:
        ...

    def _check_cancelled(self) -> None:
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

    def _is_pdf_encrypted(self, file_path: str) -> bool:
        ...

    def _normalize_mode_kwargs(self) -> None:
        ...

    def _parse_page_range(self, page_range_str: str, total_pages: int) -> list[int]:
        ...
