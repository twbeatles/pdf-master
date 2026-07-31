"""텍스트 상자 위치 프리셋 (A4 기본, 실제 페이지 크기 우선)."""

from __future__ import annotations

# PDF 포인트 기준 A4 (세로)
A4_WIDTH_PT = 595.0
A4_HEIGHT_PT = 842.0
DEFAULT_MARGIN_PT = 36.0  # 약 0.5 inch


# UI data 값 → 앵커
TEXTBOX_PRESET_KEYS = (
    "custom",
    "top-left",
    "top-center",
    "top-right",
    "center-left",
    "center",
    "center-right",
    "bottom-left",
    "bottom-center",
    "bottom-right",
)


def resolve_textbox_preset_xy(
    preset: str,
    page_w: float,
    page_h: float,
    box_w: float,
    box_h: float,
    *,
    margin: float = DEFAULT_MARGIN_PT,
) -> tuple[float, float] | None:
    """프리셋 키에 해당하는 박스 좌상단 (x, y) PDF 포인트를 반환.

    custom 또는 알 수 없는 키는 None.
    """
    key = (preset or "").strip().lower()
    if key in ("", "custom", "manual"):
        return None

    pw = max(1.0, float(page_w))
    ph = max(1.0, float(page_h))
    bw = max(1.0, min(float(box_w), pw))
    bh = max(1.0, min(float(box_h), ph))
    m = max(0.0, float(margin))

    # 여백이 박스보다 크면 여백 축소
    if bw + 2 * m > pw:
        m = max(0.0, (pw - bw) / 2.0)
    if bh + 2 * m > ph:
        m = max(0.0, (ph - bh) / 2.0)

    cx = (pw - bw) / 2.0
    cy = (ph - bh) / 2.0
    right = pw - bw - m
    bottom = ph - bh - m

    table: dict[str, tuple[float, float]] = {
        "top-left": (m, m),
        "top-center": (cx, m),
        "top-right": (right, m),
        "center-left": (m, cy),
        "center": (cx, cy),
        "center-right": (right, cy),
        "bottom-left": (m, bottom),
        "bottom-center": (cx, bottom),
        "bottom-right": (right, bottom),
    }
    xy = table.get(key)
    if xy is None:
        return None
    x = max(0.0, min(xy[0], pw - bw))
    y = max(0.0, min(xy[1], ph - bh))
    return (x, y)


__all__ = [
    "A4_WIDTH_PT",
    "A4_HEIGHT_PT",
    "DEFAULT_MARGIN_PT",
    "TEXTBOX_PRESET_KEYS",
    "resolve_textbox_preset_xy",
]
