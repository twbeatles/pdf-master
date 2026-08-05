"""PDF 비교 순수 헬퍼 (compare ops 에서 리프트)."""
from __future__ import annotations

from collections import Counter
from typing import Any

from ...optional_deps import fitz


def normalize_block_text(text: Any) -> str:
    return " ".join(str(text or "").split()).casefold()


def collect_text_blocks(page: Any) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for block in page.get_text("blocks"):
        if len(block) < 7 or block[6] != 0:
            continue
        normalized = normalize_block_text(block[4])
        if not normalized:
            continue
        blocks.append({"text": normalized, "rect": fitz.Rect(block[:4])})
    return blocks


def diff_blocks(source_blocks: list[dict[str, Any]], target_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source_counter = Counter(block["text"] for block in source_blocks)
    target_counter = Counter(block["text"] for block in target_blocks)
    remaining = source_counter - target_counter
    consumed: Counter[str] = Counter()
    diff_blocks_out: list[dict[str, Any]] = []
    for block in source_blocks:
        key = block["text"]
        if remaining[key] <= consumed[key]:
            continue
        consumed[key] += 1
        diff_blocks_out.append(block)
    return diff_blocks_out


def scale_rect(rect: Any, source_rect: Any, canvas_rect: Any) -> Any:
    width_scale = canvas_rect.width / source_rect.width if source_rect.width else 1.0
    height_scale = canvas_rect.height / source_rect.height if source_rect.height else 1.0
    return fitz.Rect(
        rect.x0 * width_scale,
        rect.y0 * height_scale,
        rect.x1 * width_scale,
        rect.y1 * height_scale,
    )


def draw_overlay_rect(
    page: Any,
    rect: Any,
    *,
    stroke: tuple[float, float, float],
    fill: tuple[float, float, float],
) -> None:
    page.draw_rect(rect, color=stroke, width=1.5)
    shape = page.new_shape()
    shape.draw_rect(rect)
    shape.finish(color=stroke, fill=fill, fill_opacity=0.25)
    shape.commit()
