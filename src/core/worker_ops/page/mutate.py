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


class WorkerPageMutateMixin(WorkerHost):
    def add_page_numbers(self):
        """페이지 번호 삽입"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        position = _as_str(self.kwargs.get('position'), 'bottom')  # bottom, top, bottom-left, bottom-right, top-left, top-right
        format_str = _as_str(self.kwargs.get('format'), '{n} / {total}')
        fontsize = _as_int(self.kwargs.get('fontsize'), 10)
        fontname = _as_str(self.kwargs.get('fontname'), 'helv')
        color = self.kwargs.get('color', (0, 0, 0))
        margin = _as_int(self.kwargs.get('margin'), 30)
        start_number = _as_int(self.kwargs.get('start_number'), 1)  # 시작 번호
        skip_first = _as_bool(self.kwargs.get('skip_first'), False)  # 첫 페이지 건너뛰기
        use_roman = _as_bool(self.kwargs.get('use_roman'), False)  # v3.2: 로마 숫자 형식

        def to_roman(num):
            """숫자를 로마 숫자로 변환"""
            val = [(1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'),
                   (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'),
                   (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]
            roman = ''
            for v, r in val:
                while num >= v:
                    roman += r
                    num -= v
            return roman

        doc = self._open_pdf_document(file_path)
        try:
            total = len(doc)

            for i in range(total):
                page = doc[i]
                self._check_cancelled()  # 취소 체크포인트
                if skip_first and i == 0:
                    continue

                page_num = start_number + i if not skip_first else start_number + i - 1

                # v3.2: 로마 숫자 변환
                if use_roman:
                    num_str = to_roman(page_num)
                    total_str = to_roman(total)
                else:
                    num_str = str(page_num)
                    total_str = str(total)

                text = format_str.replace('{n}', num_str).replace('{total}', total_str)
                rect = page.rect

                # 위치별 텍스트박스 영역 설정
                if position == 'bottom' or position == 'bottom-center':
                    r = fitz.Rect(0, rect.height - margin - 20, rect.width, rect.height - margin)
                    align = 1  # center
                elif position == 'top' or position == 'top-center':
                    r = fitz.Rect(0, margin, rect.width, margin + 20)
                    align = 1
                elif position == 'bottom-left':
                    r = fitz.Rect(margin, rect.height - margin - 20, 150, rect.height - margin)
                    align = 0  # left
                elif position == 'bottom-right':
                    r = fitz.Rect(rect.width - 150, rect.height - margin - 20, rect.width - margin, rect.height - margin)
                    align = 2  # right
                elif position == 'top-left':
                    r = fitz.Rect(margin, margin, 150, margin + 20)
                    align = 0
                elif position == 'top-right':
                    r = fitz.Rect(rect.width - 150, margin, rect.width - margin, margin + 20)
                    align = 2
                else:
                    r = fitz.Rect(0, rect.height - margin - 20, rect.width, rect.height - margin)
                    align = 1

                page.insert_textbox(r, text, fontsize=fontsize, fontname=fontname, color=color, align=align)
                self._emit_progress_if_due(int((i + 1) / total * 100))

            self._atomic_pdf_save(doc, output_path)
            format_type = self._get_msg(
                "msg_page_number_format_roman" if use_roman else "msg_page_number_format_arabic"
            )
            self.finished_signal.emit(self._get_msg("msg_page_numbers_done", format_type, total))
        finally:
            doc.close()

    def insert_blank_page(self):
        """빈 페이지 삽입"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        position = _as_int(self.kwargs.get('position'), 0)

        doc = self._open_pdf_document(file_path)
        try:
            if position < 0 or position > len(doc):
                self.error_signal.emit(
                    self._get_msg("err_page_out_of_range", str(position + 1), str(len(doc) + 1))
                )
                return
            width, height = DEFAULT_PAGE_SIZE  # A4
            doc.insert_page(position, width=width, height=height)
            self._atomic_pdf_save(doc, output_path)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(self._get_msg("msg_blank_page_inserted", position + 1))
        finally:
            doc.close()

    def replace_page(self):
        """특정 페이지 교체"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        replace_path = _as_str(self.kwargs.get('replace_path'))
        target_page = _as_int(self.kwargs.get('target_page'), 1) - 1
        source_page = _as_int(self.kwargs.get('source_page'), 1) - 1

        doc = self._open_pdf_document(file_path)
        replace_doc = self._open_pdf_document(replace_path)
        try:
            # 입력 검증
            if target_page < 0 or target_page >= len(doc):
                self.error_signal.emit(self._get_msg("err_target_page_invalid", target_page + 1))
                return
            if source_page < 0 or source_page >= len(replace_doc):
                self.error_signal.emit(self._get_msg("err_source_page_invalid", source_page + 1))
                return

            doc.delete_page(target_page)
            doc.insert_pdf(replace_doc, from_page=source_page, to_page=source_page, start_at=target_page)

            self._atomic_pdf_save(doc, output_path)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(self._get_msg("msg_page_replaced"))
        finally:
            replace_doc.close()
            doc.close()

    def duplicate_page(self):
        """페이지 복제"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_num = _as_int(self.kwargs.get('page_num'), 0)  # 0-indexed
        count = _as_int(self.kwargs.get('count'), 1)

        doc = self._open_pdf_document(file_path)
        try:
            resolved_page_num = self._resolve_page_index(page_num, len(doc))
            if resolved_page_num is None:
                return
            for i in range(count):
                self._check_cancelled()  # 취소 체크포인트
                doc.fullcopy_page(resolved_page_num, resolved_page_num + 1 + i)
                self._emit_progress_if_due(int((i + 1) / count * 100))

            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(self._get_msg("msg_page_duplicated", resolved_page_num + 1, count))
        finally:
            doc.close()
