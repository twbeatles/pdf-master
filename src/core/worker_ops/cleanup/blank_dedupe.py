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

class WorkerCleanupBlankDedupeMixin(WorkerHost):
    def remove_blank_pages(self):
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))

        doc = self._open_pdf_document(file_path)
        try:
            keep: list[int] = []
            total = len(doc)
            if total == 0:
                self.error_signal.emit(self._get_msg("err_pdf_has_no_pages"))
                return
            for i in range(total):
                self._check_cancelled()
                page = doc[i]
                if not _is_blank_page(page):
                    keep.append(i)
                self._emit_progress_if_due(int((i + 1) / total * 80))

            if not keep:
                self.error_signal.emit(self._get_msg("err_all_pages_blank"))
                return
            if len(keep) == total:
                # 변경 없음: 그래도 사본 저장
                self._atomic_pdf_save(doc, output_path)
                self._emit_progress_if_due(100)
                self.finished_signal.emit(self._get_msg("msg_remove_blank_none"))
                return

            out = fitz.open()
            try:
                for idx, page_index in enumerate(keep):
                    self._check_cancelled()
                    out.insert_pdf(doc, from_page=page_index, to_page=page_index)
                    self._emit_progress_if_due(80 + int((idx + 1) / len(keep) * 20))
                self._atomic_pdf_save(out, output_path)
            finally:
                out.close()

            removed = total - len(keep)
            self.finished_signal.emit(self._get_msg("msg_remove_blank_done", removed, len(keep)))
        finally:
            doc.close()

    def dedupe_pages(self):
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))

        doc = self._open_pdf_document(file_path)
        try:
            total = len(doc)
            if total == 0:
                self.error_signal.emit(self._get_msg("err_pdf_has_no_pages"))
                return
            seen: set[str] = set()
            keep: list[int] = []
            for i in range(total):
                self._check_cancelled()
                sig = _page_signature(doc[i])
                if sig in seen:
                    self._emit_progress_if_due(int((i + 1) / total * 80))
                    continue
                seen.add(sig)
                keep.append(i)
                self._emit_progress_if_due(int((i + 1) / total * 80))

            if len(keep) == total:
                self._atomic_pdf_save(doc, output_path)
                self.finished_signal.emit(self._get_msg("msg_dedupe_pages_none"))
                return

            out = fitz.open()
            try:
                for idx, page_index in enumerate(keep):
                    self._check_cancelled()
                    out.insert_pdf(doc, from_page=page_index, to_page=page_index)
                    self._emit_progress_if_due(80 + int((idx + 1) / len(keep) * 20))
                self._atomic_pdf_save(out, output_path)
            finally:
                out.close()
            self.finished_signal.emit(
                self._get_msg("msg_dedupe_pages_done", total - len(keep), len(keep))
            )
        finally:
            doc.close()
