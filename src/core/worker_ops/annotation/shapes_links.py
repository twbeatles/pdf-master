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


class WorkerAnnotationShapesLinksMixin(WorkerHost):
    def draw_shapes(self):
        """PDF에 도형 그리기"""
        self._normalize_mode_kwargs()
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_num = _as_int(self.kwargs.get('page_num'), 0)
        shapes = cast(list[dict[str, Any]], self.kwargs.get('shapes') or [])  # [{type, params, color, width}]

        doc = self._open_pdf_document(file_path)
        try:
            if not shapes:
                self.error_signal.emit(self._get_msg("err_shapes_required"))
                return
            # v4.5: 페이지 번호 유효성 검사
            if page_num < 0 or page_num >= len(doc):
                self.error_signal.emit(self._get_msg("err_page_out_of_range", str(page_num + 1), str(len(doc))))
                return

            page = doc[page_num]

            for shape_info in shapes:
                shape_type = shape_info.get('type', 'line')
                color = tuple(shape_info.get('color', [1, 0, 0]))
                # v4.5: 색상 값 범위 제한
                color = tuple(max(0.0, min(1.0, c)) for c in color)
                width = shape_info.get('width', 1)
                fill = shape_info.get('fill')
                if fill:
                    fill = tuple(max(0.0, min(1.0, c)) for c in fill)

                if shape_type == 'line':
                    p1 = fitz.Point(shape_info['p1'][0], shape_info['p1'][1])
                    p2 = fitz.Point(shape_info['p2'][0], shape_info['p2'][1])
                    page.draw_line(p1, p2, color=color, width=width)
                elif shape_type == 'rect':
                    rect = fitz.Rect(shape_info['rect'])
                    page.draw_rect(rect, color=color, width=width, fill=fill)
                elif shape_type == 'circle':
                    center = fitz.Point(shape_info['center'][0], shape_info['center'][1])
                    radius = shape_info.get('radius', 50)
                    page.draw_circle(center, radius, color=color, width=width, fill=fill)
                elif shape_type == 'oval':
                    rect = fitz.Rect(shape_info['rect'])
                    page.draw_oval(rect, color=color, width=width, fill=fill)

            self._atomic_pdf_save(doc, output_path)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(self._get_msg("msg_shapes_added", len(shapes)))
        finally:
            doc.close()

    def add_link(self):
        """PDF에 하이퍼링크 추가"""
        self._normalize_mode_kwargs()
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_num = _as_int(self.kwargs.get('page_num'), 0)
        link_type = _as_str(self.kwargs.get('link_type'), 'uri')  # uri, goto
        rect = cast(list[float], self.kwargs.get('rect') or [100, 100, 200, 120])  # [x0, y0, x1, y1]
        target = self.kwargs.get('target')  # URL 또는 페이지 번호

        # v4.5: link_type 유효성 검사
        valid_link_types = ['uri', 'goto']
        if link_type not in valid_link_types:
            logger.warning(f"Invalid link_type '{link_type}', defaulting to 'uri'")
            link_type = 'uri'

        # v4.5: target 유효성 검사
        if target is None or (isinstance(target, str) and not target.strip()):
            self.error_signal.emit(self._get_msg("err_link_target_required"))
            return

        doc = self._open_pdf_document(file_path)
        try:
            if page_num < 0 or page_num >= len(doc):
                self.error_signal.emit(self._get_msg("err_page_out_of_range", str(page_num + 1), str(len(doc))))
                return

            page = doc[page_num]

            link = {
                'kind': fitz.LINK_URI if link_type == 'uri' else fitz.LINK_GOTO,
                'from': fitz.Rect(rect),
            }

            if link_type == 'uri':
                target_str = str(target).strip()
                # v4.5: URL 형식 기본 검증
                if not (
                    target_str.startswith('http://') or
                    target_str.startswith('https://') or
                    target_str.startswith('mailto:')
                ):
                    logger.warning(f"URL might be invalid: {target_str}")
                link['uri'] = target_str
            else:
                try:
                    raw_target = int(target)
                    # v4.5.3: goto 대상은 0-based 인덱스만 허용 (UI에서 사전 정규화)
                    target_page = raw_target
                    if target_page < 0 or target_page >= len(doc):
                        self.error_signal.emit(
                            self._get_msg("err_link_target_zero_based", str(target), str(max(0, len(doc) - 1)))
                        )
                        return
                    link['page'] = target_page
                    link['to'] = fitz.Point(0, 0)
                except ValueError:
                    self.error_signal.emit(self._get_msg("err_page_number_numeric", str(target)))
                    return

            page.insert_link(link)
            self._atomic_pdf_save(doc, output_path)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(self._get_msg("msg_link_added", page_num + 1))
        finally:
            doc.close()
