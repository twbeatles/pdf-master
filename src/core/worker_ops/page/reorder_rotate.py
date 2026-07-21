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


class WorkerPageReorderRotateMixin(WorkerHost):
    def rotate(self):
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        angle = _as_int(self.kwargs.get('angle'))
        raw_page_indices = self.kwargs.get('page_indices')

        doc = self._open_pdf_document(file_path)
        try:
            total_pages = len(doc)
            if total_pages <= 0:
                self.error_signal.emit(self._get_msg("err_pdf_has_no_pages"))
                return

            if raw_page_indices is None:
                page_indices = list(range(total_pages))
            else:
                if isinstance(raw_page_indices, (list, tuple, set)):
                    requested_indices = list(raw_page_indices)
                else:
                    requested_indices = [raw_page_indices]

                page_indices = []
                seen = set()
                for raw_page_index in requested_indices:
                    try:
                        page_index = int(raw_page_index)
                    except (TypeError, ValueError):
                        self.error_signal.emit(self._get_msg("err_page_number_numeric", str(raw_page_index)))
                        return
                    if page_index < 0 or page_index >= total_pages:
                        self.error_signal.emit(
                            self._get_msg("err_page_out_of_range", str(page_index + 1), str(total_pages))
                        )
                        return
                    if page_index not in seen:
                        seen.add(page_index)
                        page_indices.append(page_index)

            if not page_indices:
                self.error_signal.emit(self._get_msg("msg_select_rotate_pages"))
                return

            total_to_rotate = max(1, len(page_indices))
            for idx, page_index in enumerate(page_indices):
                page = doc[page_index]
                self._check_cancelled()  # 취소 체크포인트
                page.set_rotation(page.rotation + angle)
                self._emit_progress_if_due(int((idx + 1) / total_to_rotate * 100))
            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(self._get_msg("msg_pages_rotated", len(page_indices), angle))
        finally:
            doc.close()

    def reorder(self):
        """페이지 순서 변경"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_order = [_as_int(page_num) for page_num in _as_list(self.kwargs.get('page_order'))]

        doc_src = None
        doc_out = None
        try:
            doc_src = self._open_pdf_document(file_path)
            doc_out = fitz.open()

            for idx, page_num in enumerate(page_order):
                self._check_cancelled()  # 취소 체크포인트
                doc_out.insert_pdf(doc_src, from_page=page_num, to_page=page_num)
                self._emit_progress_if_due(int((idx + 1) / len(page_order) * 100))

            self._atomic_pdf_save(doc_out, output_path)
            self.finished_signal.emit(self._get_msg("msg_reorder_done", len(page_order)))
        finally:
            if doc_out:
                doc_out.close()
            if doc_src:
                doc_src.close()

    def reverse_pages(self):
        """페이지 역순 정렬"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))

        doc = self._open_pdf_document(file_path)
        try:
            page_count = len(doc)

            # 단일 페이지 PDF 처리
            if page_count <= 1:
                self._atomic_pdf_save(doc, output_path)
                self._emit_progress_if_due(100)
                self.finished_signal.emit(self._get_msg("msg_reverse_done_single"))
                return

            # 역순으로 페이지 이동
            for i in range(page_count - 1):
                self._check_cancelled()  # 취소 체크포인트
                doc.move_page(page_count - 1, i)
                self._emit_progress_if_due(int((i + 1) / (page_count - 1) * 100))

            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(self._get_msg("msg_reverse_done", page_count))
        finally:
            doc.close()
