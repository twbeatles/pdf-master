from __future__ import annotations

import hashlib
import logging
import os
import re
from collections import Counter
from typing import Any, cast
from ..._typing import WorkerHost
from ...optional_deps import fitz
from ...worker_runtime.args import (
    _as_bool,
    _as_float,
    _as_int,
    _as_list,
    _as_str,
)
logger = logging.getLogger(__name__)
_HEADING_MIN_SIZE = 12.0
_HEADING_SIZE_GAP = 1.5


from .helpers import _page_text_len, _page_image_count, _page_drawing_count, _is_blank_page, _page_signature, _content_bbox, _collect_heading_toc

class WorkerCleanupSanitizeNupMixin(WorkerHost):
    def sanitize_pdf(self):
        """메타데이터·첨부·(옵션) 주석 제거 후 클린 저장."""
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        remove_annotations = _as_bool(self.kwargs.get("remove_annotations"), True)
        remove_attachments = _as_bool(self.kwargs.get("remove_attachments"), True)
        remove_links = _as_bool(self.kwargs.get("remove_links"), False)
        remove_bookmarks = _as_bool(self.kwargs.get("remove_bookmarks"), False)

        doc = self._open_pdf_document(file_path)
        try:
            total = max(1, len(doc))
            # 메타데이터 비우기
            empty_meta = {
                "title": "",
                "author": "",
                "subject": "",
                "keywords": "",
                "creator": "",
                "producer": "",
            }
            try:
                doc.set_metadata(empty_meta)
            except Exception as exc:
                logger.debug("metadata scrub failed: %s", exc)

            # XML metadata
            try:
                if hasattr(doc, "del_xml_metadata"):
                    doc.del_xml_metadata()
                elif hasattr(doc, "set_xml_metadata"):
                    doc.set_xml_metadata("")
            except Exception as exc:
                logger.debug("xml metadata scrub failed: %s", exc)

            if remove_bookmarks:
                try:
                    doc.set_toc([])
                except Exception:
                    pass

            if remove_attachments:
                try:
                    names = list(doc.embfile_names() or [])
                    for name in names:
                        try:
                            doc.embfile_del(name)
                        except Exception:
                            logger.debug("attachment delete failed: %s", name)
                except Exception:
                    pass

            for page_index in range(len(doc)):
                self._check_cancelled()
                page = doc[page_index]
                if remove_annotations:
                    annot = page.first_annot
                    while annot:
                        next_annot = annot.next
                        try:
                            page.delete_annot(annot)
                        except Exception:
                            pass
                        annot = next_annot
                if remove_links:
                    try:
                        links = page.get_links() or []
                        for link in links:
                            try:
                                page.delete_link(link)
                            except Exception:
                                pass
                    except Exception:
                        pass
                self._emit_progress_if_due(int((page_index + 1) / total * 90))

            # open action / JS 가능한 경우 제거
            try:
                if hasattr(doc, "set_open_action"):
                    doc.set_open_action(None)  # type: ignore[arg-type]
            except Exception:
                pass

            self._atomic_pdf_save(doc, output_path, save_profile="compact")
            self._emit_progress_if_due(100)
            self.finished_signal.emit(self._get_msg("msg_sanitize_done"))
        finally:
            doc.close()

    def impose_nup(self):
        """N-up 임포지션 (2 또는 4)."""
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        nup = _as_int(self.kwargs.get("nup"), 2)
        if nup not in (2, 4):
            nup = 2

        doc = self._open_pdf_document(file_path)
        out = fitz.open()
        try:
            total = len(doc)
            if total == 0:
                self.error_signal.emit(self._get_msg("err_pdf_has_no_pages"))
                return

            # 첫 페이지 크기 기준
            src_rect = doc[0].rect
            if nup == 2:
                cols, rows = 2, 1
                sheet_w = src_rect.width * 2
                sheet_h = src_rect.height
            else:
                cols, rows = 2, 2
                sheet_w = src_rect.width * 2
                sheet_h = src_rect.height * 2

            per_sheet = cols * rows
            sheet_count = (total + per_sheet - 1) // per_sheet

            for sheet_idx in range(sheet_count):
                self._check_cancelled()
                new_page = out.new_page(width=sheet_w, height=sheet_h)
                for slot in range(per_sheet):
                    page_index = sheet_idx * per_sheet + slot
                    if page_index >= total:
                        break
                    col = slot % cols
                    row = slot // cols
                    target = fitz.Rect(
                        col * src_rect.width,
                        row * src_rect.height,
                        (col + 1) * src_rect.width,
                        (row + 1) * src_rect.height,
                    )
                    # 원본 페이지 비율 유지 fit
                    page = doc[page_index]
                    pr = page.rect
                    scale = min(target.width / max(pr.width, 1), target.height / max(pr.height, 1))
                    rw, rh = pr.width * scale, pr.height * scale
                    ox = target.x0 + (target.width - rw) / 2
                    oy = target.y0 + (target.height - rh) / 2
                    fit = fitz.Rect(ox, oy, ox + rw, oy + rh)
                    new_page.show_pdf_page(fit, doc, page_index)
                self._emit_progress_if_due(int((sheet_idx + 1) / sheet_count * 100))

            self._atomic_pdf_save(out, output_path)
            self.finished_signal.emit(self._get_msg("msg_impose_nup_done", nup, sheet_count))
        finally:
            out.close()
            doc.close()
