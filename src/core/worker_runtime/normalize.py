from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from ..optional_deps import fitz

logger = logging.getLogger(__name__)


def _normalize_draw_shapes(kwargs: dict[str, Any]) -> None:
    shapes = kwargs.get("shapes")
    if not shapes and any(k in kwargs for k in ("shape_type", "x", "y", "width", "height")):
        shape_type = kwargs.get("shape_type", "rect")
        x = float(kwargs.get("x", 100))
        y = float(kwargs.get("y", 100))
        w = float(kwargs.get("width", 120))
        h = float(kwargs.get("height", 80))
        stroke_width = float(kwargs.get("line_width", 1))
        line_color = kwargs.get("line_color", kwargs.get("color", (1, 0, 0)))
        fill_color = kwargs.get("fill_color", kwargs.get("fill"))
        shape = {"type": shape_type, "color": line_color, "width": stroke_width}
        if fill_color is not None:
            shape["fill"] = fill_color
        if shape_type == "line":
            shape["p1"] = [x, y]
            shape["p2"] = [x + w, y + h]
        elif shape_type == "circle":
            shape["center"] = [x + (w / 2.0), y + (h / 2.0)]
            shape["radius"] = max(1.0, min(abs(w), abs(h)) / 2.0)
        elif shape_type == "oval":
            shape["rect"] = [x, y, x + w, y + h]
        else:
            shape["type"] = "rect"
            shape["rect"] = [x, y, x + w, y + h]
        kwargs["shapes"] = [shape]


def _normalize_add_link(kwargs: dict[str, Any]) -> None:
    link_type = kwargs.get("link_type", "uri")
    if link_type == "url":
        kwargs["link_type"] = "uri"
    elif link_type == "page":
        kwargs["link_type"] = "goto"


def _normalize_insert_textbox(kwargs: dict[str, Any]) -> None:
    if "rect" not in kwargs:
        x = float(kwargs.get("x", 100))
        y = float(kwargs.get("y", 100))
        w = float(kwargs.get("width", 200))
        h = float(kwargs.get("height", 50))
        kwargs["rect"] = [x, y, x + w, y + h]


def _normalize_copy_page_between_docs(kwargs: dict[str, Any], parse_page_range: Callable[[str, int], list[int]]) -> None:
    if not kwargs.get("target_path"):
        kwargs["target_path"] = kwargs.get("file_path")
    source_pages = kwargs.get("source_pages")
    if source_pages is None:
        page_range = kwargs.get("page_range", "")
        if isinstance(page_range, str) and page_range.strip():
            kwargs["source_pages"] = parse_page_range(page_range, 10**9)
        else:
            kwargs["source_pages"] = None
    elif isinstance(source_pages, int):
        kwargs["source_pages"] = [source_pages]


def _normalize_image_watermark(kwargs: dict[str, Any]) -> None:
    alias_map = {
        "top-center": "top",
        "bottom-center": "bottom",
    }
    pos = kwargs.get("position")
    if isinstance(pos, str):
        kwargs["position"] = alias_map.get(pos, pos)

    if "scale" in kwargs and kwargs.get("image_path"):
        try:
            scale = float(kwargs.get("scale", 1.0))
        except (TypeError, ValueError):
            scale = 1.0
        scale = max(0.01, scale)
        try:
            pix = fitz.Pixmap(kwargs["image_path"])
            base_w, base_h = pix.width, pix.height
            del pix
            kwargs["width"] = max(1, int(base_w * scale))
            kwargs["height"] = max(1, int(base_h * scale))
        except Exception:
            logger.debug("Failed to compute watermark image size from scale", exc_info=True)


NORMALIZERS = {
    "draw_shapes": lambda kwargs, parse_page_range: _normalize_draw_shapes(kwargs),
    "add_link": lambda kwargs, parse_page_range: _normalize_add_link(kwargs),
    "insert_textbox": lambda kwargs, parse_page_range: _normalize_insert_textbox(kwargs),
    "copy_page_between_docs": _normalize_copy_page_between_docs,
    "image_watermark": lambda kwargs, parse_page_range: _normalize_image_watermark(kwargs),
}


def normalize_mode_kwargs(
    mode: str,
    kwargs: dict[str, Any],
    parse_page_range: Callable[[str, int], list[int]],
) -> None:
    normalizer = NORMALIZERS.get(mode)
    if normalizer is None:
        return
    normalizer(kwargs, parse_page_range)
