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
    PAGE_SIZES,
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


class WorkerAnnotationOpsMixin(WorkerHost):
    def watermark(self):
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        text = _as_str(self.kwargs.get('text'))
        opacity = _as_float(self.kwargs.get('opacity'), 0.3)
        color = tuple(self.kwargs.get('color', (0.5, 0.5, 0.5)))
        fontsize = _as_int(self.kwargs.get('fontsize'), 40)
        rotation = _as_int(self.kwargs.get('rotation'), 45)
        fontname = _as_str(self.kwargs.get('fontname'), 'helv')
        position = _as_str(self.kwargs.get('position'), 'center')
        layer = _as_str(self.kwargs.get('layer'), 'foreground')
        scale_percent = _as_int(self.kwargs.get('scale_percent'), 100)

        # v4.5: 입력 검증 강화
        valid_positions = ['center', 'tile', 'top', 'bottom', 'top-left', 'top-right', 'bottom-left', 'bottom-right']
        if position not in valid_positions:
            logger.warning(f"Invalid watermark position '{position}', defaulting to 'center'")
            position = 'center'

        # opacity 범위 제한
        opacity = max(0.0, min(1.0, opacity))

        actual_fontsize = int(fontsize * scale_percent / 100)

        doc = self._open_pdf_document(file_path)
        try:
            # 입력 검증
            if not text:
                self.error_signal.emit(self._get_msg("err_watermark_text_required"))
                return

            total_pages = max(1, len(doc))
            margin = 50  # 가장자리 여백

            for i in range(len(doc)):
                page = doc[i]
                self._check_cancelled()
                rect = page.rect

                # v4.5: 모든 위치 옵션 지원
                positions = {
                    'center': (rect.width / 2, rect.height / 2),
                    'top': (rect.width / 2, margin + actual_fontsize),
                    'bottom': (rect.width / 2, rect.height - margin),
                    'top-left': (margin, margin + actual_fontsize),
                    'top-right': (rect.width - margin, margin + actual_fontsize),
                    'bottom-left': (margin, rect.height - margin),
                    'bottom-right': (rect.width - margin, rect.height - margin),
                }

                if layer == 'background':
                    shape = page.new_shape()
                    if position == 'tile':
                        for y in range(0, int(rect.height), 200):
                            for x in range(0, int(rect.width), 300):
                                shape.insert_text(
                                    fitz.Point(x, y), text, fontsize=actual_fontsize,
                                    fontname=fontname, rotate=rotation,
                                    color=color, fill_opacity=opacity
                                )
                    else:
                        x, y = positions.get(position, positions['center'])
                        shape.insert_text(
                            fitz.Point(x, y), text, fontsize=actual_fontsize,
                            fontname=fontname, rotate=rotation,
                            color=color, fill_opacity=opacity
                        )
                    shape.commit(overlay=False)
                else:
                    if position == 'tile':
                        for y in range(0, int(rect.height), 200):
                            for x in range(0, int(rect.width), 300):
                                page.insert_text(
                                    fitz.Point(x, y), text, fontsize=actual_fontsize,
                                    fontname=fontname, rotate=rotation,
                                    color=color, fill_opacity=opacity
                                )
                    else:
                        x, y = positions.get(position, positions['center'])
                        page.insert_text(
                            fitz.Point(x, y), text, fontsize=actual_fontsize,
                            fontname=fontname, rotate=rotation,
                            color=color, fill_opacity=opacity
                        )
                self._emit_progress_if_due(int((i + 1) / total_pages * 100))
            self._atomic_pdf_save(doc, output_path)
            layer_name = self._get_msg("msg_layer_background" if layer == 'background' else "msg_layer_foreground")
            self.finished_signal.emit(self._get_msg("msg_watermark_applied", layer_name, int(opacity * 100)))
        finally:
            doc.close()

    def add_annotation(self):
        """PDF에 주석 추가"""
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        page_num = _as_int(self.kwargs.get("page_num"), 0)
        annot_type = _as_str(self.kwargs.get("annot_type"), "text")
        text = _as_str(self.kwargs.get("text"))
        point = cast(list[float], self.kwargs.get("point") or [100, 100])
        rect = cast(list[float], self.kwargs.get("rect") or [100, 100, 300, 150])
        doc = None
        try:
            doc = self._open_pdf_document(file_path)
            if page_num < 0 or page_num >= len(doc):
                self.error_signal.emit(self._get_msg("err_page_out_of_range", str(page_num + 1), str(len(doc))))
                return

            page = doc[page_num]
            annot = None
            if annot_type in ("text", "sticky"):
                annot = page.add_text_annot(fitz.Point(point[0], point[1]), text)
            elif annot_type == "freetext":
                annot = page.add_freetext_annot(fitz.Rect(rect), text, fontsize=12)
            else:
                self.error_signal.emit(self._get_msg("err_operation_failed", f"unsupported annotation type: {annot_type}"))
                return

            if annot:
                annot.update()

            self._atomic_pdf_save(doc, output_path)
        finally:
            if doc:
                doc.close()
        self._emit_progress_if_due(100)
        self.finished_signal.emit(self._get_msg("msg_annotation_added", page_num + 1))

    def remove_annotations(self):
        """PDF에서 모든 주석 제거"""
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        count = 0
        doc = None
        try:
            doc = self._open_pdf_document(file_path)
            for page in doc:
                self._check_cancelled()
                annot = page.first_annot
                while annot:
                    next_annot = annot.next
                    page.delete_annot(annot)
                    count += 1
                    annot = next_annot

            self._atomic_pdf_save(doc, output_path)
        finally:
            if doc:
                doc.close()
        self._emit_progress_if_due(100)
        self.finished_signal.emit(self._get_msg("msg_annotations_removed", count))

    def image_watermark(self):
        """이미지 워터마크"""
        self._normalize_mode_kwargs()
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        image_path = _as_str(self.kwargs.get('image_path'))
        position = _as_str(self.kwargs.get('position'), 'center')
        # v4.5: 크기/투명도 파라미터 지원
        img_width = _as_int(self.kwargs.get('width'), 150)
        img_height = _as_int(self.kwargs.get('height'), 150)
        opacity = _as_float(self.kwargs.get('opacity'), 1.0)  # 0.0 ~ 1.0

        doc = self._open_pdf_document(file_path)
        try:
            total_pages = len(doc)
            for i in range(total_pages):
                page = doc[i]
                self._check_cancelled()  # 취소 체크포인트
                rect = page.rect
                if position == 'center':
                    x, y = (rect.width - img_width) / 2, (rect.height - img_height) / 2
                elif position == 'top':
                    x, y = (rect.width - img_width) / 2, 20
                elif position == 'bottom':
                    x, y = (rect.width - img_width) / 2, rect.height - img_height - 20
                elif position == 'top-left':
                    x, y = 20, 20
                elif position == 'top-right':
                    x, y = rect.width - img_width - 20, 20
                elif position == 'bottom-left':
                    x, y = 20, rect.height - img_height - 20
                else:  # bottom-right
                    x, y = rect.width - img_width - 20, rect.height - img_height - 20

                img_rect = fitz.Rect(x, y, x + img_width, y + img_height)
                # v4.5: opacity를 alpha로 변환 (0~255)
                alpha = int(opacity * 255) if 0 <= opacity <= 1 else 255
                page.insert_image(img_rect, filename=image_path, overlay=True, alpha=alpha)
                self._emit_progress_if_due(int((i + 1) / total_pages * 100))

            self._atomic_pdf_save(doc, output_path)
            opacity_pct = int(opacity * 100) if 0 <= opacity <= 1 else 100
            self.finished_signal.emit(self._get_msg("msg_image_watermark_done", img_width, img_height, opacity_pct))
        finally:
            doc.close()

    def add_stamp(self):
        """PDF 스탬프 추가"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        stamp_text = _as_str(self.kwargs.get('stamp_text'), '기밀')
        position = _as_str(self.kwargs.get('position'), 'top-right')
        color = self.kwargs.get('color', (1, 0, 0))  # 빨강

        doc = self._open_pdf_document(file_path)
        try:
            total_pages = len(doc)
            for i in range(total_pages):
                page = doc[i]
                self._check_cancelled()  # 취소 체크포인트
                rect = page.rect
                if position == 'top-right':
                    point = fitz.Point(rect.width - 100, 40)
                elif position == 'top-left':
                    point = fitz.Point(30, 40)
                elif position == 'bottom-right':
                    point = fitz.Point(rect.width - 100, rect.height - 30)
                else:
                    point = fitz.Point(30, rect.height - 30)

                # 스탬프 테두리 (좌표 기반 간단 구현)
                stamp_rect = fitz.Rect(point.x - 10, point.y - 20, point.x + 80, point.y + 5)
                page.draw_rect(stamp_rect, color=color, width=2)
                page.insert_text(point, stamp_text, fontsize=14, fontname="helv", color=color)
                self._emit_progress_if_due(int((i + 1) / total_pages * 100))

            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(self._get_msg("msg_stamp_done"))
        finally:
            doc.close()

    def insert_signature(self):
        """전자 서명 이미지 삽입"""
        from datetime import datetime
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        signature_path = _as_str(self.kwargs.get('signature_path'))
        page_num = self.kwargs.get('page_num', -1)  # -1 = 마지막 페이지
        position = _as_str(self.kwargs.get('position'), 'bottom_right')
        signer_name = _as_str(self.kwargs.get('signer_name'))  # v3.2: 서명자 이름
        add_timestamp = _as_bool(self.kwargs.get('add_timestamp'), False)  # v3.2: 타임스탬프

        doc = self._open_pdf_document(file_path)
        try:
            total_pages = len(doc)
            resolved_page_num = self._resolve_page_index(
                page_num,
                total_pages,
                allow_last_page_sentinel=True,
            )
            if resolved_page_num is None:
                return

            page = doc[resolved_page_num]
            page_rect = page.rect

            # 서명 이미지 크기 (가로 150pt)
            sig_width = 150
            sig_height = 50

            # v3.2: 타임스탬프/서명자 텍스트 높이 추가
            text_height = 0
            if signer_name or add_timestamp:
                text_height = 30

            # 위치 계산
            positions = {
                'bottom_right': fitz.Rect(page_rect.width - sig_width - 50, page_rect.height - sig_height - 50 - text_height,
                                          page_rect.width - 50, page_rect.height - 50 - text_height),
                'bottom_left': fitz.Rect(50, page_rect.height - sig_height - 50 - text_height,
                                         50 + sig_width, page_rect.height - 50 - text_height),
                'top_right': fitz.Rect(page_rect.width - sig_width - 50, 50,
                                       page_rect.width - 50, 50 + sig_height),
                'top_left': fitz.Rect(50, 50, 50 + sig_width, 50 + sig_height),
            }

            rect = positions.get(position, positions['bottom_right'])

            # 서명 이미지 삽입
            page.insert_image(rect, filename=signature_path)

            # v3.2: 서명자 이름 및 타임스탬프 추가
            if signer_name or add_timestamp:
                text_parts = []
                if signer_name:
                    text_parts.append(f"서명자: {signer_name}")
                if add_timestamp:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M")
                    text_parts.append(f"일시: {now}")

                text_str = " | ".join(text_parts)
                text_rect = fitz.Rect(rect.x0, rect.y1 + 5, rect.x1, rect.y1 + 25)
                page.insert_textbox(text_rect, text_str, fontsize=8, fontname="helv",
                                   color=(0.3, 0.3, 0.3), align=1)

            # v3.2: 메타데이터에 서명 정보 기록
            if signer_name:
                meta = cast(dict[str, Any], doc.metadata or {})
                existing_keywords = meta.get('keywords', '') or ''
                new_keywords = f"{existing_keywords}; Signed by: {signer_name}" if existing_keywords else f"Signed by: {signer_name}"
                meta['keywords'] = new_keywords
                doc.set_metadata(meta)

            self._emit_progress_if_due(100)

            self._atomic_pdf_save(doc, output_path)
            extra_info = ""
            if signer_name:
                extra_info += self._get_msg("msg_signature_signer_suffix", signer_name)
            if add_timestamp:
                extra_info += self._get_msg("msg_signature_timestamp_suffix")
            self.finished_signal.emit(
                self._get_msg("msg_signature_inserted", extra_info, resolved_page_num + 1)
            )
        finally:
            doc.close()

    def highlight_text(self):
        """PDF 내 텍스트 하이라이트"""
        file_path = _as_str(self.kwargs.get('file_path'))
        search_term = _as_str(self.kwargs.get('search_term'))
        output_path = _as_str(self.kwargs.get('output_path'))
        color = self.kwargs.get('color', (1, 1, 0))  # 기본 노란색

        doc = self._open_pdf_document(file_path)
        highlight_count = 0
        try:
            total_pages = len(doc)
            for page_num in range(len(doc)):
                page = doc[page_num]
                self._check_cancelled()  # 취소 체크포인트
                text_instances = page.search_for(search_term)
                for inst in text_instances:
                    highlight = page.add_highlight_annot(inst)
                    highlight.set_colors(stroke=color)
                    highlight.update()
                    highlight_count += 1
                self._emit_progress_if_due(int((page_num + 1) / total_pages * 100))

            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(self._get_msg("msg_highlight_done", search_term, highlight_count))
        finally:
            doc.close()

    def draw_shapes(self):
        """PDF에 도형 그리기"""
        self._normalize_mode_kwargs()
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_num = _as_int(self.kwargs.get('page_num'), 0)
        shapes = cast(list[dict[str, Any]], self.kwargs.get('shapes') or [])  # [{type, params, color, width}]

        doc = self._open_pdf_document(file_path)
        try:
            if not shapes:
                self.error_signal.emit(self._get_msg("err_shapes_required"))
                return
            # v4.5: 페이지 번호 유효성 검사
            if page_num < 0 or page_num >= len(doc):
                self.error_signal.emit(self._get_msg("err_page_out_of_range", str(page_num + 1), str(len(doc))))
                return

            page = doc[page_num]

            for shape_info in shapes:
                shape_type = shape_info.get('type', 'line')
                color = tuple(shape_info.get('color', [1, 0, 0]))
                # v4.5: 색상 값 범위 제한
                color = tuple(max(0.0, min(1.0, c)) for c in color)
                width = shape_info.get('width', 1)
                fill = shape_info.get('fill')
                if fill:
                    fill = tuple(max(0.0, min(1.0, c)) for c in fill)

                if shape_type == 'line':
                    p1 = fitz.Point(shape_info['p1'][0], shape_info['p1'][1])
                    p2 = fitz.Point(shape_info['p2'][0], shape_info['p2'][1])
                    page.draw_line(p1, p2, color=color, width=width)
                elif shape_type == 'rect':
                    rect = fitz.Rect(shape_info['rect'])
                    page.draw_rect(rect, color=color, width=width, fill=fill)
                elif shape_type == 'circle':
                    center = fitz.Point(shape_info['center'][0], shape_info['center'][1])
                    radius = shape_info.get('radius', 50)
                    page.draw_circle(center, radius, color=color, width=width, fill=fill)
                elif shape_type == 'oval':
                    rect = fitz.Rect(shape_info['rect'])
                    page.draw_oval(rect, color=color, width=width, fill=fill)

            self._atomic_pdf_save(doc, output_path)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(self._get_msg("msg_shapes_added", len(shapes)))
        finally:
            doc.close()

    def add_link(self):
        """PDF에 하이퍼링크 추가"""
        self._normalize_mode_kwargs()
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_num = _as_int(self.kwargs.get('page_num'), 0)
        link_type = _as_str(self.kwargs.get('link_type'), 'uri')  # uri, goto
        rect = cast(list[float], self.kwargs.get('rect') or [100, 100, 200, 120])  # [x0, y0, x1, y1]
        target = self.kwargs.get('target')  # URL 또는 페이지 번호

        # v4.5: link_type 유효성 검사
        valid_link_types = ['uri', 'goto']
        if link_type not in valid_link_types:
            logger.warning(f"Invalid link_type '{link_type}', defaulting to 'uri'")
            link_type = 'uri'

        # v4.5: target 유효성 검사
        if target is None or (isinstance(target, str) and not target.strip()):
            self.error_signal.emit(self._get_msg("err_link_target_required"))
            return

        doc = self._open_pdf_document(file_path)
        try:
            if page_num < 0 or page_num >= len(doc):
                self.error_signal.emit(self._get_msg("err_page_out_of_range", str(page_num + 1), str(len(doc))))
                return

            page = doc[page_num]

            link = {
                'kind': fitz.LINK_URI if link_type == 'uri' else fitz.LINK_GOTO,
                'from': fitz.Rect(rect),
            }

            if link_type == 'uri':
                target_str = str(target).strip()
                # v4.5: URL 형식 기본 검증
                if not (
                    target_str.startswith('http://') or
                    target_str.startswith('https://') or
                    target_str.startswith('mailto:')
                ):
                    logger.warning(f"URL might be invalid: {target_str}")
                link['uri'] = target_str
            else:
                try:
                    raw_target = int(target)
                    # v4.5.3: goto 대상은 0-based 인덱스만 허용 (UI에서 사전 정규화)
                    target_page = raw_target
                    if target_page < 0 or target_page >= len(doc):
                        self.error_signal.emit(
                            self._get_msg("err_link_target_zero_based", str(target), str(max(0, len(doc) - 1)))
                        )
                        return
                    link['page'] = target_page
                    link['to'] = fitz.Point(0, 0)
                except ValueError:
                    self.error_signal.emit(self._get_msg("err_page_number_numeric", str(target)))
                    return

            page.insert_link(link)
            self._atomic_pdf_save(doc, output_path)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(self._get_msg("msg_link_added", page_num + 1))
        finally:
            doc.close()

    def redact_text(self):
        """PDF에서 텍스트 영구 삭제 (교정)"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        search_term = _as_str(self.kwargs.get('search_term'))
        fill_color = self.kwargs.get('fill_color', (0, 0, 0))  # 검정색 기본
        images = _as_int(self.kwargs.get("images"), 2)  # apply_redactions images flag

        if not search_term:
            self.error_signal.emit(self._get_msg("err_redact_text_required"))
            return

        doc = self._open_pdf_document(file_path)
        try:
            redact_count = 0
            total_pages = len(doc)

            for page_num in range(len(doc)):
                page = doc[page_num]
                self._check_cancelled()  # 취소 체크포인트
                text_instances = page.search_for(search_term)
                for inst in text_instances:
                    page.add_redact_annot(inst, fill=fill_color)
                    redact_count += 1
                try:
                    page.apply_redactions(images=images)
                except TypeError:
                    page.apply_redactions()
                self._emit_progress_if_due(int((page_num + 1) / total_pages * 100))

            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(self._get_msg("msg_redact_done", redact_count))
        finally:
            doc.close()

    def redact_area(self):
        """좌표 영역 기반 영구 교정.

        rects: [{page: 1-based, rect: [x0,y0,x1,y1]}, ...] 또는
               page + rect 단일 지정.
        """
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        fill_color = self.kwargs.get("fill_color", (0, 0, 0))
        images = _as_int(self.kwargs.get("images"), 2)
        raw_rects = _as_list(self.kwargs.get("rects"))

        # 단일 page/rect 단축 인자
        if not raw_rects:
            page_one = self.kwargs.get("page")
            rect = self.kwargs.get("rect")
            if page_one is not None and rect is not None:
                raw_rects = [{"page": page_one, "rect": rect}]

        if not raw_rects:
            self.error_signal.emit(self._get_msg("err_redact_area_required"))
            return

        doc = self._open_pdf_document(file_path)
        try:
            page_count = len(doc)
            by_page: dict[int, list[Any]] = {}
            for item in raw_rects:
                if isinstance(item, dict):
                    page_num = _as_int(item.get("page"), 0)
                    rect_vals = item.get("rect")
                elif isinstance(item, (list, tuple)) and len(item) >= 5:
                    page_num = int(item[0])
                    rect_vals = item[1:5]
                else:
                    continue
                if page_num < 1 or page_num > page_count:
                    continue
                try:
                    coords = [float(v) for v in rect_vals]  # type: ignore[arg-type]
                    if len(coords) < 4:
                        continue
                    rect = fitz.Rect(coords[0], coords[1], coords[2], coords[3])
                except Exception:
                    continue
                if rect.is_empty or rect.width < 1 or rect.height < 1:
                    continue
                by_page.setdefault(page_num - 1, []).append(rect)

            if not by_page:
                self.error_signal.emit(self._get_msg("err_redact_area_invalid"))
                return

            redact_count = 0
            pages = sorted(by_page.keys())
            for idx, page_index in enumerate(pages):
                self._check_cancelled()
                page = doc[page_index]
                for rect in by_page[page_index]:
                    page.add_redact_annot(rect, fill=fill_color)
                    redact_count += 1
                try:
                    page.apply_redactions(images=images)
                except TypeError:
                    page.apply_redactions()
                self._emit_progress_if_due(int((idx + 1) / max(1, len(pages)) * 100))

            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(self._get_msg("msg_redact_done", redact_count))
        finally:
            doc.close()

    def add_background(self):
        """PDF 페이지에 배경색 추가"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        color = self.kwargs.get('color', [1, 1, 0.9])  # 연한 노란색 기본

        # v4.5: 색상 값 범위 검증 (0.0-1.0)
        if isinstance(color, (list, tuple)):
            color = tuple(max(0.0, min(1.0, c)) for c in color)
        else:
            logger.warning(f"Invalid color format, using default")
            color = (1, 1, 0.9)

        doc = self._open_pdf_document(file_path)
        try:
            total_pages = len(doc)
            for page_num in range(len(doc)):
                page = doc[page_num]
                self._check_cancelled()  # 취소 체크포인트
                rect = page.rect
                shape = page.new_shape()
                shape.draw_rect(rect)
                shape.finish(color=color, fill=color)
                shape.commit(overlay=False)  # 배경으로 삽입
                self._emit_progress_if_due(int((page_num + 1) / total_pages * 100))

            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(self._get_msg("msg_background_added", len(doc)))
        finally:
            doc.close()

    def add_text_markup(self):
        """검색어에 밑줄 또는 취소선 추가"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        search_term = _as_str(self.kwargs.get('search_term'))
        markup_type = _as_str(self.kwargs.get('markup_type'), 'underline')  # underline, strikeout, squiggly
        valid_markup_types = {'underline', 'strikeout', 'squiggly'}

        if markup_type not in valid_markup_types:
            self.error_signal.emit(self._get_msg("err_invalid_markup_type", str(markup_type)))
            return

        doc = self._open_pdf_document(file_path)
        count = 0
        try:
            total_pages = len(doc)
            for page_num in range(len(doc)):
                page = doc[page_num]
                self._check_cancelled()  # 취소 체크포인트
                instances = page.search_for(search_term)
                for inst in instances:
                    annot = None
                    if markup_type == 'underline':
                        annot = page.add_underline_annot(inst)
                    elif markup_type == 'strikeout':
                        annot = page.add_strikeout_annot(inst)
                    elif markup_type == 'squiggly':
                        annot = page.add_squiggly_annot(inst)
                    if annot:
                        annot.update()
                    count += 1
                self._emit_progress_if_due(int((page_num + 1) / total_pages * 100))

            self._atomic_pdf_save(doc, output_path)
            markup_name = self._get_msg(f"msg_markup_label_{markup_type}")
            if markup_name == f"msg_markup_label_{markup_type}":
                markup_name = markup_type
            self.finished_signal.emit(self._get_msg("msg_text_markup_added", markup_name, search_term, count))
        finally:
            doc.close()

    def insert_textbox(self):
        """PDF에 텍스트 상자 삽입"""
        self._normalize_mode_kwargs()
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_num = _as_int(self.kwargs.get('page_num'), 0)
        rect = cast(list[float], self.kwargs.get('rect') or [100, 100, 300, 150])  # [x0, y0, x1, y1]
        text = _as_str(self.kwargs.get('text'))
        fontsize = _as_int(self.kwargs.get('fontsize'), 12)
        color = tuple(self.kwargs.get('color', [0, 0, 0]))
        align = _as_int(self.kwargs.get('align'), 0)  # 0=left, 1=center, 2=right

        doc = self._open_pdf_document(file_path)
        try:
            # 유효성 검사 추가
            if page_num < 0 or page_num >= len(doc):
                self.error_signal.emit(self._get_msg("err_page_out_of_range", str(page_num + 1), str(len(doc))))
                return

            page = doc[page_num]

            page.insert_textbox(fitz.Rect(rect), text, fontsize=fontsize,
                               fontname="helv", color=color, align=align)

            self._atomic_pdf_save(doc, output_path)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(self._get_msg("msg_textbox_inserted", page_num + 1))
        finally:
            doc.close()

    def add_sticky_note(self):
        """PDF에 스티키 노트(텍스트 주석) 추가"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_num = _as_int(self.kwargs.get('page_num'), 0)
        x = _as_int(self.kwargs.get('x'), 100)  # 노트 위치 X
        y = _as_int(self.kwargs.get('y'), 100)  # 노트 위치 Y
        content = _as_str(self.kwargs.get('content'))  # 노트 내용
        title = _as_str(self.kwargs.get('title'), '메모')  # 노트 제목
        icon = _as_str(self.kwargs.get('icon'), 'Note')  # Note, Comment, Key, Help, Insert, Paragraph

        doc = self._open_pdf_document(file_path)
        try:
            resolved_page_num = self._resolve_page_index(page_num, len(doc))
            if resolved_page_num is None:
                return

            page = doc[resolved_page_num]
            point = fitz.Point(x, y)

            # 스티키 노트 주석 추가
            annot = page.add_text_annot(point, content, icon=icon)
            if annot:
                annot.set_info(title=title, content=content)
                annot.update()

            self._emit_progress_if_due(100)
            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(self._get_msg("msg_sticky_note_added", resolved_page_num + 1, icon))
        finally:
            doc.close()

    def add_ink_annotation(self):
        """PDF에 프리핸드 드로잉(잉크 주석) 추가"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_num = _as_int(self.kwargs.get('page_num'), 0)
        points = cast(list[list[float]], self.kwargs.get('points') or [])  # [[x1,y1], [x2,y2], ...] 좌표 목록
        color = self.kwargs.get('color', (0, 0, 1))  # 기본 파란색
        width = _as_int(self.kwargs.get('width'), 2)  # 선 두께

        doc = self._open_pdf_document(file_path)
        try:
            resolved_page_num = self._resolve_page_index(page_num, len(doc))
            if resolved_page_num is None:
                return

            page = doc[resolved_page_num]

            if not points:
                self.error_signal.emit(self._get_msg("err_ink_points_required"))
                return

            try:
                normalized_points = _normalize_stroke_points(points)
            except (TypeError, ValueError):
                self.error_signal.emit(self._get_msg("msg_invalid_stroke_format"))
                return

            try:
                annot = page.add_ink_annot([normalized_points])
            except (TypeError, ValueError):
                self.error_signal.emit(self._get_msg("msg_invalid_stroke_format"))
                return

            if annot:
                annot.set_colors(stroke=color)
                annot.set_border(width=width)
                annot.update()

            self._emit_progress_if_due(100)
            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(
                self._get_msg("msg_ink_annotation_added", resolved_page_num + 1, len(normalized_points))
            )
        finally:
            doc.close()

    def add_freehand_signature(self):
        """PDF에 프리핸드 서명 (여러 획) 추가"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        page_num = self.kwargs.get('page_num', -1)  # -1 = 마지막 페이지
        strokes = cast(list[list[list[float]]], self.kwargs.get('strokes') or [])  # [[[x1,y1], [x2,y2]], [[x3,y3], [x4,y4]]] 다중 획
        color = self.kwargs.get('color', (0, 0, 0))  # 기본 검정
        width = _as_int(self.kwargs.get('width'), 2)

        doc = self._open_pdf_document(file_path)
        try:
            total_pages = len(doc)
            resolved_page_num = self._resolve_page_index(
                page_num,
                total_pages,
                allow_last_page_sentinel=True,
            )
            if resolved_page_num is None:
                return

            page = doc[resolved_page_num]

            if not strokes:
                self.error_signal.emit(self._get_msg("msg_stroke_required"))
                return

            all_strokes: list[list[list[float]]] = []
            for stroke in strokes:
                self._check_cancelled()
                try:
                    all_strokes.append(_normalize_stroke_points(stroke))
                except (TypeError, ValueError):
                    self.error_signal.emit(self._get_msg("msg_invalid_stroke_format"))
                    return

            if not all_strokes:
                self.error_signal.emit(self._get_msg("err_no_valid_strokes"))
                return

            try:
                self._check_cancelled()
                annot = page.add_ink_annot(all_strokes)
            except (TypeError, ValueError):
                self.error_signal.emit(self._get_msg("msg_invalid_stroke_format"))
                return
            if annot:
                annot.set_colors(stroke=color)
                annot.set_border(width=width)
                annot.update()

            self._check_cancelled()
            self._emit_progress_if_due(100)
            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(
                self._get_msg("msg_freehand_signature_added", resolved_page_num + 1, len(all_strokes))
            )
        finally:
            doc.close()
