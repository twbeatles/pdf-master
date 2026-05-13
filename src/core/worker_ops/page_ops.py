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


class WorkerPageOpsMixin(WorkerHost):
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

    def rotate(self):
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        angle = _as_int(self.kwargs.get('angle'))
        raw_page_indices = self.kwargs.get('page_indices')

        doc = self._open_pdf_document(file_path)
        try:
            total_pages = len(doc)
            if total_pages <= 0:
                self.error_signal.emit(self._get_msg("err_pdf_has_no_pages"))
                return

            if raw_page_indices is None:
                page_indices = list(range(total_pages))
            else:
                if isinstance(raw_page_indices, (list, tuple, set)):
                    requested_indices = list(raw_page_indices)
                else:
                    requested_indices = [raw_page_indices]

                page_indices = []
                seen = set()
                for raw_page_index in requested_indices:
                    try:
                        page_index = int(raw_page_index)
                    except (TypeError, ValueError):
                        self.error_signal.emit(self._get_msg("err_page_number_numeric", str(raw_page_index)))
                        return
                    if page_index < 0 or page_index >= total_pages:
                        self.error_signal.emit(
                            self._get_msg("err_page_out_of_range", str(page_index + 1), str(total_pages))
                        )
                        return
                    if page_index not in seen:
                        seen.add(page_index)
                        page_indices.append(page_index)

            if not page_indices:
                self.error_signal.emit(self._get_msg("msg_select_rotate_pages"))
                return

            total_to_rotate = max(1, len(page_indices))
            for idx, page_index in enumerate(page_indices):
                page = doc[page_index]
                self._check_cancelled()  # 취소 체크포인트
                page.set_rotation(page.rotation + angle)
                self._emit_progress_if_due(int((idx + 1) / total_to_rotate * 100))
            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(self._get_msg("msg_pages_rotated", len(page_indices), angle))
        finally:
            doc.close()

    def reorder(self):
        """페이지 순서 변경"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_order = [_as_int(page_num) for page_num in _as_list(self.kwargs.get('page_order'))]

        doc_src = None
        doc_out = None
        try:
            doc_src = self._open_pdf_document(file_path)
            doc_out = fitz.open()

            for idx, page_num in enumerate(page_order):
                self._check_cancelled()  # 취소 체크포인트
                doc_out.insert_pdf(doc_src, from_page=page_num, to_page=page_num)
                self._emit_progress_if_due(int((idx + 1) / len(page_order) * 100))

            self._atomic_pdf_save(doc_out, output_path)
            self.finished_signal.emit(self._get_msg("msg_reorder_done", len(page_order)))
        finally:
            if doc_out:
                doc_out.close()
            if doc_src:
                doc_src.close()

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

    def add_page_numbers(self):
        """페이지 번호 삽입"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        position = _as_str(self.kwargs.get('position'), 'bottom')  # bottom, top, bottom-left, bottom-right, top-left, top-right
        format_str = _as_str(self.kwargs.get('format'), '{n} / {total}')
        fontsize = _as_int(self.kwargs.get('fontsize'), 10)
        fontname = _as_str(self.kwargs.get('fontname'), 'helv')
        color = self.kwargs.get('color', (0, 0, 0))
        margin = _as_int(self.kwargs.get('margin'), 30)
        start_number = _as_int(self.kwargs.get('start_number'), 1)  # 시작 번호
        skip_first = _as_bool(self.kwargs.get('skip_first'), False)  # 첫 페이지 건너뛰기
        use_roman = _as_bool(self.kwargs.get('use_roman'), False)  # v3.2: 로마 숫자 형식

        def to_roman(num):
            """숫자를 로마 숫자로 변환"""
            val = [(1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'),
                   (100, 'C'), (90, 'XC'), (50, 'L'), (40, 'XL'),
                   (10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]
            roman = ''
            for v, r in val:
                while num >= v:
                    roman += r
                    num -= v
            return roman

        doc = self._open_pdf_document(file_path)
        try:
            total = len(doc)

            for i in range(total):
                page = doc[i]
                self._check_cancelled()  # 취소 체크포인트
                if skip_first and i == 0:
                    continue

                page_num = start_number + i if not skip_first else start_number + i - 1

                # v3.2: 로마 숫자 변환
                if use_roman:
                    num_str = to_roman(page_num)
                    total_str = to_roman(total)
                else:
                    num_str = str(page_num)
                    total_str = str(total)

                text = format_str.replace('{n}', num_str).replace('{total}', total_str)
                rect = page.rect

                # 위치별 텍스트박스 영역 설정
                if position == 'bottom' or position == 'bottom-center':
                    r = fitz.Rect(0, rect.height - margin - 20, rect.width, rect.height - margin)
                    align = 1  # center
                elif position == 'top' or position == 'top-center':
                    r = fitz.Rect(0, margin, rect.width, margin + 20)
                    align = 1
                elif position == 'bottom-left':
                    r = fitz.Rect(margin, rect.height - margin - 20, 150, rect.height - margin)
                    align = 0  # left
                elif position == 'bottom-right':
                    r = fitz.Rect(rect.width - 150, rect.height - margin - 20, rect.width - margin, rect.height - margin)
                    align = 2  # right
                elif position == 'top-left':
                    r = fitz.Rect(margin, margin, 150, margin + 20)
                    align = 0
                elif position == 'top-right':
                    r = fitz.Rect(rect.width - 150, margin, rect.width - margin, margin + 20)
                    align = 2
                else:
                    r = fitz.Rect(0, rect.height - margin - 20, rect.width, rect.height - margin)
                    align = 1

                page.insert_textbox(r, text, fontsize=fontsize, fontname=fontname, color=color, align=align)
                self._emit_progress_if_due(int((i + 1) / total * 100))

            self._atomic_pdf_save(doc, output_path)
            format_type = self._get_msg(
                "msg_page_number_format_roman" if use_roman else "msg_page_number_format_arabic"
            )
            self.finished_signal.emit(self._get_msg("msg_page_numbers_done", format_type, total))
        finally:
            doc.close()

    def insert_blank_page(self):
        """빈 페이지 삽입"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        position = _as_int(self.kwargs.get('position'), 0)

        doc = self._open_pdf_document(file_path)
        try:
            if position < 0 or position > len(doc):
                self.error_signal.emit(
                    self._get_msg("err_page_out_of_range", str(position + 1), str(len(doc) + 1))
                )
                return
            width, height = DEFAULT_PAGE_SIZE  # A4
            doc.insert_page(position, width=width, height=height)
            self._atomic_pdf_save(doc, output_path)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(self._get_msg("msg_blank_page_inserted", position + 1))
        finally:
            doc.close()

    def replace_page(self):
        """특정 페이지 교체"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        replace_path = _as_str(self.kwargs.get('replace_path'))
        target_page = _as_int(self.kwargs.get('target_page'), 1) - 1
        source_page = _as_int(self.kwargs.get('source_page'), 1) - 1

        doc = self._open_pdf_document(file_path)
        replace_doc = self._open_pdf_document(replace_path)
        try:
            # 입력 검증
            if target_page < 0 or target_page >= len(doc):
                self.error_signal.emit(self._get_msg("err_target_page_invalid", target_page + 1))
                return
            if source_page < 0 or source_page >= len(replace_doc):
                self.error_signal.emit(self._get_msg("err_source_page_invalid", source_page + 1))
                return

            doc.delete_page(target_page)
            doc.insert_pdf(replace_doc, from_page=source_page, to_page=source_page, start_at=target_page)

            self._atomic_pdf_save(doc, output_path)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(self._get_msg("msg_page_replaced"))
        finally:
            replace_doc.close()
            doc.close()

    def duplicate_page(self):
        """페이지 복제"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_num = _as_int(self.kwargs.get('page_num'), 0)  # 0-indexed
        count = _as_int(self.kwargs.get('count'), 1)

        doc = self._open_pdf_document(file_path)
        try:
            resolved_page_num = self._resolve_page_index(page_num, len(doc))
            if resolved_page_num is None:
                return
            for i in range(count):
                self._check_cancelled()  # 취소 체크포인트
                doc.fullcopy_page(resolved_page_num, resolved_page_num + 1 + i)
                self._emit_progress_if_due(int((i + 1) / count * 100))

            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(self._get_msg("msg_page_duplicated", resolved_page_num + 1, count))
        finally:
            doc.close()

    def reverse_pages(self):
        """페이지 역순 정렬"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))

        doc = self._open_pdf_document(file_path)
        try:
            page_count = len(doc)

            # 단일 페이지 PDF 처리
            if page_count <= 1:
                self._atomic_pdf_save(doc, output_path)
                self._emit_progress_if_due(100)
                self.finished_signal.emit(self._get_msg("msg_reverse_done_single"))
                return

            # 역순으로 페이지 이동
            for i in range(page_count - 1):
                self._check_cancelled()  # 취소 체크포인트
                doc.move_page(page_count - 1, i)
                self._emit_progress_if_due(int((i + 1) / (page_count - 1) * 100))

            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(self._get_msg("msg_reverse_done", page_count))
        finally:
            doc.close()
