from __future__ import annotations
import csv
import io
import json
import logging
import os
from collections import Counter
from typing import Any, cast
from ..._typing import WorkerHost
from ...constants import (
    DEFAULT_PAGE_SIZE,
    PAGE_SIZES,
    WATERMARK_DEFAULTS,
    WATERMARK_TILE_SPACING_X,
    WATERMARK_TILE_SPACING_Y,
)
from ...optional_deps import fitz
from ...worker_runtime.args import (
    _as_bool,
    _as_dict,
    _as_float,
    _as_int,
    _as_list,
    _as_str,
)
from .._pdf_helpers import (
    _extract_page_markdown,
    _fallback_markdown_from_text,
    _markdown_front_matter,
    _normalize_stroke_points,
    _page_asset_placeholders,
    _sample_diff_text,
)
logger = logging.getLogger(__name__)


class WorkerExtractBookmarksMixin(WorkerHost):
    def get_bookmarks(self):
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        toc: list[list[Any]] = []
        doc = None
        try:
            doc = self._open_pdf_document(file_path)
            toc = cast(list[list[Any]], doc.get_toc() or [])
        finally:
            if doc:
                doc.close()

        lines = [f"# {self._get_msg('extract_bookmarks_title', os.path.basename(file_path))}", ""]
        if toc:
            for item in toc:
                level, title, page = item[0], item[1], item[2]
                indent = "  " * (max(0, int(level) - 1))
                lines.append(
                    f"{indent}- [{title}] -> {self._get_msg('extract_bookmarks_page', page)}"
                )
        else:
            lines.append(self._get_msg("extract_bookmarks_empty"))
        lines.append("")
        self._atomic_text_save(output_path, "\n".join(lines))
        self._emit_progress_if_due(100)
        self.finished_signal.emit(self._get_msg("msg_bookmarks_extracted", len(toc)))

    def set_bookmarks(self):
        """PDF 북마크(목차) 설정"""
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        raw_bookmarks = self.kwargs.get("bookmarks") or []
        if not isinstance(raw_bookmarks, list):
            self.error_signal.emit(self._get_msg("err_bookmarks_invalid"))
            return

        normalized: list[list[Any]] = []
        for item in raw_bookmarks:
            if not isinstance(item, (list, tuple)) or len(item) < 3:
                self.error_signal.emit(self._get_msg("err_bookmarks_invalid"))
                return
            try:
                level = int(item[0])
                title = str(item[1]).strip()
                page = int(item[2])
            except (TypeError, ValueError):
                self.error_signal.emit(self._get_msg("err_bookmarks_invalid"))
                return
            if level < 1 or page < 1 or not title:
                self.error_signal.emit(self._get_msg("err_bookmarks_invalid"))
                return
            normalized.append([level, title, page])

        doc = None
        try:
            doc = self._open_pdf_document(file_path)
            page_count = len(doc)
            for _level, _title, page in normalized:
                if page > page_count:
                    self.error_signal.emit(
                        self._get_msg("err_page_out_of_range", str(page), str(page_count))
                    )
                    return
            doc.set_toc(normalized)
            self._atomic_pdf_save(doc, output_path)
        finally:
            if doc:
                doc.close()

        self._emit_progress_if_due(100)
        self.finished_signal.emit(self._get_msg("msg_bookmarks_set", len(normalized)))
