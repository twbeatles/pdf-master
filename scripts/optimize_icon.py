"""원본 icon.png에서 앱 번들용 아이콘 자산을 생성합니다."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ICON = REPO_ROOT / "icon.png"
ASSETS_DIR = REPO_ROOT / "assets"
PNG_OUTPUT = ASSETS_DIR / "app_icon.png"
ICO_OUTPUT = ASSETS_DIR / "app_icon.ico"
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
PNG_SIZE = 256


def _load_source_image() -> Image.Image:
    if not SOURCE_ICON.is_file():
        raise FileNotFoundError(f"원본 아이콘을 찾을 수 없습니다: {SOURCE_ICON}")
    image = Image.open(SOURCE_ICON).convert("RGBA")
    return image


def _write_png(image: Image.Image) -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    resized = image.resize((PNG_SIZE, PNG_SIZE), Image.Resampling.LANCZOS)
    resized.save(PNG_OUTPUT, format="PNG", optimize=True)


def _write_ico(image: Image.Image) -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    image.save(
        ICO_OUTPUT,
        format="ICO",
        sizes=[(size, size) for size in ICO_SIZES],
    )


def main() -> int:
    source = _load_source_image()
    _write_png(source)
    _write_ico(source)

    png_kb = PNG_OUTPUT.stat().st_size / 1024
    ico_kb = ICO_OUTPUT.stat().st_size / 1024
    print(f"[OK] {PNG_OUTPUT.relative_to(REPO_ROOT)} ({png_kb:.1f} KB)")
    print(f"[OK] {ICO_OUTPUT.relative_to(REPO_ROOT)} ({ico_kb:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())