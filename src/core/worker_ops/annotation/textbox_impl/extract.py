"""영역 클립 텍스트 추출 (memory payload)."""
from __future__ import annotations

import logging

from ...._typing import WorkerHost
from ....optional_deps import fitz
from ....worker_runtime.args import _as_int, _as_str
from .args import rect_from_source

logger = logging.getLogger(__name__)


class WorkerTextboxExtractMixin(WorkerHost):
    def extract_text_in_rect(self):
        """지정 페이지 사각형 클립 텍스트 추출 (memory payload)."""
        self._normalize_mode_kwargs()
        file_path = _as_str(self.kwargs.get("file_path"))
        page_num = _as_int(self.kwargs.get("page_num"), 0)
        rect = rect_from_source(
            self.kwargs,
            default_x=0.0,
            default_y=0.0,
            default_w=100.0,
            default_h=50.0,
        )

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


__all__ = ["WorkerTextboxExtractMixin"]
