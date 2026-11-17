"""PDF helpers facade (호환 경로)."""

from __future__ import annotations

from ._pdf_helpers_impl import (
    _extract_native_markdown,
    _extract_page_markdown,
    _fallback_markdown_from_text,
    _image_display_size_pt,
    _markdown_front_matter,
    _normalize_stroke_points,
    _page_asset_placeholders,
    _pixmap_for_reencode,
    _sample_diff_text,
    _target_scale,
    optimize_pdf_images,
    subset_document_fonts,
    text_needs_cjk,
)

__all__ = [
    "text_needs_cjk",
    "_normalize_stroke_points",
    "_fallback_markdown_from_text",
    "_extract_native_markdown",
    "_extract_page_markdown",
    "_page_asset_placeholders",
    "_markdown_front_matter",
    "_sample_diff_text",
    "_pixmap_for_reencode",
    "_image_display_size_pt",
    "_target_scale",
    "optimize_pdf_images",
    "subset_document_fonts",
]
