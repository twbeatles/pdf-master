#!/usr/bin/env python3
"""compare/ops.py 중첩 순수 함수를 helpers 모듈로 리프트 (move-only)."""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / "src/core/worker_ops/compare/ops.py"
HELPERS = ROOT / "src/core/worker_ops/compare/helpers.py"


def main() -> None:
    src = OPS.read_text(encoding="utf-8")
    # Nested helpers that do not close over outer state (except fitz/Counter which are imports)
    # Lift: _normalize_block_text, _collect_text_blocks, _diff_blocks, _scale_rect, _draw_overlay_rect
    # Keep _pixel_diff_ratio nested (closes over visual_dpi)

    helpers_src = '''"""PDF 비교 순수 헬퍼 (compare ops 에서 리프트)."""
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
'''
    HELPERS.write_text(helpers_src, encoding="utf-8")

    # Rewrite ops.py: remove nested defs and use helpers; keep _pixel_diff_ratio nested
    # Strategy: string replace the nested function block with import + aliases
    old_nested = '''        def _normalize_block_text(text: Any) -> str:
            return " ".join(str(text or "").split()).casefold()

        def _collect_text_blocks(page: Any) -> list[dict[str, Any]]:
            blocks: list[dict[str, Any]] = []
            for block in page.get_text("blocks"):
                if len(block) < 7 or block[6] != 0:
                    continue
                normalized = _normalize_block_text(block[4])
                if not normalized:
                    continue
                blocks.append({"text": normalized, "rect": fitz.Rect(block[:4])})
            return blocks

        def _diff_blocks(source_blocks: list[dict[str, Any]], target_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
            source_counter = Counter(block["text"] for block in source_blocks)
            target_counter = Counter(block["text"] for block in target_blocks)
            remaining = source_counter - target_counter
            consumed: Counter[str] = Counter()
            diff_blocks: list[dict[str, Any]] = []
            for block in source_blocks:
                key = block["text"]
                if remaining[key] <= consumed[key]:
                    continue
                consumed[key] += 1
                diff_blocks.append(block)
            return diff_blocks

        def _scale_rect(rect: Any, source_rect: Any, canvas_rect: Any) -> Any:
            width_scale = canvas_rect.width / source_rect.width if source_rect.width else 1.0
            height_scale = canvas_rect.height / source_rect.height if source_rect.height else 1.0
            return fitz.Rect(
                rect.x0 * width_scale,
                rect.y0 * height_scale,
                rect.x1 * width_scale,
                rect.y1 * height_scale,
            )

        def _draw_overlay_rect(page: Any, rect: Any, *, stroke: tuple[float, float, float], fill: tuple[float, float, float]):
            page.draw_rect(rect, color=stroke, width=1.5)
            shape = page.new_shape()
            shape.draw_rect(rect)
            shape.finish(color=stroke, fill=fill, fill_opacity=0.25)
            shape.commit()
'''
    new_nested = '''        _normalize_block_text = normalize_block_text
        _collect_text_blocks = collect_text_blocks
        _diff_blocks = diff_blocks
        _scale_rect = scale_rect
        _draw_overlay_rect = draw_overlay_rect
'''
    if old_nested not in src:
        raise SystemExit("nested block not found — ops.py may have changed")
    src = src.replace(old_nested, new_nested, 1)

    # Add import for helpers after existing imports
    needle = "from .._pdf_helpers import (\n"
    if "from .helpers import" not in src:
        insert = (
            "from .helpers import (\n"
            "    collect_text_blocks,\n"
            "    diff_blocks,\n"
            "    draw_overlay_rect,\n"
            "    normalize_block_text,\n"
            "    scale_rect,\n"
            ")\n"
        )
        # insert before logger
        src = src.replace(
            "logger = logging.getLogger(__name__)\n",
            insert + "\nlogger = logging.getLogger(__name__)\n",
            1,
        )

    # Counter may still be needed in ops for other uses — leave import
    OPS.write_text(src, encoding="utf-8")
    ast.parse(src)
    ast.parse(helpers_src)
    print(f"OK compare helpers={len(helpers_src.splitlines())} ops={len(src.splitlines())}")


if __name__ == "__main__":
    main()
