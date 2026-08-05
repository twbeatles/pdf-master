"""텍스트상자 삽입 순수 헬퍼 (self 비의존)."""
from __future__ import annotations

import logging
from typing import Any

from ...optional_deps import fitz
from .._pdf_helpers import text_needs_cjk

logger = logging.getLogger(__name__)


def ensure_textbox_rect(rect: list[float], text: str, fontsize: int) -> list[float]:
    """폰트 크기·줄 수에 맞게 최소 높이를 확보한다."""
    x0, y0, x1, y1 = (float(rect[0]), float(rect[1]), float(rect[2]), float(rect[3]))
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0
    lines = max(1, text.count("\n") + 1)
    # insert_textbox 는 박스 높이가 부족하면 글자를 쓰지 않고 음수를 반환한다
    min_h = max(float(fontsize) * 1.4 * lines + 4.0, float(fontsize) + 8.0)
    min_w = max(40.0, float(fontsize) * 2.0)
    if (y1 - y0) < min_h:
        y1 = y0 + min_h
    if (x1 - x0) < min_w:
        x1 = x0 + min_w
    return [x0, y0, x1, y1]

def write_textbox_content(page: Any,
    fitz_rect: Any,
    text: str,
    *,
    fontsize: int,
    fontname: str,
    color: tuple[float, ...],
    align: int,
    rotation: int,
    opacity: float,
    overlay: bool,
) -> bool:
    """insert_textbox 시도 → 오버플로 시 높이 확장 재시도 → insert_text 폴백."""
    try:
        rc = page.insert_textbox(
            fitz_rect,
            text,
            fontsize=fontsize,
            fontname=fontname,
            color=color,
            align=align,
            rotate=rotation,
            fill_opacity=opacity,
            stroke_opacity=opacity,
            overlay=overlay,
        )
    except Exception:
        logger.warning("insert_textbox failed; trying insert_text fallback", exc_info=True)
        rc = -1.0

    # 음수 = 남은 높이 부족(텍스트 미기록 또는 부분 실패)
    if isinstance(rc, (int, float)) and rc < 0:
        expanded = fitz.Rect(
            fitz_rect.x0,
            fitz_rect.y0,
            fitz_rect.x1,
            fitz_rect.y1 + abs(float(rc)) + float(fontsize),
        )
        # 페이지 하단 클램프
        expanded.y1 = min(expanded.y1, page.rect.y1 - 2)
        if expanded.height > fitz_rect.height + 0.5:
            try:
                rc2 = page.insert_textbox(
                    expanded,
                    text,
                    fontsize=fontsize,
                    fontname=fontname,
                    color=color,
                    align=align,
                    rotate=rotation,
                    fill_opacity=opacity,
                    stroke_opacity=opacity,
                    overlay=overlay,
                )
                if isinstance(rc2, (int, float)) and rc2 >= 0:
                    return True
            except Exception:
                logger.debug("expanded insert_textbox failed", exc_info=True)

        # 최종 폴백: 기준점 텍스트 (항상 기록 시도)
        try:
            baseline = fitz.Point(
                fitz_rect.x0,
                min(fitz_rect.y0 + float(fontsize), page.rect.y1 - 2),
            )
            n = page.insert_text(
                baseline,
                text,
                fontsize=fontsize,
                fontname=fontname,
                color=color,
                rotate=rotation if rotation in (0, 90, 180, 270) else 0,
                fill_opacity=opacity,
                overlay=overlay,
            )
            return isinstance(n, (int, float)) and int(n) > 0
        except Exception:
            logger.warning("insert_text fallback failed", exc_info=True)
            return False

    # 성공 경로: 텍스트가 실제로 있는지 확인 (빈 성공 방지)
    try:
        sample = page.get_text("text") or ""
        # 입력 텍스트의 첫 토큰이 페이지에 있으면 OK (부분 매칭)
        token = text.strip().split()[0] if text.strip() else ""
        if token and token in sample:
            return True
        # CJK/공백 없는 문자열
        compact = text.strip()[:8]
        if compact and compact in sample.replace("\n", ""):
            return True
        # insert_textbox 양수 반환이면 공간은 남았다는 뜻 — 내용 기록된 것으로 간주
        if isinstance(rc, (int, float)) and rc >= 0:
            return True
    except Exception:
        if isinstance(rc, (int, float)) and rc >= 0:
            return True
    return False

def resolve_textbox_fontname(page: Any, fontname: str, text: str = "") -> str:
    """UI/별칭 폰트명을 PyMuPDF insert_textbox 가 받을 수 있는 이름으로 해석."""
    key = (fontname or "").strip().lower()
    # 자동: 텍스트에 CJK가 있으면 cjk 임베드 (배치 워터마크 등)
    if not key or key in {"auto", "default"}:
        key = "cjk" if text_needs_cjk(text) else "helv"
    # Base-14 / 흔한 별칭
    aliases = {
        "helv": "helv",
        "helvetica": "helv",
        "cour": "cour",
        "courier": "cour",
        "couri": "cour",
        "tiro": "tiro",
        "times": "tiro",
        "times-roman": "tiro",
        "timesroman": "tiro",
    }
    if key in aliases:
        # helv 지정인데 CJK 텍스트면 자동 승격
        if key == "helv" and text_needs_cjk(text):
            key = "cjk"
        else:
            return aliases[key]

    # CJK: fontname="cjk" 직접 전달 불가 → 임베드 후 등록명 사용
    if key in {"cjk", "cjk_safe", "ko", "korean", "china-s", "china-t", "japan", "korea"}:
        registered = "pdfmaster_cjk"
        try:
            page.insert_font(fontname=registered, fontbuffer=fitz.Font("cjk").buffer)
            return registered
        except Exception:
            logger.warning("CJK font embed failed; falling back to helv", exc_info=True)
            return "helv"

    # 알 수 없는 이름은 그대로 시도 (커스텀 등록 폰트 등)
    return fontname or "helv"
