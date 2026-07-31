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
            rect = [float(v) for v in cast(list[Any], rect_arg)]
        else:
            x = _as_float(self.kwargs.get('x'), 100.0)
            y = _as_float(self.kwargs.get('y'), 100.0)
            w = _as_float(self.kwargs.get('w'), _as_float(self.kwargs.get('width'), 200.0))
            h = _as_float(self.kwargs.get('h'), _as_float(self.kwargs.get('height'), 50.0))
            rect = [x, y, x + w, y + h]

        text = _as_str(self.kwargs.get('text'))
        fontsize = max(1, _as_int(self.kwargs.get('fontsize'), 12))
        raw_color = self.kwargs.get('color', [0, 0, 0])
        try:
            color = tuple(float(c) for c in cast(list[Any] | tuple[Any, ...], raw_color)[:3])
            if len(color) < 3:
                color = (0.0, 0.0, 0.0)
        except Exception:
            color = (0.0, 0.0, 0.0)
        align = _as_int(self.kwargs.get('align'), 0)  # 0=left, 1=center, 2=right
        fontname = _as_str(self.kwargs.get('fontname'), 'helv')
        opacity = max(0.0, min(1.0, _as_float(self.kwargs.get('opacity'), 1.0)))
        # insert_textbox 는 90° 배수만 허용
        rotation = _as_int(self.kwargs.get('rotation'), 0) % 360
        rotation = int(round(rotation / 90.0) * 90) % 360
        layer = _as_str(self.kwargs.get('layer'), 'foreground')

        if not text.strip():
            self.error_signal.emit(self._get_msg("msg_enter_text"))
            return

        # 너무 낮은 높이 → insert_textbox 가 조용히 실패(음수 반환)하므로 최소 높이 보장
        rect = self._ensure_textbox_rect(rect, text, fontsize)

        doc = self._open_pdf_document(file_path)
        try:
            if page_num < 0 or page_num >= len(doc):
                self.error_signal.emit(
                    self._get_msg("err_page_out_of_range", str(page_num + 1), str(len(doc)))
                )
                return

            page = doc[page_num]
            fitz_rect = fitz.Rect(rect)
            # 페이지 밖으로 완전히 벗어나면 클램프
            page_rect = page.rect
            fitz_rect = fitz_rect & page_rect
            if fitz_rect.is_empty or fitz_rect.width < 2 or fitz_rect.height < 2:
                # 페이지 밖이면 기본 위치로 폴백
                fitz_rect = fitz.Rect(
                    50,
                    50,
                    min(page_rect.width - 50, 50 + max(120.0, fontsize * 8)),
                    min(page_rect.height - 50, 50 + max(float(fontsize) * 2.0, 28.0)),
                )

            resolved_fontname = self._resolve_textbox_fontname(page, fontname)
            overlay = layer != 'background'
            wrote = self._write_textbox_content(
                page,
                fitz_rect,
                text,
                fontsize=fontsize,
                fontname=resolved_fontname,
                color=color,
                align=align,
                rotation=rotation,
                opacity=opacity,
                overlay=overlay,
            )
            if not wrote:
                self.error_signal.emit(self._get_msg("err_textbox_insert_failed"))
                return

            self._atomic_pdf_save(doc, output_path)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(self._get_msg("msg_textbox_inserted", page_num + 1))
        finally:
            doc.close()

    def _ensure_textbox_rect(
        self, rect: list[float], text: str, fontsize: int
    ) -> list[float]:
        """폰트 크기·줄 수에 맞게 최소 높이를 확보한다."""
        x0, y0, x1, y1 = (float(rect[0]), float(rect[1]), float(rect[2]), float(rect[3]))
        if x1 < x0:
            x0, x1 = x1, x0
        if y1 < y0:
            y0, y1 = y1, y0
        lines = max(1, text.count("\n") + 1)
        # insert_textbox 는 박스 높이가 부족하면 글자를 쓰지 않고 음수를 반환한다
        min_h = max(float(fontsize) * 1.4 * lines + 4.0, float(fontsize) + 8.0)
        min_w = max(40.0, float(fontsize) * 2.0)
        if (y1 - y0) < min_h:
            y1 = y0 + min_h
        if (x1 - x0) < min_w:
            x1 = x0 + min_w
        return [x0, y0, x1, y1]

    def _write_textbox_content(
        self,
        page: Any,
        fitz_rect: Any,
        text: str,
        *,
        fontsize: int,
        fontname: str,
        color: tuple[float, ...],
        align: int,
        rotation: int,
        opacity: float,
        overlay: bool,
    ) -> bool:
        """insert_textbox 시도 → 오버플로 시 높이 확장 재시도 → insert_text 폴백."""
        try:
            rc = page.insert_textbox(
                fitz_rect,
                text,
                fontsize=fontsize,
                fontname=fontname,
                color=color,
                align=align,
                rotate=rotation,
                fill_opacity=opacity,
                stroke_opacity=opacity,
                overlay=overlay,
            )
        except Exception:
            logger.warning("insert_textbox failed; trying insert_text fallback", exc_info=True)
            rc = -1.0

        # 음수 = 남은 높이 부족(텍스트 미기록 또는 부분 실패)
        if isinstance(rc, (int, float)) and rc < 0:
            expanded = fitz.Rect(
                fitz_rect.x0,
                fitz_rect.y0,
                fitz_rect.x1,
                fitz_rect.y1 + abs(float(rc)) + float(fontsize),
            )
            # 페이지 하단 클램프
            expanded.y1 = min(expanded.y1, page.rect.y1 - 2)
            if expanded.height > fitz_rect.height + 0.5:
                try:
                    rc2 = page.insert_textbox(
                        expanded,
                        text,
                        fontsize=fontsize,
                        fontname=fontname,
                        color=color,
                        align=align,
                        rotate=rotation,
                        fill_opacity=opacity,
                        stroke_opacity=opacity,
                        overlay=overlay,
                    )
                    if isinstance(rc2, (int, float)) and rc2 >= 0:
                        return True
                except Exception:
                    logger.debug("expanded insert_textbox failed", exc_info=True)

            # 최종 폴백: 기준점 텍스트 (항상 기록 시도)
            try:
                baseline = fitz.Point(
                    fitz_rect.x0,
                    min(fitz_rect.y0 + float(fontsize), page.rect.y1 - 2),
                )
                n = page.insert_text(
                    baseline,
                    text,
                    fontsize=fontsize,
                    fontname=fontname,
                    color=color,
                    rotate=rotation if rotation in (0, 90, 180, 270) else 0,
                    fill_opacity=opacity,
                    overlay=overlay,
                )
                return isinstance(n, (int, float)) and int(n) > 0
            except Exception:
                logger.warning("insert_text fallback failed", exc_info=True)
                return False

        # 성공 경로: 텍스트가 실제로 있는지 확인 (빈 성공 방지)
        try:
            sample = page.get_text("text") or ""
            # 입력 텍스트의 첫 토큰이 페이지에 있으면 OK (부분 매칭)
            token = text.strip().split()[0] if text.strip() else ""
            if token and token in sample:
                return True
            # CJK/공백 없는 문자열
            compact = text.strip()[:8]
            if compact and compact in sample.replace("\n", ""):
                return True
            # insert_textbox 양수 반환이면 공간은 남았다는 뜻 — 내용 기록된 것으로 간주
            if isinstance(rc, (int, float)) and rc >= 0:
                return True
        except Exception:
            if isinstance(rc, (int, float)) and rc >= 0:
                return True
        return False

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
