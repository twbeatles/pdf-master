from __future__ import annotations

import csv
import io
import json
import logging
import os
from collections import Counter
from typing import Any, cast

from .._typing import WorkerHost
from ..constants import (
    DEFAULT_PAGE_SIZE,
    WATERMARK_DEFAULTS,
    WATERMARK_TILE_SPACING_X,
    WATERMARK_TILE_SPACING_Y,
)
from ..optional_deps import fitz
from ..worker_runtime.args import (
    _as_bool,
    _as_dict,
    _as_float,
    _as_int,
    _as_list,
    _as_str,
)
from ._pdf_helpers import (
    _extract_page_markdown,
    _fallback_markdown_from_text,
    _markdown_front_matter,
    _normalize_stroke_points,
    _page_asset_placeholders,
    _sample_diff_text,
)

logger = logging.getLogger(__name__)


class WorkerFormOpsMixin(WorkerHost):
    def get_form_fields(self):
        """PDF 양식 필드 목록 반환"""
        file_path = _as_str(self.kwargs.get('file_path'))

        doc = self._open_pdf_document(file_path)
        fields = []

        try:
            total_pages = max(1, len(doc))
            for page_num in range(len(doc)):
                self._check_cancelled()
                page = doc[page_num]
                widgets = page.widgets()
                if widgets:
                    for widget in widgets:
                        rect = widget.rect or fitz.Rect(0, 0, 0, 0)
                        fields.append({
                            'page': page_num + 1,
                            'name': widget.field_name or f"field_{len(fields)}",
                            'type': widget.field_type_string,
                            'value': widget.field_value or "",
                            'rect': [rect.x0, rect.y0, rect.x1, rect.y1],
                        })
                self._emit_progress_if_due(int((page_num + 1) / total_pages * 100))

            # 결과를 kwargs에 저장 (메인 스레드에서 접근)
            self.kwargs['result_fields'] = fields
            self._set_result_payload(fields=fields)
            self.finished_signal.emit(self._get_msg("msg_form_fields_done", len(fields)))
        finally:
            doc.close()

    def fill_form(self):
        """PDF 양식 필드에 값 채우기"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        field_values = _as_dict(self.kwargs.get('field_values'))

        doc = self._open_pdf_document(file_path)
        filled_count = 0

        try:
            total_pages = max(1, len(doc))
            for page_index, page in enumerate(doc):
                self._check_cancelled()
                widgets = page.widgets()
                if widgets:
                    for widget in widgets:
                        field_name = widget.field_name
                        if field_name and field_name in field_values:
                            widget.field_value = field_values[field_name]
                            widget.update()
                            filled_count += 1
                self._emit_progress_if_due(int((page_index + 1) / total_pages * 100))

            self._check_cancelled()
            self._atomic_pdf_save(doc, output_path)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(self._get_msg("msg_form_filled", filled_count))
        finally:
            doc.close()
