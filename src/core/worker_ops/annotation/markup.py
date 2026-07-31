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


class WorkerAnnotationMarkupMixin(WorkerHost):
    def highlight_text(self):
        """PDF 내 텍스트 하이라이트"""
        file_path = _as_str(self.kwargs.get('file_path'))
        search_term = _as_str(self.kwargs.get('search_term'))
        output_path = _as_str(self.kwargs.get('output_path'))
        color = self.kwargs.get('color', (1, 1, 0))  # 기본 노란색

        doc = self._open_pdf_document(file_path)
        highlight_count = 0
        try:
            total_pages = len(doc)
            for page_num in range(len(doc)):
                page = doc[page_num]
                self._check_cancelled()  # 취소 체크포인트
                text_instances = page.search_for(search_term)
                for inst in text_instances:
                    highlight = page.add_highlight_annot(inst)
                    highlight.set_colors(stroke=color)
                    highlight.update()
                    highlight_count += 1
                self._emit_progress_if_due(int((page_num + 1) / total_pages * 100))

            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(self._get_msg("msg_highlight_done", search_term, highlight_count))
        finally:
            doc.close()

    def add_text_markup(self):
        """검색어에 밑줄 또는 취소선 추가"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        search_term = _as_str(self.kwargs.get('search_term'))
        markup_type = _as_str(self.kwargs.get('markup_type'), 'underline')  # underline, strikeout, squiggly
        valid_markup_types = {'underline', 'strikeout', 'squiggly'}

        if markup_type not in valid_markup_types:
            self.error_signal.emit(self._get_msg("err_invalid_markup_type", str(markup_type)))
            return

        doc = self._open_pdf_document(file_path)
        count = 0
        try:
            total_pages = len(doc)
            for page_num in range(len(doc)):
                page = doc[page_num]
                self._check_cancelled()  # 취소 체크포인트
                instances = page.search_for(search_term)
                for inst in instances:
                    annot = None
                    if markup_type == 'underline':
                        annot = page.add_underline_annot(inst)
                    elif markup_type == 'strikeout':
                        annot = page.add_strikeout_annot(inst)
                    elif markup_type == 'squiggly':
                        annot = page.add_squiggly_annot(inst)
                    if annot:
                        annot.update()
                    count += 1
                self._emit_progress_if_due(int((page_num + 1) / total_pages * 100))

            self._atomic_pdf_save(doc, output_path)
            markup_name = self._get_msg(f"msg_markup_label_{markup_type}")
            if markup_name == f"msg_markup_label_{markup_type}":
                markup_name = markup_type
            self.finished_signal.emit(self._get_msg("msg_text_markup_added", markup_name, search_term, count))
        finally:
            doc.close()

    def insert_textbox(self):
        """PDF에 텍스트 상자/선택 위치 워터마크 삽입"""
        self._normalize_mode_kwargs()
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_num = _as_int(self.kwargs.get('page_num'), 0)

        # rect or (x, y[, w, h])
        rect_arg = self.kwargs.get('rect')
        if rect_arg:
            rect = cast(list[float], rect_arg)
        else:
            x = _as_float(self.kwargs.get('x'), 100.0)
            y = _as_float(self.kwargs.get('y'), 100.0)
            w = _as_float(self.kwargs.get('w'), _as_float(self.kwargs.get('width'), 200.0))
            h = _as_float(self.kwargs.get('h'), _as_float(self.kwargs.get('height'), 50.0))
            rect = [x, y, x + w, y + h]

        text = _as_str(self.kwargs.get('text'))
        fontsize = _as_int(self.kwargs.get('fontsize'), 12)
        color = tuple(self.kwargs.get('color', [0, 0, 0]))
        align = _as_int(self.kwargs.get('align'), 0)  # 0=left, 1=center, 2=right
        fontname = _as_str(self.kwargs.get('fontname'), 'helv')
        opacity = max(0.0, min(1.0, _as_float(self.kwargs.get('opacity'), 1.0)))
        # insert_textbox 는 90° 배수만 허용
        rotation = _as_int(self.kwargs.get('rotation'), 0) % 360
        rotation = (round(rotation / 90) * 90) % 360
        layer = _as_str(self.kwargs.get('layer'), 'foreground')

        if not text.strip():
            self.error_signal.emit(self._get_msg("msg_enter_text"))
            return

        doc = self._open_pdf_document(file_path)
        try:
            if page_num < 0 or page_num >= len(doc):
                self.error_signal.emit(
                    self._get_msg("err_page_out_of_range", str(page_num + 1), str(len(doc)))
                )
                return

            page = doc[page_num]
            fitz_rect = fitz.Rect(rect)
            resolved_fontname = self._resolve_textbox_fontname(page, fontname)
            overlay = layer != 'background'

            page.insert_textbox(
                fitz_rect,
                text,
                fontsize=fontsize,
                fontname=resolved_fontname,
                color=color,
                align=align,
                rotate=rotation,
                fill_opacity=opacity,
                stroke_opacity=opacity,
                overlay=overlay,
            )

            self._atomic_pdf_save(doc, output_path)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(self._get_msg("msg_textbox_inserted", page_num + 1))
        finally:
            doc.close()

    def _resolve_textbox_fontname(self, page: Any, fontname: str) -> str:
        """UI/별칭 폰트명을 PyMuPDF insert_textbox 가 받을 수 있는 이름으로 해석."""
        key = (fontname or "helv").strip().lower()
        # Base-14 / 흔한 별칭
        aliases = {
            "helv": "helv",
            "helvetica": "helv",
            "cour": "cour",
            "courier": "cour",
            "couri": "cour",
            "tiro": "tiro",
            "times": "tiro",
            "times-roman": "tiro",
            "timesroman": "tiro",
        }
        if key in aliases:
            return aliases[key]

        # CJK: fontname="cjk" 직접 전달 불가 → 임베드 후 등록명 사용
        if key in {"cjk", "cjk_safe", "ko", "korean", "china-s", "china-t", "japan", "korea"}:
            registered = "pdfmaster_cjk"
            try:
                page.insert_font(fontname=registered, fontbuffer=fitz.Font("cjk").buffer)
                return registered
            except Exception:
                logger.warning("CJK font embed failed; falling back to helv", exc_info=True)
                return "helv"

        # 알 수 없는 이름은 그대로 시도 (커스텀 등록 폰트 등)
        return fontname or "helv"

    def add_sticky_note(self):
        """PDF에 스티키 노트(텍스트 주석) 추가"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_num = _as_int(self.kwargs.get('page_num'), 0)
        x = _as_int(self.kwargs.get('x'), 100)  # 노트 위치 X
        y = _as_int(self.kwargs.get('y'), 100)  # 노트 위치 Y
        content = _as_str(self.kwargs.get('content'))  # 노트 내용
        title = _as_str(self.kwargs.get('title'), '메모')  # 노트 제목
        icon = _as_str(self.kwargs.get('icon'), 'Note')  # Note, Comment, Key, Help, Insert, Paragraph

        doc = self._open_pdf_document(file_path)
        try:
            resolved_page_num = self._resolve_page_index(page_num, len(doc))
            if resolved_page_num is None:
                return

            page = doc[resolved_page_num]
            point = fitz.Point(x, y)

            # 스티키 노트 주석 추가
            annot = page.add_text_annot(point, content, icon=icon)
            if annot:
                annot.set_info(title=title, content=content)
                annot.update()

            self._emit_progress_if_due(100)
            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(self._get_msg("msg_sticky_note_added", resolved_page_num + 1, icon))
        finally:
            doc.close()
