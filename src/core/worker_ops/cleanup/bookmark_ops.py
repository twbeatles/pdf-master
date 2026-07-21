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

class WorkerCleanupBookmarkOpsMixin(WorkerHost):
    def split_by_bookmarks(self):
        """북마크(목차) 기준으로 PDF 분할."""
        file_path = _as_str(self.kwargs.get("file_path"))
        output_dir = _as_str(self.kwargs.get("output_dir"))
        max_level = _as_int(self.kwargs.get("max_level"), 1)

        doc = self._open_pdf_document(file_path)
        try:
            toc = cast(list[list[Any]], doc.get_toc(simple=True) or [])
            # [level, title, page] 1-based page
            entries = [
                (int(item[0]), str(item[1]).strip(), int(item[2]))
                for item in toc
                if isinstance(item, (list, tuple)) and len(item) >= 3
            ]
            entries = [e for e in entries if e[0] <= max(1, max_level) and e[1] and e[2] >= 1]
            if not entries:
                self.error_signal.emit(self._get_msg("err_no_bookmarks_to_split"))
                return

            page_count = len(doc)
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            os.makedirs(output_dir, exist_ok=True)
            used_stems: set[str] = set()
            created = 0

            for idx, (_level, title, start_page) in enumerate(entries):
                self._check_cancelled()
                start = max(1, min(start_page, page_count))
                if idx + 1 < len(entries):
                    next_start = max(1, min(entries[idx + 1][2], page_count + 1))
                    end = max(start, next_start - 1)
                else:
                    end = page_count
                if end < start:
                    continue

                safe_title = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", title).strip(" .") or f"part_{idx + 1}"
                safe_title = safe_title[:60]
                stem = self._build_unique_output_stem(
                    output_dir,
                    f"{base_name}_{idx + 1:02d}_{safe_title}",
                    ".pdf",
                    used_stems,
                )
                out_path = os.path.join(output_dir, f"{stem}.pdf")
                part = fitz.open()
                try:
                    part.insert_pdf(doc, from_page=start - 1, to_page=end - 1)
                    self._atomic_pdf_save(part, out_path)
                finally:
                    part.close()
                created += 1
                self._emit_progress_if_due(int((idx + 1) / max(1, len(entries)) * 100))

            if created == 0:
                self.error_signal.emit(self._get_msg("err_split_no_valid_ranges"))
                return
            self.finished_signal.emit(self._get_msg("msg_split_by_bookmarks_done", created))
        finally:
            doc.close()

    def auto_bookmarks(self):
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        min_size = _as_float(self.kwargs.get("min_heading_size"), _HEADING_MIN_SIZE)

        doc = self._open_pdf_document(file_path)
        try:
            toc = _collect_heading_toc(
                doc,
                min_size=min_size or _HEADING_MIN_SIZE,
                check_cancelled=self._check_cancelled,
            )
            if not toc:
                self.error_signal.emit(self._get_msg("err_no_headings_for_bookmarks"))
                return
            self._check_cancelled()
            doc.set_toc(toc)
            self._atomic_pdf_save(doc, output_path)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(self._get_msg("msg_auto_bookmarks_done", len(toc)))
        finally:
            doc.close()
