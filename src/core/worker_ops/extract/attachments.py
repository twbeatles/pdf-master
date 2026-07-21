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


class WorkerExtractAttachmentsMixin(WorkerHost):
    def list_attachments(self):
        """PDF 첨부 파일 목록"""
        file_path = _as_str(self.kwargs.get('file_path'))

        doc = self._open_pdf_document(file_path)
        attachments = []

        try:
            count = doc.embfile_count()
            for i in range(count):
                self._check_cancelled()
                info = doc.embfile_info(i)
                attachments.append({
                    'index': i,
                    'name': info.get('name', 'Unknown'),
                    'size': info.get('size', 0),
                    'created': info.get('creationDate', ''),
                })

            self.kwargs['result_attachments'] = attachments
            self._set_result_payload(attachments=attachments)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(self._get_msg("msg_attachments_listed", len(attachments)))
        finally:
            doc.close()

    def add_attachment(self):
        """PDF에 파일 첨부"""
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        attach_path = _as_str(self.kwargs.get("attach_path"))
        doc = None
        try:
            self._check_cancelled()
            doc = self._open_pdf_document(file_path)
            with open(attach_path, "rb") as handle:
                data = handle.read()

            self._check_cancelled()
            doc.embfile_add(os.path.basename(attach_path), data)
            self._atomic_pdf_save(doc, output_path)
        finally:
            if doc:
                doc.close()
        self._emit_progress_if_due(100)
        self.finished_signal.emit(
            self._get_msg("msg_attachment_added", os.path.basename(attach_path))
        )

    def extract_attachments(self):
        """PDF 첨부 파일 추출"""
        file_path = _as_str(self.kwargs.get("file_path"))
        output_dir = _as_str(self.kwargs.get("output_dir"))
        doc = None
        count = 0
        used_names: set[str] = set()
        try:
            os.makedirs(output_dir, exist_ok=True)
            doc = self._open_pdf_document(file_path)
            total = doc.embfile_count()

            if total == 0:
                self._emit_progress_if_due(100)
                self.finished_signal.emit(self._get_msg("msg_no_attachments_found"))
                return

            for i in range(total):
                self._check_cancelled()
                info = _as_dict(doc.embfile_info(i))
                data = doc.embfile_get(i)
                raw_name = info.get("name", f"attachment_{i + 1}")
                out_path, _saved_name = self._build_safe_attachment_output_path(output_dir, raw_name, i, used_names)
                self._atomic_binary_save(out_path, data)
                count += 1
                self._emit_progress_if_due(int((i + 1) / total * 100))
        finally:
            if doc:
                doc.close()
        self.finished_signal.emit(self._get_msg("msg_attachments_extracted", count))
