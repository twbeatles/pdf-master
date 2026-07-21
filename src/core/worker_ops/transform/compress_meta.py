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


class WorkerTransformCompressMetaMixin(WorkerHost):
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
            save_profile = normalize_save_profile(
                raw_save_profile,
                default=quality_to_save_profile(quality),
            )
            extra_save_kwargs = {}
            if not raw_save_profile:
                extra_save_kwargs = dict(COMPRESSION_SETTINGS.get(quality, COMPRESSION_SETTINGS["high"]))

            optimize_opts = resolve_image_optimize_options(
                save_profile,
                optimize_images=self.kwargs.get("optimize_images"),
                subset_fonts=self.kwargs.get("subset_fonts"),
                max_image_dpi=self.kwargs.get("max_image_dpi"),
                jpeg_quality=self.kwargs.get("jpeg_quality"),
                grayscale_images=self.kwargs.get("grayscale_images"),
            )

            images_replaced = 0
            if optimize_opts.get("optimize_images"):
                def _image_progress(done: int, total: int) -> None:
                    # 이미지 단계: 0~70%
                    ratio = done / max(1, total)
                    self._emit_progress_if_due(int(ratio * 70))

                images_replaced = optimize_pdf_images(
                    doc,
                    max_dpi=float(optimize_opts.get("max_dpi") or 150.0),
                    jpeg_quality=int(optimize_opts.get("jpeg_quality") or 75),
                    grayscale=bool(optimize_opts.get("grayscale")),
                    check_cancelled=self._check_cancelled,
                    progress_cb=_image_progress,
                )
            else:
                self._check_cancelled()
                self._emit_progress_if_due(40)

            fonts_subset = False
            if optimize_opts.get("subset_fonts"):
                self._check_cancelled()
                fonts_subset = subset_document_fonts(doc)
            self._emit_progress_if_due(80)

            # 완료 메시지/디버그에 쓸 수 있도록 기록
            self.kwargs["compress_images_replaced"] = images_replaced
            self.kwargs["compress_fonts_subset"] = fonts_subset

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
