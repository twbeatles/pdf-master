"""Fluent redesign design tokens (DESKTOP_UI_DESIGN_RULES §5·§6·§7·§20·§21).

Pure-Python single source: spacing / control heights / typography /
semantic colors / window sizing. Qt import 없음 — headless 테스트 가능.
기존 자값(1200x850, margins 15/10, spacing 8)은 COMPACT 프리셋으로 보존하고,
신규 화면은 COMFORTABLE(§21 page margin 24) 권장.
"""

from __future__ import annotations

# §5 spacing scale — 이 값만 사용
SPACING_4 = 4
SPACING_8 = 8
SPACING_12 = 12
SPACING_16 = 16
SPACING_24 = 24
SPACING_32 = 32
ALLOWED_SPACING = frozenset({4, 8, 12, 16, 24, 32})

# form row / group / section / page 여백 (§21)
FORM_ROW_GAP = SPACING_12
GROUP_GAP = SPACING_16
SECTION_GAP = SPACING_24
PAGE_MARGIN_COMFORTABLE = SPACING_24
ICON_TEXT_GAP = SPACING_8

# 현행 main_window 레이아웃값 보존용 compact 프리셋
PAGE_MARGIN_COMPACT_H = 15
PAGE_MARGIN_COMPACT_V = 10
LAYOUT_SPACING_COMPACT = 8

# §5 컨트롤 높이
CONTROL_HEIGHT_SMALL = 32
CONTROL_HEIGHT_DEFAULT = 36
CONTROL_HEIGHT_LARGE = 40

# §6 typography (pt 기준, fallback chain)
FONT_FAMILIES = ("Pretendard", "Segoe UI", "Apple SD Gothic Neo", "Malgun Gothic", "sans-serif")
FONT_SIZE_PAGE = 22  # Page title 22~24 Semibold
FONT_SIZE_SECTION = 16  # Section 16~18
FONT_SIZE_BODY = 13  # Body 13~14 (현행 Segoe UI 9pt와 시각 동등대)
FONT_SIZE_SECONDARY = 12
FONT_SIZE_CAPTION = 11

# §7 semantic colors — 기존 ThemeColors.PRIMARY(#4f8cff) 유지, 도메인색 복제 금지(§0)
SEMANTIC_COLORS = {
    "primary": "#4f8cff",
    "background_dark": "#0a0e14",
    "surface_dark": "#141922",
    "border_dark": "#2d3748",
    "text_dark": "#f0f4f8",
    "text_secondary_dark": "#94a3b8",
    "background_light": "#f8fafc",
    "surface_light": "#ffffff",
    "border_light": "#e2e8f0",
    "text_light": "#1e293b",
    "text_secondary_light": "#64748b",
    "success": "#10b981",
    "warning": "#f59e0b",
    "error": "#ef4444",
}

# §20 window sizing (srtgo preferred_window_size 계승)
WINDOW_DEFAULT_SIZE = (1200, 850)
WINDOW_MIN_SIZE = (950, 700)
SCREEN_MARGIN = 40


def preferred_window_size(
    avail_width: int | None,
    avail_height: int | None,
    default: tuple[int, int] = WINDOW_DEFAULT_SIZE,
    minimum: tuple[int, int] = WINDOW_MIN_SIZE,
    margin: int = SCREEN_MARGIN,
) -> tuple[int, int]:
    """가용 영역을 넘지 않는 초기 창 크기. avail None이면 default."""
    if avail_width is None or avail_height is None:
        return (default[0], default[1])
    width = min(default[0], max(minimum[0], avail_width - margin))
    height = min(default[1], max(minimum[1], avail_height - margin))
    return (width, height)


def clamp_minimum_size(width: int, height: int, minimum: tuple[int, int] = WINDOW_MIN_SIZE) -> tuple[int, int]:
    """작은 화면에서 minimum이 창보다 커지는 파손 방지."""
    return (min(minimum[0], width), min(minimum[1], height))
