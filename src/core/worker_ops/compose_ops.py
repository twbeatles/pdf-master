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


class WorkerComposeOpsMixin(WorkerHost):
    def merge(self):
        files = [path for path in _as_list(self.kwargs.get('files')) if isinstance(path, str)]
        output_path = _as_str(self.kwargs.get('output_path'))
        if not files:
            self.error_signal.emit(self._get_msg("err_no_files_selected"))
            return
        if not output_path:
            self.error_signal.emit(self._get_msg("err_output_path_missing"))
            return

        # 유효한 파일만 필터링
        valid_files = [f for f in files if f and os.path.exists(f)]
        if not valid_files:
            self.error_signal.emit(self._get_msg("err_no_valid_pdf"))
            return

        skipped_count = 0
        doc_merged = fitz.open()
        try:
            for idx, path in enumerate(valid_files):
                self._check_cancelled()  # 취소 체크포인트
                try:
                    doc = self._open_pdf_document(path)
                    # v4.4: 암호화 PDF 감지
                    if doc.is_encrypted:
                        logger.warning(f"Encrypted PDF skipped: {path}")
                        skipped_count += 1
                        doc.close()
                        continue
                    doc_merged.insert_pdf(doc)
                    doc.close()
                except Exception as e:
                    logger.warning(f"Skipping {path}: {e}")
                    skipped_count += 1
                self._emit_progress_if_due(int((idx + 1) / len(valid_files) * 100))

            self._atomic_pdf_save(doc_merged, output_path)

            result_msg = f"✅ 병합 완료!\n{len(valid_files) - skipped_count}개 파일 → 1개 PDF"
            if skipped_count > 0:
                result_msg += f"\n⚠️ {skipped_count}개 파일 건너뜀"
            self.finished_signal.emit(result_msg)
        finally:
            doc_merged.close()

    def images_to_pdf(self):
        files = [path for path in _as_list(self.kwargs.get('files')) if isinstance(path, str)]
        output_path = _as_str(self.kwargs.get('output_path'))
        doc = None
        try:
            doc = fitz.open()
            for idx, img_path in enumerate(files):
                self._check_cancelled()  # 취소 체크포인트
                img = fitz.open(img_path)
                try:
                    pdf_bytes = img.convert_to_pdf()
                finally:
                    img.close()
                img_pdf = fitz.open("pdf", pdf_bytes)
                try:
                    doc.insert_pdf(img_pdf)
                finally:
                    img_pdf.close()
                self._emit_progress_if_due(int((idx + 1) / len(files) * 100))
            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(self._get_msg("msg_images_to_pdf_done", len(files)))
        finally:
            if doc:
                doc.close()

    def copy_page_between_docs(self):
        """다른 PDF에서 페이지 복사"""
        self._normalize_mode_kwargs()
        source_path = _as_str(self.kwargs.get('source_path'))
        target_path = _as_str(self.kwargs.get('target_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        source_pages = self.kwargs.get('source_pages')  # 복사할 페이지 번호들 (0-indexed)
        page_range = self.kwargs.get('page_range', '')
        insert_at = self.kwargs.get('insert_at', -1)  # 삽입 위치 (-1 = 끝)

        source_doc = self._open_pdf_document(source_path)
        target_doc = self._open_pdf_document(target_path)

        try:
            if source_pages is None:
                if isinstance(page_range, str) and page_range.strip():
                    source_pages = self._parse_page_range(page_range, len(source_doc))
                else:
                    self.error_signal.emit(self._get_msg("err_copy_pages_required"))
                    return
            elif isinstance(source_pages, int):
                source_pages = [source_pages]
            elif isinstance(source_pages, str):
                source_pages = self._parse_page_range(source_pages, len(source_doc))
            elif not isinstance(source_pages, list):
                self.error_signal.emit(self._get_msg("err_invalid_page_range", str(source_pages)))
                return

            if not source_pages:
                input_text = page_range if isinstance(page_range, str) and page_range.strip() else str(source_pages)
                self.error_signal.emit(self._get_msg("err_invalid_page_range", input_text))
                return

            normalized_source_pages = []
            for raw_page in source_pages:
                try:
                    page_num = int(raw_page)
                except (TypeError, ValueError):
                    self.error_signal.emit(self._get_msg("err_page_number_numeric", str(raw_page)))
                    return
                if page_num < 0 or page_num >= len(source_doc):
                    self.error_signal.emit(self._get_msg("err_page_out_of_range", str(page_num), str(len(source_doc))))
                    return
                normalized_source_pages.append(page_num)
            source_pages = normalized_source_pages

            try:
                insert_pos = int(insert_at)
            except (TypeError, ValueError):
                insert_pos = -1
            if insert_pos < 0:
                insert_pos = len(target_doc)
            insert_pos = min(insert_pos, len(target_doc))

            inserted_count = 0
            total_to_copy = max(1, len(source_pages))

            for i, page_num in enumerate(source_pages):
                self._check_cancelled()  # v4.5: 취소 체크포인트 추가
                target_doc.insert_pdf(source_doc, from_page=page_num, to_page=page_num, start_at=insert_pos + inserted_count)
                inserted_count += 1
                self._emit_progress_if_due(int((i + 1) / total_to_copy * 100))

            self._atomic_pdf_save(target_doc, output_path)
            self.finished_signal.emit(self._get_msg("msg_pages_copied", inserted_count))
        finally:
            source_doc.close()
            target_doc.close()
