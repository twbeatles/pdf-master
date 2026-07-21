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


class WorkerAnnotationWatermarkMixin(WorkerHost):
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
