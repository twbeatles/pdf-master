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


class WorkerAnnotationSignaturesMixin(WorkerHost):
    def add_stamp(self):
        """PDF 스탬프 추가"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        stamp_text = _as_str(self.kwargs.get('stamp_text'), '기밀')
        position = _as_str(self.kwargs.get('position'), 'top-right')
        color = self.kwargs.get('color', (1, 0, 0))  # 빨강

        doc = self._open_pdf_document(file_path)
        try:
            total_pages = len(doc)
            for i in range(total_pages):
                page = doc[i]
                self._check_cancelled()  # 취소 체크포인트
                rect = page.rect
                if position == 'top-right':
                    point = fitz.Point(rect.width - 100, 40)
                elif position == 'top-left':
                    point = fitz.Point(30, 40)
                elif position == 'bottom-right':
                    point = fitz.Point(rect.width - 100, rect.height - 30)
                else:
                    point = fitz.Point(30, rect.height - 30)

                # 스탬프 테두리 (좌표 기반 간단 구현)
                stamp_rect = fitz.Rect(point.x - 10, point.y - 20, point.x + 80, point.y + 5)
                page.draw_rect(stamp_rect, color=color, width=2)
                page.insert_text(point, stamp_text, fontsize=14, fontname="helv", color=color)
                self._emit_progress_if_due(int((i + 1) / total_pages * 100))

            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(self._get_msg("msg_stamp_done"))
        finally:
            doc.close()

    def insert_signature(self):
        """전자 서명 이미지 삽입"""
        from datetime import datetime
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        signature_path = _as_str(self.kwargs.get('signature_path'))
        page_num = self.kwargs.get('page_num', -1)  # -1 = 마지막 페이지
        position = _as_str(self.kwargs.get('position'), 'bottom_right')
        signer_name = _as_str(self.kwargs.get('signer_name'))  # v3.2: 서명자 이름
        add_timestamp = _as_bool(self.kwargs.get('add_timestamp'), False)  # v3.2: 타임스탬프

        doc = self._open_pdf_document(file_path)
        try:
            total_pages = len(doc)
            resolved_page_num = self._resolve_page_index(
                page_num,
                total_pages,
                allow_last_page_sentinel=True,
            )
            if resolved_page_num is None:
                return

            page = doc[resolved_page_num]
            page_rect = page.rect

            # 서명 이미지 크기 (가로 150pt)
            sig_width = 150
            sig_height = 50

            # v3.2: 타임스탬프/서명자 텍스트 높이 추가
            text_height = 0
            if signer_name or add_timestamp:
                text_height = 30

            # 위치 계산
            positions = {
                'bottom_right': fitz.Rect(page_rect.width - sig_width - 50, page_rect.height - sig_height - 50 - text_height,
                                          page_rect.width - 50, page_rect.height - 50 - text_height),
                'bottom_left': fitz.Rect(50, page_rect.height - sig_height - 50 - text_height,
                                         50 + sig_width, page_rect.height - 50 - text_height),
                'top_right': fitz.Rect(page_rect.width - sig_width - 50, 50,
                                       page_rect.width - 50, 50 + sig_height),
                'top_left': fitz.Rect(50, 50, 50 + sig_width, 50 + sig_height),
            }

            rect = positions.get(position, positions['bottom_right'])

            # 서명 이미지 삽입
            page.insert_image(rect, filename=signature_path)

            # v3.2: 서명자 이름 및 타임스탬프 추가
            if signer_name or add_timestamp:
                text_parts = []
                if signer_name:
                    text_parts.append(f"서명자: {signer_name}")
                if add_timestamp:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M")
                    text_parts.append(f"일시: {now}")

                text_str = " | ".join(text_parts)
                text_rect = fitz.Rect(rect.x0, rect.y1 + 5, rect.x1, rect.y1 + 25)
                page.insert_textbox(text_rect, text_str, fontsize=8, fontname="helv",
                                   color=(0.3, 0.3, 0.3), align=1)

            # v3.2: 메타데이터에 서명 정보 기록
            if signer_name:
                meta = cast(dict[str, Any], doc.metadata or {})
                existing_keywords = meta.get('keywords', '') or ''
                new_keywords = f"{existing_keywords}; Signed by: {signer_name}" if existing_keywords else f"Signed by: {signer_name}"
                meta['keywords'] = new_keywords
                doc.set_metadata(meta)

            self._emit_progress_if_due(100)

            self._atomic_pdf_save(doc, output_path)
            extra_info = ""
            if signer_name:
                extra_info += self._get_msg("msg_signature_signer_suffix", signer_name)
            if add_timestamp:
                extra_info += self._get_msg("msg_signature_timestamp_suffix")
            self.finished_signal.emit(
                self._get_msg("msg_signature_inserted", extra_info, resolved_page_num + 1)
            )
        finally:
            doc.close()

    def add_ink_annotation(self):
        """PDF에 프리핸드 드로잉(잉크 주석) 추가"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_num = _as_int(self.kwargs.get('page_num'), 0)
        points = cast(list[list[float]], self.kwargs.get('points') or [])  # [[x1,y1], [x2,y2], ...] 좌표 목록
        color = self.kwargs.get('color', (0, 0, 1))  # 기본 파란색
        width = _as_int(self.kwargs.get('width'), 2)  # 선 두께

        doc = self._open_pdf_document(file_path)
        try:
            resolved_page_num = self._resolve_page_index(page_num, len(doc))
            if resolved_page_num is None:
                return

            page = doc[resolved_page_num]

            if not points:
                self.error_signal.emit(self._get_msg("err_ink_points_required"))
                return

            try:
                normalized_points = _normalize_stroke_points(points)
            except (TypeError, ValueError):
                self.error_signal.emit(self._get_msg("msg_invalid_stroke_format"))
                return

            try:
                annot = page.add_ink_annot([normalized_points])
            except (TypeError, ValueError):
                self.error_signal.emit(self._get_msg("msg_invalid_stroke_format"))
                return

            if annot:
                annot.set_colors(stroke=color)
                annot.set_border(width=width)
                annot.update()

            self._emit_progress_if_due(100)
            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(
                self._get_msg("msg_ink_annotation_added", resolved_page_num + 1, len(normalized_points))
            )
        finally:
            doc.close()

    def add_freehand_signature(self):
        """PDF에 프리핸드 서명 (여러 획) 추가"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_num = self.kwargs.get('page_num', -1)  # -1 = 마지막 페이지
        strokes = cast(list[list[list[float]]], self.kwargs.get('strokes') or [])  # [[[x1,y1], [x2,y2]], [[x3,y3], [x4,y4]]] 다중 획
        color = self.kwargs.get('color', (0, 0, 0))  # 기본 검정
        width = _as_int(self.kwargs.get('width'), 2)

        doc = self._open_pdf_document(file_path)
        try:
            total_pages = len(doc)
            resolved_page_num = self._resolve_page_index(
                page_num,
                total_pages,
                allow_last_page_sentinel=True,
            )
            if resolved_page_num is None:
                return

            page = doc[resolved_page_num]

            if not strokes:
                self.error_signal.emit(self._get_msg("msg_stroke_required"))
                return

            all_strokes: list[list[list[float]]] = []
            for stroke in strokes:
                self._check_cancelled()
                try:
                    all_strokes.append(_normalize_stroke_points(stroke))
                except (TypeError, ValueError):
                    self.error_signal.emit(self._get_msg("msg_invalid_stroke_format"))
                    return

            if not all_strokes:
                self.error_signal.emit(self._get_msg("err_no_valid_strokes"))
                return

            try:
                self._check_cancelled()
                annot = page.add_ink_annot(all_strokes)
            except (TypeError, ValueError):
                self.error_signal.emit(self._get_msg("msg_invalid_stroke_format"))
                return
            if annot:
                annot.set_colors(stroke=color)
                annot.set_border(width=width)
                annot.update()

            self._check_cancelled()
            self._emit_progress_if_due(100)
            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(
                self._get_msg("msg_freehand_signature_added", resolved_page_num + 1, len(all_strokes))
            )
        finally:
            doc.close()
