"""텍스트 상자 일괄 삽입 (세션 큐 커밋)."""
from __future__ import annotations

from ....optional_deps import fitz
from ....worker_runtime.args import _as_int, _as_str
from .args import rect_from_source, style_from_source
from .base import WorkerTextboxBaseMixin


class WorkerTextboxBatchMixin(WorkerTextboxBaseMixin):
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
                rect = rect_from_source(item)
                style = style_from_source(item)
                fontsize = style["fontsize"]
                color = style["color"]
                align = style["align"]
                fontname = style["fontname"]
                opacity = style["opacity"]
                rotation = style["rotation"]
                layer = style["layer"]
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


__all__ = ["WorkerTextboxBatchMixin"]
