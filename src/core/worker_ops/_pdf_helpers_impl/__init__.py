"""_pdf_helpers 구현 패키지."""
from __future__ import annotations

from .text_cjk import (
    text_needs_cjk,
)

from .strokes import (
    _normalize_stroke_points,
)

from .markdown import (
    _fallback_markdown_from_text,
    _extract_native_markdown,
    _extract_page_markdown,
    _page_asset_placeholders,
    _markdown_front_matter,
)

from .diff_sample import (
    _sample_diff_text,
)

from .image_optimize import (
    _pixmap_for_reencode,
    _image_display_size_pt,
    _target_scale,
    optimize_pdf_images,
    subset_document_fonts,
)

__all__ = ['text_needs_cjk', '_normalize_stroke_points', '_fallback_markdown_from_text', '_extract_native_markdown', '_extract_page_markdown', '_page_asset_placeholders', '_markdown_front_matter', '_sample_diff_text', '_pixmap_for_reencode', '_image_display_size_pt', '_target_scale', 'optimize_pdf_images', 'subset_document_fonts']
