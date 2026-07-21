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


class WorkerPageSplitDeleteMixin(WorkerHost):
    def split(self):
        file_path = _as_str(self.kwargs.get('file_path'))
        output_dir = _as_str(self.kwargs.get('output_dir'))
        page_range = _as_str(self.kwargs.get('page_range'))

        doc_src = self._open_pdf_document(file_path)
        doc_final = fitz.open()
        try:
            total_pages = len(doc_src)
            # v3.2: 개선된 페이지 파싱 유틸리티 사용
            pages_to_keep = self._parse_page_range(page_range, total_pages)

            # 원본 순서 유지를 위해 입력 문자열 재파싱 또는 set 정렬 사용
            # _parse_page_range는 정렬된 리스트를 반환하므로, 사용자가 입력한 순서가 중요하다면 로직 변경 필요
            # 현재 로직은 단순 추출이므로 정렬된 순서 유지

            if not pages_to_keep:
                raise ValueError(f"유효한 페이지 범위가 아닙니다: {page_range}")

            total_count = max(1, len(pages_to_keep))  # Division by zero 방지
            for idx, p_num in enumerate(pages_to_keep):
                self._check_cancelled()
                doc_final.insert_pdf(doc_src, from_page=p_num, to_page=p_num)
                self._emit_progress_if_due(int((idx + 1) / total_count * 100))

            base = os.path.splitext(os.path.basename(file_path))[0]
            out = os.path.join(output_dir, f"{base}_extracted.pdf")
            self._check_cancelled()
            self._atomic_pdf_save(doc_final, out)
            self.finished_signal.emit(self._get_msg("msg_pages_extracted", len(pages_to_keep)))
        finally:
            doc_src.close()
            doc_final.close()

    def delete_pages(self):
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_range = _as_str(self.kwargs.get('page_range'))
        doc = None
        try:
            doc = self._open_pdf_document(file_path)
            total_pages = len(doc)
            pages_to_delete = self._parse_page_range(page_range, total_pages)
            pages_to_delete = sorted(pages_to_delete, reverse=True)
            if not pages_to_delete:
                raise ValueError("삭제할 페이지가 없습니다.")
            total_to_delete = len(pages_to_delete)
            for idx, p in enumerate(pages_to_delete):
                self._check_cancelled()
                doc.delete_page(p)
                self._emit_progress_if_due(int((idx + 1) / total_to_delete * 90))
            self._atomic_pdf_save(doc, output_path)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(self._get_msg("msg_pages_deleted", len(pages_to_delete)))
        finally:
            if doc:
                doc.close()

    def split_by_pages(self):
        """PDF 분할 - 각 페이지를 개별 파일로"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_dir = _as_str(self.kwargs.get('output_dir'))
        split_mode = _as_str(self.kwargs.get('split_mode'), 'each')
        ranges = _as_str(self.kwargs.get('ranges'))

        doc = None
        try:
            doc = self._open_pdf_document(file_path)
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            page_count = len(doc)

            if split_mode == 'each':
                for i in range(page_count):
                    self._check_cancelled()  # 취소 체크포인트
                    new_doc = fitz.open()
                    try:
                        new_doc.insert_pdf(doc, from_page=i, to_page=i)
                        out_path = os.path.join(output_dir, f"{base_name}_page_{i+1}.pdf")
                        out_path_exists = os.path.exists(out_path)
                        self._atomic_pdf_save(new_doc, out_path)
                        if not out_path_exists:
                            self._record_created_output_path(out_path)
                    finally:
                        new_doc.close()
                    self._emit_progress_if_due(int((i + 1) / page_count * 100))
                self.finished_signal.emit(self._get_msg("msg_split_done", page_count))
            else:
                count = 0
                range_list = [r.strip() for r in ranges.split(',') if r.strip()]
                if not range_list:
                    self.error_signal.emit(self._get_msg("err_split_ranges_required"))
                    return

                total_ranges = len(range_list)
                for part_idx, rng in enumerate(range_list):
                    self._check_cancelled()  # 취소 체크포인트
                    try:
                        if '-' in rng:
                            parts = rng.split('-')
                            if len(parts) != 2:
                                logger.warning(f"잘못된 범위 형식: {rng}")
                                continue
                            start, end = int(parts[0]), int(parts[1])
                        else:
                            start = end = int(rng)

                        # 페이지 범위 유효성 검사
                        if start < 1 or end < 1:
                            logger.warning(f"유효하지 않은 페이지 번호: {rng}")
                            continue
                        if start > page_count or end > page_count:
                            logger.warning(f"페이지 범위 초과: {rng} (전체 {page_count}페이지)")
                            # 범위를 조정하여 계속 진행
                            start = min(start, page_count)
                            end = min(end, page_count)
                        if start > end:
                            start, end = end, start  # 역순이면 swap

                        new_doc = fitz.open()
                        try:
                            new_doc.insert_pdf(doc, from_page=start-1, to_page=end-1)
                            out_path = os.path.join(output_dir, f"{base_name}_part_{part_idx+1}.pdf")
                            out_path_exists = os.path.exists(out_path)
                            self._atomic_pdf_save(new_doc, out_path)
                            if not out_path_exists:
                                self._record_created_output_path(out_path)
                        finally:
                            new_doc.close()
                        count += 1
                        self._emit_progress_if_due(int((part_idx + 1) / total_ranges * 100))
                    except ValueError as e:
                        logger.warning(f"범위 파싱 오류: {rng} - {e}")
                        continue

                if count == 0:
                    self.error_signal.emit(self._get_msg("err_split_no_valid_ranges"))
                else:
                    self.finished_signal.emit(self._get_msg("msg_split_done", count))
        finally:
            if doc:
                doc.close()
