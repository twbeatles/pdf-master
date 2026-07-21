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


class WorkerAnnotationRedactionMixin(WorkerHost):
    def redact_text(self):
        """PDF에서 텍스트 영구 삭제 (교정)"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        search_term = _as_str(self.kwargs.get('search_term'))
        fill_color = self.kwargs.get('fill_color', (0, 0, 0))  # 검정색 기본
        images = _as_int(self.kwargs.get("images"), 2)  # apply_redactions images flag

        if not search_term:
            self.error_signal.emit(self._get_msg("err_redact_text_required"))
            return

        doc = self._open_pdf_document(file_path)
        try:
            redact_count = 0
            total_pages = len(doc)

            for page_num in range(len(doc)):
                page = doc[page_num]
                self._check_cancelled()  # 취소 체크포인트
                text_instances = page.search_for(search_term)
                for inst in text_instances:
                    page.add_redact_annot(inst, fill=fill_color)
                    redact_count += 1
                try:
                    page.apply_redactions(images=images)
                except TypeError:
                    page.apply_redactions()
                self._emit_progress_if_due(int((page_num + 1) / total_pages * 100))

            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(self._get_msg("msg_redact_done", redact_count))
        finally:
            doc.close()

    def redact_area(self):
        """좌표 영역 기반 영구 교정.

        rects: [{page: 1-based, rect: [x0,y0,x1,y1]}, ...] 또는
               page + rect 단일 지정.
        """
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        fill_color = self.kwargs.get("fill_color", (0, 0, 0))
        images = _as_int(self.kwargs.get("images"), 2)
        raw_rects = _as_list(self.kwargs.get("rects"))

        # 단일 page/rect 단축 인자
        if not raw_rects:
            page_one = self.kwargs.get("page")
            rect = self.kwargs.get("rect")
            if page_one is not None and rect is not None:
                raw_rects = [{"page": page_one, "rect": rect}]

        if not raw_rects:
            self.error_signal.emit(self._get_msg("err_redact_area_required"))
            return

        doc = self._open_pdf_document(file_path)
        try:
            page_count = len(doc)
            by_page: dict[int, list[Any]] = {}
            for item in raw_rects:
                if isinstance(item, dict):
                    page_num = _as_int(item.get("page"), 0)
                    rect_vals = item.get("rect")
                elif isinstance(item, (list, tuple)) and len(item) >= 5:
                    page_num = int(item[0])
                    rect_vals = item[1:5]
                else:
                    continue
                if page_num < 1 or page_num > page_count:
                    continue
                try:
                    coords = [float(v) for v in rect_vals]  # type: ignore[arg-type]
                    if len(coords) < 4:
                        continue
                    rect = fitz.Rect(coords[0], coords[1], coords[2], coords[3])
                except Exception:
                    continue
                if rect.is_empty or rect.width < 1 or rect.height < 1:
                    continue
                by_page.setdefault(page_num - 1, []).append(rect)

            if not by_page:
                self.error_signal.emit(self._get_msg("err_redact_area_invalid"))
                return

            redact_count = 0
            pages = sorted(by_page.keys())
            for idx, page_index in enumerate(pages):
                self._check_cancelled()
                page = doc[page_index]
                for rect in by_page[page_index]:
                    page.add_redact_annot(rect, fill=fill_color)
                    redact_count += 1
                try:
                    page.apply_redactions(images=images)
                except TypeError:
                    page.apply_redactions()
                self._emit_progress_if_due(int((idx + 1) / max(1, len(pages)) * 100))

            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(self._get_msg("msg_redact_done", redact_count))
        finally:
            doc.close()
