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


def pixel_diff_ratio(
    p1: Any,
    p2: Any,
    *,
    visual_dpi: float = 72.0,
) -> float:
    """두 페이지 pixmap 샘플 기반 픽셀 차이 비율 (0~1)."""
    zoom = visual_dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix1 = p1.get_pixmap(matrix=mat, alpha=False)
    pix2 = p2.get_pixmap(matrix=mat, alpha=False)
    # 크기 맞추기
    w = min(pix1.width, pix2.width)
    h = min(pix1.height, pix2.height)
    if w <= 0 or h <= 0:
        return 1.0
    if pix1.width != w or pix1.height != h:
        pix1 = fitz.Pixmap(pix1, w, h, None)
    if pix2.width != w or pix2.height != h:
        pix2 = fitz.Pixmap(pix2, w, h, None)
    s1 = pix1.samples
    s2 = pix2.samples
    n = min(len(s1), len(s2))
    if n == 0:
        return 1.0
    # 샘플링으로 속도 확보
    step = max(1, n // 120000)
    diff = 0
    total = 0
    for i in range(0, n, step):
        total += 1
        if s1[i] != s2[i]:
            diff += 1
    return diff / max(1, total)
