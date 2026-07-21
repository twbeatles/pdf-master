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


class WorkerTransformConvertMixin(WorkerHost):
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

    def convert_to_svg(self):
        """페이지별 SVG 내보내기."""
        file_paths = [
            path
            for path in (_as_list(self.kwargs.get("file_paths")) or [_as_str(self.kwargs.get("file_path"))])
            if isinstance(path, str) and path
        ]
        output_dir = _as_str(self.kwargs.get("output_dir"))
        if not output_dir:
            self.error_signal.emit(self._get_msg("err_output_path_missing"))
            return

        os.makedirs(output_dir, exist_ok=True)
        total_files = len(file_paths)
        used_stems: set[str] = set()
        page_total_written = 0

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
                    "_p001.svg",
                    used_stems,
                )
                for i in range(len(doc)):
                    self._check_cancelled()
                    page = doc[i]
                    svg = page.get_svg_image()
                    out_path = os.path.join(output_dir, f"{unique_stem}_p{i + 1:03d}.svg")
                    self._atomic_text_save(out_path, svg if isinstance(svg, str) else str(svg))
                    page_total_written += 1
            finally:
                if doc:
                    doc.close()
            self._emit_progress_if_due(int((file_idx + 1) / max(1, total_files) * 100))

        self.finished_signal.emit(self._get_msg("msg_convert_to_svg_done", page_total_written))
