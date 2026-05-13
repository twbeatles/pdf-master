from __future__ import annotations

import json
import os
from typing import Any, cast

from ..optional_deps import fitz
from ..worker_runtime.args import _as_str


def _sample_diff_text(lines: list[str], max_items: int = 2) -> str:
    visible = [line.strip() for line in lines if isinstance(line, str) and line.strip()]
    return " | ".join(visible[:max_items]) if visible else "∅"

def _normalize_stroke_points(raw_points: Any) -> list[list[float]]:
    if not isinstance(raw_points, (list, tuple)):
        raise ValueError("points must be a sequence")

    normalized_points: list[list[float]] = []
    for raw_point in raw_points:
        if not isinstance(raw_point, (list, tuple)) or len(raw_point) < 2:
            raise ValueError("invalid stroke point")
        normalized_points.append([float(raw_point[0]), float(raw_point[1])])

    if len(normalized_points) < 2:
        raise ValueError("stroke requires at least two points")

    return normalized_points

def _fallback_markdown_from_text(page: Any) -> str:
    text = _as_str(page.get_text("text"))
    page_chunks: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped:
            page_chunks.append(stripped)
    return "\n\n".join(page_chunks).strip()

def _extract_native_markdown(page: Any) -> str:
    for option in ("markdown", "md"):
        try:
            extracted = page.get_text(option)
        except Exception:
            extracted = ""
        if isinstance(extracted, str) and extracted.strip():
            return extracted.strip()
    return ""

def _extract_page_markdown(page: Any, markdown_mode: str) -> str:
    if markdown_mode in {"auto", "native"}:
        native_markdown = _extract_native_markdown(page)
        if native_markdown:
            return native_markdown
        if markdown_mode == "native":
            raise RuntimeError("Native Markdown extraction is not available for this document/runtime.")
    return _fallback_markdown_from_text(page)

def _page_asset_placeholders(page: Any) -> list[str]:
    placeholders: list[str] = []
    try:
        image_count = len(page.get_images(full=True))
    except Exception:
        image_count = 0
    if image_count > 0:
        placeholders.append(f"_[Images detected: {image_count}]_")

    try:
        find_tables = getattr(page, "find_tables", None)
        tables = find_tables() if callable(find_tables) else None
        table_list = getattr(tables, "tables", tables)
        if table_list is not None and hasattr(table_list, "__len__"):
            table_count = len(cast(Any, table_list))
        else:
            table_count = 0
    except Exception:
        table_count = 0
    if table_count > 0:
        placeholders.append(f"_[Tables detected: {table_count}]_")
    return placeholders

def _markdown_front_matter(file_path: str, doc: Any) -> str:
    metadata = doc.metadata if isinstance(getattr(doc, "metadata", None), dict) else {}
    title = _as_str(metadata.get("title"))
    author = _as_str(metadata.get("author"))
    page_count = len(doc)
    lines = [
        "---",
        f"file_name: {json.dumps(os.path.basename(file_path), ensure_ascii=False)}",
        f"title: {json.dumps(title, ensure_ascii=False)}",
        f"author: {json.dumps(author, ensure_ascii=False)}",
        f"page_count: {page_count}",
        "---",
        "",
        "",
    ]
    return "\n".join(lines)
