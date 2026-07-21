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
    COMPRESSION_SETTINGS,
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
    optimize_pdf_images,
    subset_document_fonts,
)
from ..cleanup_ops import _content_bbox
from ...pdf_validation import validate_pdf_file
from ...worker_runtime.save_profiles import (
    normalize_save_profile,
    quality_to_save_profile,
    resolve_image_optimize_options,
)
logger = logging.getLogger(__name__)


class WorkerTransformGeometryMixin(WorkerHost):
    def crop_pdf(self):
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        margins = _as_dict(self.kwargs.get("margins") or {"left": 0, "top": 0, "right": 0, "bottom": 0})
        crop_mode = _as_str(self.kwargs.get("crop_mode"), "margins")  # margins | content
        pad = _as_float(self.kwargs.get("content_pad"), 2.0)

        doc = self._open_pdf_document(file_path)
        try:
            total_pages = len(doc)
            for i in range(total_pages):
                page = doc[i]
                self._check_cancelled()
                rect = page.rect
                if crop_mode == "content":
                    bbox = _content_bbox(page, pad=float(pad or 0.0))
                    if bbox is None or bbox.is_empty or bbox.width < 5 or bbox.height < 5:
                        new_rect = rect
                    else:
                        new_rect = bbox
                else:
                    new_rect = fitz.Rect(
                        rect.x0 + float(margins.get("left") or 0),
                        rect.y0 + float(margins.get("top") or 0),
                        rect.x1 - float(margins.get("right") or 0),
                        rect.y1 - float(margins.get("bottom") or 0),
                    )
                if new_rect.width > 1 and new_rect.height > 1:
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
