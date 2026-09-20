"""영역 텍스트 교체 (redact + insert)."""
from __future__ import annotations

import logging

from ....optional_deps import fitz
from ....worker_runtime.args import _as_int, _as_str
from .args import fill_from_source, rect_from_source, style_from_source
from .base import WorkerTextboxBaseMixin

logger = logging.getLogger(__name__)


class WorkerTextboxReplaceMixin(WorkerTextboxBaseMixin):
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

        rect = rect_from_source(self.kwargs)

        style = style_from_source(self.kwargs)
        fontsize = style["fontsize"]
        color = style["color"]
        align = style["align"]
        fontname = style["fontname"]
        opacity = style["opacity"]
        rotation = style["rotation"]
        layer = style["layer"]
        fill = fill_from_source(self.kwargs)

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


__all__ = ["WorkerTextboxReplaceMixin"]
