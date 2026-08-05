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
    text_needs_cjk,
)
logger = logging.getLogger(__name__)

from .textbox_helpers import (
    ensure_textbox_rect,
    resolve_textbox_fontname,
    write_textbox_content,
)


class WorkerAnnotationTextboxMixin(WorkerHost):
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
            # 페이지 밖으로 완전히 벗어나면 침묵 폴백하지 않고 hard-fail (감사 §3.9)
            page_rect = page.rect
            fitz_rect = fitz_rect & page_rect
            if fitz_rect.is_empty or fitz_rect.width < 2 or fitz_rect.height < 2:
                self.error_signal.emit(self._get_msg("err_textbox_rect_outside_page"))
                return

            resolved_fontname = self._resolve_textbox_fontname(page, fontname, text)
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

    def insert_textboxes(self):
        """여러 텍스트 상자를 한 번에 삽입 (세션 큐 일괄 커밋)."""
        self._normalize_mode_kwargs()
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        raw_boxes = self.kwargs.get("boxes")
        if not isinstance(raw_boxes, list) or not raw_boxes:
            self.error_signal.emit(self._get_msg("err_textbox_queue_empty"))
            return

        doc = self._open_pdf_document(file_path)
        wrote_count = 0
        failed_indices: list[int] = []
        try:
            total = len(raw_boxes)
            for idx, item in enumerate(raw_boxes):
                self._check_cancelled()
                if not isinstance(item, dict):
                    failed_indices.append(idx + 1)
                    continue
                text = _as_str(item.get("text"))
                if not text.strip():
                    failed_indices.append(idx + 1)
                    continue
                page_num = _as_int(item.get("page_num"), 0)
                if page_num < 0 or page_num >= len(doc):
                    self.error_signal.emit(
                        self._get_msg("err_page_out_of_range", str(page_num + 1), str(len(doc)))
                    )
                    return
                rect_arg = item.get("rect")
                if rect_arg:
                    rect = [float(v) for v in cast(list[Any], rect_arg)]
                else:
                    x = _as_float(item.get("x"), 100.0)
                    y = _as_float(item.get("y"), 100.0)
                    w = _as_float(item.get("w"), 200.0)
                    h = _as_float(item.get("h"), 50.0)
                    rect = [x, y, x + w, y + h]
                fontsize = max(1, _as_int(item.get("fontsize"), 12))
                raw_color = item.get("color", [0, 0, 0])
                try:
                    color = tuple(float(c) for c in cast(list[Any] | tuple[Any, ...], raw_color)[:3])
                    if len(color) < 3:
                        color = (0.0, 0.0, 0.0)
                except Exception:
                    color = (0.0, 0.0, 0.0)
                align = _as_int(item.get("align"), 0)
                fontname = _as_str(item.get("fontname"), "helv")
                opacity = max(0.0, min(1.0, _as_float(item.get("opacity"), 1.0)))
                rotation = _as_int(item.get("rotation"), 0) % 360
                rotation = int(round(rotation / 90.0) * 90) % 360
                layer = _as_str(item.get("layer"), "foreground")
                rect = self._ensure_textbox_rect(rect, text, fontsize)

                page = doc[page_num]
                fitz_rect = fitz.Rect(rect) & page.rect
                if fitz_rect.is_empty or fitz_rect.width < 2 or fitz_rect.height < 2:
                    failed_indices.append(idx + 1)
                    continue
                resolved_fontname = self._resolve_textbox_fontname(page, fontname, text)
                ok = self._write_textbox_content(
                    page,
                    fitz_rect,
                    text,
                    fontsize=fontsize,
                    fontname=resolved_fontname,
                    color=color,
                    align=align,
                    rotation=rotation,
                    opacity=opacity,
                    overlay=layer != "background",
                )
                if ok:
                    wrote_count += 1
                else:
                    failed_indices.append(idx + 1)
                self._emit_progress_if_due(int((idx + 1) / total * 100))

            if wrote_count <= 0:
                self.error_signal.emit(self._get_msg("err_textbox_insert_failed"))
                return
            self._atomic_pdf_save(doc, output_path)
            self._emit_progress_if_due(100)
            if failed_indices:
                # 부분 성공: 실패한 큐 번호(1-based) 요약
                preview = ", ".join(str(i) for i in failed_indices[:8])
                if len(failed_indices) > 8:
                    preview += "…"
                self.finished_signal.emit(
                    self._get_msg(
                        "msg_textboxes_inserted_partial",
                        wrote_count,
                        len(failed_indices),
                        preview,
                    )
                )
            else:
                self.finished_signal.emit(self._get_msg("msg_textboxes_inserted", wrote_count))
        finally:
            doc.close()

    def replace_text_in_rect(self):
        """영역 내 기존 내용을 교정(redact)한 뒤 새 텍스트 상자를 삽입."""
        self._normalize_mode_kwargs()
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        page_num = _as_int(self.kwargs.get("page_num"), 0)
        text = _as_str(self.kwargs.get("text"))
        if not text.strip():
            self.error_signal.emit(self._get_msg("msg_enter_text"))
            return

        rect_arg = self.kwargs.get("rect")
        if rect_arg:
            rect = [float(v) for v in cast(list[Any], rect_arg)]
        else:
            x = _as_float(self.kwargs.get("x"), 100.0)
            y = _as_float(self.kwargs.get("y"), 100.0)
            w = _as_float(self.kwargs.get("w"), 200.0)
            h = _as_float(self.kwargs.get("h"), 50.0)
            rect = [x, y, x + w, y + h]

        fontsize = max(1, _as_int(self.kwargs.get("fontsize"), 12))
        raw_color = self.kwargs.get("color", [0, 0, 0])
        try:
            color = tuple(float(c) for c in cast(list[Any] | tuple[Any, ...], raw_color)[:3])
            if len(color) < 3:
                color = (0.0, 0.0, 0.0)
        except Exception:
            color = (0.0, 0.0, 0.0)
        align = _as_int(self.kwargs.get("align"), 0)
        fontname = _as_str(self.kwargs.get("fontname"), "helv")
        opacity = max(0.0, min(1.0, _as_float(self.kwargs.get("opacity"), 1.0)))
        rotation = _as_int(self.kwargs.get("rotation"), 0) % 360
        rotation = int(round(rotation / 90.0) * 90) % 360
        layer = _as_str(self.kwargs.get("layer"), "foreground")
        fill_color = self.kwargs.get("fill_color", (1, 1, 1))
        try:
            fill = tuple(float(c) for c in cast(list[Any] | tuple[Any, ...], fill_color)[:3])
            if len(fill) < 3:
                fill = (1.0, 1.0, 1.0)
        except Exception:
            fill = (1.0, 1.0, 1.0)

        rect = self._ensure_textbox_rect(rect, text, fontsize)
        doc = self._open_pdf_document(file_path)
        try:
            if page_num < 0 or page_num >= len(doc):
                self.error_signal.emit(
                    self._get_msg("err_page_out_of_range", str(page_num + 1), str(len(doc)))
                )
                return
            page = doc[page_num]
            fitz_rect = fitz.Rect(rect) & page.rect
            if fitz_rect.is_empty or fitz_rect.width < 2 or fitz_rect.height < 2:
                self.error_signal.emit(self._get_msg("err_textbox_insert_failed"))
                return

            self._check_cancelled()
            try:
                annot = page.add_redact_annot(fitz_rect, fill=fill)
                if annot is not None:
                    annot.update()
                page.apply_redactions()
            except Exception:
                logger.warning("redact before replace_text_in_rect failed", exc_info=True)
                # 교정 실패 시 insert를 계속하면 "교체"가 "추가"로 변질 → hard-fail
                self.error_signal.emit(self._get_msg("err_textbox_redact_failed"))
                return
            self._check_cancelled()

            resolved_fontname = self._resolve_textbox_fontname(page, fontname, text)
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
                overlay=layer != "background",
            )
            if not wrote:
                self.error_signal.emit(self._get_msg("err_textbox_insert_failed"))
                return
            self._atomic_pdf_save(doc, output_path)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(self._get_msg("msg_text_replaced_in_rect", page_num + 1))
        finally:
            doc.close()

    def extract_text_in_rect(self):
        """지정 페이지 사각형 클립 텍스트 추출 (memory payload)."""
        self._normalize_mode_kwargs()
        file_path = _as_str(self.kwargs.get("file_path"))
        page_num = _as_int(self.kwargs.get("page_num"), 0)
        rect_arg = self.kwargs.get("rect")
        if rect_arg:
            rect = [float(v) for v in cast(list[Any], rect_arg)]
        else:
            x = _as_float(self.kwargs.get("x"), 0.0)
            y = _as_float(self.kwargs.get("y"), 0.0)
            w = _as_float(self.kwargs.get("w"), 100.0)
            h = _as_float(self.kwargs.get("h"), 50.0)
            rect = [x, y, x + w, y + h]

        doc = self._open_pdf_document(file_path)
        try:
            if page_num < 0 or page_num >= len(doc):
                self.error_signal.emit(
                    self._get_msg("err_page_out_of_range", str(page_num + 1), str(len(doc)))
                )
                return
            self._check_cancelled()
            page = doc[page_num]
            clip = fitz.Rect(
                min(rect[0], rect[2]),
                min(rect[1], rect[3]),
                max(rect[0], rect[2]),
                max(rect[1], rect[3]),
            )
            clip = clip & page.rect
            text = ""
            if not clip.is_empty:
                try:
                    text = (page.get_text("text", clip=clip) or "").strip()
                except Exception:
                    logger.debug("extract_text_in_rect get_text failed", exc_info=True)
                    text = ""
            self._set_result_payload(
                text=text,
                page_num=page_num,
                rect=[float(clip.x0), float(clip.y0), float(clip.x1), float(clip.y1)],
            )
            self._emit_progress_if_due(100)
            self.finished_signal.emit(
                self._get_msg("msg_text_extracted_in_rect", page_num + 1, len(text))
            )
        finally:
            doc.close()

    def _ensure_textbox_rect(
        self, rect: list[float], text: str, fontsize: int
    ) -> list[float]:
        """폰트 크기·줄 수에 맞게 최소 높이를 확보한다."""
        return ensure_textbox_rect(rect, text, fontsize)

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
        return write_textbox_content(
            page,
            fitz_rect,
            text,
            fontsize=fontsize,
            fontname=fontname,
            color=color,
            align=align,
            rotation=rotation,
            opacity=opacity,
            overlay=overlay,
        )

    def _resolve_textbox_fontname(self, page: Any, fontname: str, text: str = "") -> str:
        """UI/별칭 폰트명을 PyMuPDF insert_textbox 가 받을 수 있는 이름으로 해석."""
        return resolve_textbox_fontname(page, fontname, text)

