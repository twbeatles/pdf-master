"""단일 텍스트 상자 삽입."""
from __future__ import annotations

from ....optional_deps import fitz
from ....worker_runtime.args import _as_int, _as_str
from .args import rect_from_source, style_from_source
from .base import WorkerTextboxBaseMixin


class WorkerTextboxSingleMixin(WorkerTextboxBaseMixin):
    def insert_textbox(self):
        """PDF에 텍스트 상자/선택 위치 워터마크 삽입"""
        self._normalize_mode_kwargs()
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        page_num = _as_int(self.kwargs.get("page_num"), 0)

        # rect or (x, y[, w, h])
        rect = rect_from_source(self.kwargs, use_size_aliases=True)

        text = _as_str(self.kwargs.get("text"))
        style = style_from_source(self.kwargs)
        fontsize = style["fontsize"]
        color = style["color"]
        align = style["align"]
        fontname = style["fontname"]
        opacity = style["opacity"]
        rotation = style["rotation"]
        layer = style["layer"]

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
            overlay = layer != "background"
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


__all__ = ["WorkerTextboxSingleMixin"]
