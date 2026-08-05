"""PDF helpers facade (호환 경로)."""
from __future__ import annotations

from ._pdf_helpers_impl import (
    text_needs_cjk,
    _normalize_stroke_points,
    _fallback_markdown_from_text,
    _extract_native_markdown,
    _extract_page_markdown,
    _page_asset_placeholders,
    _markdown_front_matter,
    _sample_diff_text,
    _pixmap_for_reencode,
    _image_display_size_pt,
    _target_scale,
    optimize_pdf_images,
    subset_document_fonts,
)

__all__ = ['text_needs_cjk', '_normalize_stroke_points', '_fallback_markdown_from_text', '_extract_native_markdown', '_extract_page_markdown', '_page_asset_placeholders', '_markdown_front_matter', '_sample_diff_text', '_pixmap_for_reencode', '_image_display_size_pt', '_target_scale', 'optimize_pdf_images', 'subset_document_fonts']
