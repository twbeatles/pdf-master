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
    COMPRESSION_SETTINGS,
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

from ..pdf_validation import validate_pdf_file
from ..worker_runtime.save_profiles import normalize_save_profile, quality_to_save_profile


class WorkerTransformOpsMixin(WorkerHost):
    def convert_to_img(self):
        # 다중 파일 지원
        file_paths = [path for path in (_as_list(self.kwargs.get('file_paths')) or [_as_str(self.kwargs.get('file_path'))]) if isinstance(path, str) and path]
        output_dir = _as_str(self.kwargs.get('output_dir'))
        fmt = _as_str(self.kwargs.get('fmt'), 'png')
        dpi = _as_int(self.kwargs.get('dpi'), 200)
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)

        total_files = len(file_paths)
        used_output_stems: set[str] = set()
        os.makedirs(output_dir, exist_ok=True)

        for file_idx, file_path in enumerate(file_paths):
            if not file_path or not os.path.exists(file_path):
                continue
            doc = None
            try:
                doc = self._open_pdf_document(file_path)
                base = os.path.splitext(os.path.basename(file_path))[0]
                unique_stem = self._build_unique_output_stem(
                    output_dir,
                    base,
                    f"_p001.{fmt}",
                    used_output_stems,
                )
                for i in range(len(doc)):
                    page = doc[i]
                    self._check_cancelled()  # 취소 체크포인트
                    pix = page.get_pixmap(matrix=mat)
                    save_path = os.path.join(output_dir, f"{unique_stem}_p{i+1:03d}.{fmt}")
                    self._atomic_pixmap_save(pix, save_path)
            finally:
                if doc:
                    doc.close()
            self._emit_progress_if_due(int((file_idx + 1) / max(1, total_files) * 100))

        self.finished_signal.emit(
            self._get_msg("msg_convert_to_img_done", total_files, fmt.upper())
        )

    def metadata_update(self):
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        new_meta = _as_dict(self.kwargs.get("metadata"))

        doc = self._open_pdf_document(file_path)
        try:
            meta = cast(dict[str, Any], doc.metadata or {})
            for key, value in new_meta.items():
                if value:
                    meta[key] = value
            doc.set_metadata(meta)
            self._atomic_pdf_save(doc, output_path)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(self._get_msg("msg_metadata_saved"))
        finally:
            doc.close()

    def compress(self):
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        quality = _as_str(self.kwargs.get("quality"), "high")
        raw_save_profile = _as_str(self.kwargs.get("save_profile"))

        if not file_path or not os.path.exists(file_path):
            self.error_signal.emit(self._get_msg("err_input_file_missing"))
            return
        if not output_path:
            self.error_signal.emit(self._get_msg("err_output_path_missing"))
            return

        original_size = os.path.getsize(file_path)
        doc = self._open_pdf_document(file_path)
        try:
            total_pages = len(doc)
            save_profile = normalize_save_profile(
                raw_save_profile,
                default=quality_to_save_profile(quality),
            )
            extra_save_kwargs = {}
            if not raw_save_profile:
                extra_save_kwargs = dict(COMPRESSION_SETTINGS.get(quality, COMPRESSION_SETTINGS["high"]))

            for page_num in range(total_pages):
                self._check_cancelled()
                self._emit_progress_if_due(int((page_num + 1) / total_pages * 20))

            self._emit_progress_if_due(25)
            self._atomic_pdf_save(
                doc,
                output_path,
                save_profile=save_profile,
                **extra_save_kwargs,
            )
            self._emit_progress_if_due(95)
        finally:
            doc.close()

        new_size = os.path.getsize(output_path)
        ratio = (1 - new_size / original_size) * 100 if original_size > 0 else 0
        self._emit_progress_if_due(100)
        self.finished_signal.emit(
            self._get_msg("msg_compression_done", save_profile, original_size // 1024, new_size // 1024, ratio)
        )

    def crop_pdf(self):
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        margins = _as_dict(self.kwargs.get("margins") or {"left": 0, "top": 0, "right": 0, "bottom": 0})

        doc = self._open_pdf_document(file_path)
        try:
            total_pages = len(doc)
            for i in range(total_pages):
                page = doc[i]
                self._check_cancelled()
                rect = page.rect
                new_rect = fitz.Rect(
                    rect.x0 + margins["left"],
                    rect.y0 + margins["top"],
                    rect.x1 - margins["right"],
                    rect.y1 - margins["bottom"],
                )
                page.set_cropbox(new_rect)
                self._emit_progress_if_due(int((i + 1) / total_pages * 100))

            self._atomic_pdf_save(doc, output_path)
            self.finished_signal.emit(self._get_msg("msg_crop_done"))
        finally:
            doc.close()

    def resize_pages(self):
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        target_size = _as_str(self.kwargs.get("target_size"), "A4")

        target_w, target_h = PAGE_SIZES.get(target_size, DEFAULT_PAGE_SIZE)
        doc = self._open_pdf_document(file_path)
        resized_doc = fitz.open()
        try:
            metadata = cast(dict[str, Any], doc.metadata or {})
            if metadata:
                resized_doc.set_metadata(metadata)
            total_pages = len(doc)
            for i in range(total_pages):
                page = doc[i]
                self._check_cancelled()
                src_rect = page.rect
                scale = min(target_w / max(src_rect.width, 1), target_h / max(src_rect.height, 1))
                render_w = src_rect.width * scale
                render_h = src_rect.height * scale
                offset_x = (target_w - render_w) / 2
                offset_y = (target_h - render_h) / 2

                new_page = resized_doc.new_page(width=target_w, height=target_h)
                target_rect = fitz.Rect(
                    offset_x,
                    offset_y,
                    offset_x + render_w,
                    offset_y + render_h,
                )
                new_page.show_pdf_page(target_rect, doc, i)
                self._emit_progress_if_due(int((i + 1) / total_pages * 100))

            self._atomic_pdf_save(resized_doc, output_path)
            self.finished_signal.emit(
                self._get_msg("msg_resize_pages_done", len(doc), target_size)
            )
        finally:
            resized_doc.close()
            doc.close()
