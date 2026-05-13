from __future__ import annotations

import csv
import io
import json
import logging
import os
from collections import Counter
from typing import Any, cast

from .._typing import WorkerHost
from ..constants import (
    DEFAULT_PAGE_SIZE,
    WATERMARK_DEFAULTS,
    WATERMARK_TILE_SPACING_X,
    WATERMARK_TILE_SPACING_Y,
)
from ..optional_deps import fitz
from ..worker_runtime.args import (
    _as_bool,
    _as_dict,
    _as_float,
    _as_int,
    _as_list,
    _as_str,
)
from ._pdf_helpers import (
    _extract_page_markdown,
    _fallback_markdown_from_text,
    _markdown_front_matter,
    _normalize_stroke_points,
    _page_asset_placeholders,
    _sample_diff_text,
)

logger = logging.getLogger(__name__)

FITZ_PDF_PERM_ACCESSIBILITY = int(getattr(fitz, "PDF_PERM_ACCESSIBILITY", 0))
FITZ_PDF_PERM_ANNOTATE = int(getattr(fitz, "PDF_PERM_ANNOTATE", 0))
FITZ_PDF_PERM_ASSEMBLE = int(getattr(fitz, "PDF_PERM_ASSEMBLE", 0))
FITZ_PDF_PERM_COPY = int(getattr(fitz, "PDF_PERM_COPY", 0))
FITZ_PDF_PERM_FORM = int(getattr(fitz, "PDF_PERM_FORM", 0))
FITZ_PDF_PERM_MODIFY = int(getattr(fitz, "PDF_PERM_MODIFY", 0))
FITZ_PDF_PERM_PRINT = int(getattr(fitz, "PDF_PERM_PRINT", 0))
FITZ_PDF_PERM_PRINT_HQ = int(getattr(fitz, "PDF_PERM_PRINT_HQ", 0))
FITZ_PDF_ENCRYPT_AES_256 = int(getattr(fitz, "PDF_ENCRYPT_AES_256", 0))


class WorkerSecurityOpsMixin(WorkerHost):
    def protect(self):
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        pw = _as_str(self.kwargs.get('password'))
        doc = None
        try:
            if not pw:
                self.error_signal.emit(self._get_msg("err_password_required"))
                return

            doc = self._open_pdf_document(file_path)
            perm = FITZ_PDF_PERM_ACCESSIBILITY | FITZ_PDF_PERM_PRINT | FITZ_PDF_PERM_COPY
            self._atomic_pdf_save(
                doc,
                output_path,
                encryption=FITZ_PDF_ENCRYPT_AES_256,
                owner_pw=pw,
                user_pw=pw,
                permissions=perm,
            )
            self._emit_progress_if_due(100)
            self.finished_signal.emit(self._get_msg("msg_encryption_success"))
        finally:
            if doc:
                doc.close()

    def decrypt_pdf(self):
        """암호화된 PDF 복호화"""
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        password = _as_str(self.kwargs.get("password"))
        doc = None
        try:
            doc = self._open_pdf_document(file_path, password=password)

            self._atomic_pdf_save(doc, output_path, save_profile="compact", garbage=4, deflate=True)
        finally:
            if doc:
                doc.close()
        self._emit_progress_if_due(100)
        self.finished_signal.emit(self._get_msg("msg_decryption_success"))
