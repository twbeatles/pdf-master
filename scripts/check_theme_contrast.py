"""Stylesheet contrast gate: keep menu text legible in every theme.

Dark sheets once shipped menu backgrounds without text colors (black text
inherited on near-black backgrounds); light sheets inherited a near-white
disabled gray. Both were invisible in practice. This gate fails the build
when any QMenu*/QMenuBar* rule (except separators) lacks an explicit text
color or falls below the contrast threshold.

Usage: python scripts/check_theme_contrast.py  (exit 1 on violation)
Requires only the standard library.
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ui.theme import (
    DARK_STYLESHEET,
    LIGHT_STYLESHEET,
    NATIVE_DARK_STYLESHEET,
    NATIVE_LIGHT_STYLESHEET,
)

BLOCK_RE = re.compile(r"(QMenuBar[^{]*|QMenu[^{]*)\{([^}]*)\}")
COLOR_RE = re.compile(r"(?<![\w-])color\s*:\s*([^;]+);")
BACKGROUND_RE = re.compile(r"(?<![\w-])background(?:-color)?\s*:\s*([^;]+);")
HEX_RE = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})")
RGBA_RE = re.compile(
    r"rgba\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*([0-9.]+)\s*\)"
)

NAMED_COLORS = {"white": "#ffffff", "black": "#000000"}

NORMAL_MIN_CONTRAST = 4.5
STATE_MIN_CONTRAST = 3.0  # :selected/:disabled/:hover/:checked highlights
SKIP_SELECTORS = ("QMenu::separator",)

SHEETS = (
    ("NATIVE_DARK", NATIVE_DARK_STYLESHEET, "#141922"),
    ("DARK", DARK_STYLESHEET, "#141922"),
    ("NATIVE_LIGHT", NATIVE_LIGHT_STYLESHEET, "#ffffff"),
    ("LIGHT", LIGHT_STYLESHEET, "#ffffff"),
)


def _to_rgb(value: str) -> tuple[int, int, int] | None:
    value = value.strip().lower()
    if value in NAMED_COLORS:
        value = NAMED_COLORS[value]
    match = re.fullmatch(r"#([0-9a-f]{6}|[0-9a-f]{3})", value)
    if not match:
        return None
    digits = match.group(1)
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    return (int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16))


def _luminance(rgb: tuple[int, int, int]) -> float:
    def linear(channel: float) -> float:
        channel /= 255.0
        return channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = rgb
    return 0.2126 * linear(red) + 0.7152 * linear(green) + 0.0722 * linear(blue)


def contrast(fg: tuple[int, int, int], bg: tuple[int, int, int]) -> float:
    light, dark = max(_luminance(fg), _luminance(bg)), min(_luminance(fg), _luminance(bg))
    return (light + 0.05) / (dark + 0.05)


def _effective_background(value: str, base: tuple[int, int, int]) -> tuple[int, int, int] | None:
    """Resolve a background value to one RGB: solid hex, darkest gradient
    stop, or rgba blended over the sheet base. Returns None when unknown."""
    rgba = RGBA_RE.search(value)
    if rgba:
        red, green, blue, alpha = int(rgba.group(1)), int(rgba.group(2)), int(rgba.group(3)), float(rgba.group(4))
        blended = [
            round(alpha * channel + (1.0 - alpha) * ground)
            for channel, ground in zip((red, green, blue), base)
        ]
        return (blended[0], blended[1], blended[2])
    hexes = [_to_rgb("#" + digits) for digits in HEX_RE.findall(value)]
    hexes = [rgb for rgb in hexes if rgb is not None]
    if hexes:
        return min(hexes, key=_luminance)
    return None


def check_sheet(name: str, sheet: str, base_bg: str) -> list[str]:
    """Return human-readable violations for one stylesheet (empty when OK)."""
    base = _to_rgb(base_bg)
    assert base is not None
    issues = []
    for selector, body in BLOCK_RE.findall(sheet):
        selector = selector.strip()
        if selector in SKIP_SELECTORS:
            continue
        color_match = COLOR_RE.search(body)
        if not color_match:
            issues.append(f"{name} {selector}: missing explicit text color")
            continue
        fg = _to_rgb(color_match.group(1))
        if fg is None:
            continue  # Unparsable color keyword: presence is still enforced.
        bg_match = BACKGROUND_RE.search(body)
        if bg_match:
            bg = _effective_background(bg_match.group(1), base)
            bg_label = bg_match.group(1).strip()
        else:
            bg, bg_label = base, base_bg
        if bg is None:
            continue
        threshold = (
            STATE_MIN_CONTRAST
            if any(state in selector for state in (":selected", ":disabled", ":hover", ":checked"))
            else NORMAL_MIN_CONTRAST
        )
        ratio = contrast(fg, bg)
        if ratio < threshold:
            issues.append(
                f"{name} {selector}: contrast {ratio:.2f} < {threshold} "
                f"({color_match.group(1).strip()} on {bg_label})"
            )
    return issues


def check_all_sheets() -> dict[str, list[str]]:
    return {
        name: check_sheet(name, sheet, base)
        for name, sheet, base in SHEETS
    }


def main() -> int:
    failures = {name: issues for name, issues in check_all_sheets().items() if issues}
    if failures:
        for name, issues in failures.items():
            for issue in issues:
                print(f"FAIL {issue}")
        return 1
    print(f"OK menu contrast in {len(SHEETS)} stylesheets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
