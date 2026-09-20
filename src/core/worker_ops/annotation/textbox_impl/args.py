"""텍스트상자 kwargs 파싱 순수 헬퍼 (self 비의존).

single/batch/replace에 흩어져 있던 rect·스타일 파싱 3중복을 한 곳으로 모은다.
동작은 기존 메서드와 동일하게 유지한다 (기본값·별칭 차이 포함).
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from ....worker_runtime.args import _as_float, _as_int, _as_str


def rect_from_source(
    source: Mapping[str, Any],
    *,
    default_x: float = 100.0,
    default_y: float = 100.0,
    default_w: float = 200.0,
    default_h: float = 50.0,
    use_size_aliases: bool = False,
) -> list[float]:
    """rect 또는 x/y[/w/h] 에서 [x0, y0, x1, y1] 을 만든다."""
    rect_arg = source.get("rect")
    if rect_arg:
        return [float(v) for v in cast(list[Any], rect_arg)]
    x = _as_float(source.get("x"), default_x)
    y = _as_float(source.get("y"), default_y)
    if use_size_aliases:
        w = _as_float(source.get("w"), _as_float(source.get("width"), default_w))
        h = _as_float(source.get("h"), _as_float(source.get("height"), default_h))
    else:
        w = _as_float(source.get("w"), default_w)
        h = _as_float(source.get("h"), default_h)
    return [x, y, x + w, y + h]


def style_from_source(source: Mapping[str, Any]) -> dict[str, Any]:
    """fontsize·color·align·fontname·opacity·rotation·layer 파싱."""
    fontsize = max(1, _as_int(source.get("fontsize"), 12))
    raw_color = source.get("color", [0, 0, 0])
    try:
        color = tuple(float(c) for c in cast(list[Any] | tuple[Any, ...], raw_color)[:3])
        if len(color) < 3:
            color = (0.0, 0.0, 0.0)
    except Exception:
        color = (0.0, 0.0, 0.0)
    align = _as_int(source.get("align"), 0)
    fontname = _as_str(source.get("fontname"), "helv")
    opacity = max(0.0, min(1.0, _as_float(source.get("opacity"), 1.0)))
    # insert_textbox 는 90° 배수만 허용
    rotation = _as_int(source.get("rotation"), 0) % 360
    rotation = int(round(rotation / 90.0) * 90) % 360
    layer = _as_str(source.get("layer"), "foreground")
    return {
        "fontsize": fontsize,
        "color": color,
        "align": align,
        "fontname": fontname,
        "opacity": opacity,
        "rotation": rotation,
        "layer": layer,
    }


def fill_from_source(source: Mapping[str, Any]) -> tuple[float, float, float]:
    """교정(redact) 영역 배경색 파싱. 기본 흰색."""
    fill_color = source.get("fill_color", (1, 1, 1))
    try:
        fill = tuple(float(c) for c in cast(list[Any] | tuple[Any, ...], fill_color)[:3])
        if len(fill) < 3:
            fill = (1.0, 1.0, 1.0)
    except Exception:
        fill = (1.0, 1.0, 1.0)
    return (fill[0], fill[1], fill[2])


__all__ = ["fill_from_source", "rect_from_source", "style_from_source"]
