"""첨부 경로·원자 저장 믹스인 (io.py thin wrapper)."""
from __future__ import annotations

from typing import Any

from .._typing import WorkerHost
from .io import (
    atomic_binary_save,
    atomic_pixmap_save,
    atomic_pdf_save,
    atomic_text_save,
    build_safe_attachment_output_path,
    build_unique_output_stem,
    record_created_output_path,
    sanitize_attachment_filename,
)


class WorkerRuntimeFilesMixin(WorkerHost):
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

    def _atomic_pixmap_save(self, pixmap: Any, output_path: str) -> None:
        atomic_pixmap_save(self, pixmap, output_path)

    def _record_created_output_path(self, path: str) -> None:
        record_created_output_path(self, path)


__all__ = ["WorkerRuntimeFilesMixin"]
