from __future__ import annotations
import hashlib
import logging
import os
import re
from collections import Counter
from typing import Any, cast
from ..._typing import WorkerHost
from ...optional_deps import fitz
from ...worker_runtime.args import (
    _as_bool,
    _as_float,
    _as_int,
    _as_list,
    _as_str,
)
logger = logging.getLogger(__name__)
_HEADING_MIN_SIZE = 12.0
_HEADING_SIZE_GAP = 1.5


def _page_text_len(page: Any) -> int:
    try:
        return len((_as_str(page.get_text("text")) or "").strip())
    except Exception:
        return 0

def _page_image_count(page: Any) -> int:
    try:
        return len(page.get_images(full=True) or [])
    except Exception:
        return 0

def _page_drawing_count(page: Any) -> int:
    get_drawings = getattr(page, "get_drawings", None)
    if not callable(get_drawings):
        return 0
    try:
        drawings = get_drawings() or []
        return len(cast(list[Any], drawings))
    except Exception:
        return 0

def _is_blank_page(page: Any, *, text_threshold: int = 0) -> bool:
    if _page_text_len(page) > text_threshold:
        return False
    if _page_image_count(page) > 0:
        return False
    if _page_drawing_count(page) > 0:
        return False
    # 저해상도 렌더로 거의 흰 페이지만 빈 페이지로 취급
    try:
        pix = page.get_pixmap(matrix=fitz.Matrix(0.2, 0.2), alpha=False)
        samples = pix.samples
        if not samples:
            return True
        # 평균 밝기 매우 높고 분산이 작으면 빈 페이지
        step = max(1, len(samples) // 3000)
        vals = samples[::step]
        if not vals:
            return True
        avg = sum(vals) / len(vals)
        if avg < 250:
            return False
        var = sum((v - avg) ** 2 for v in vals) / len(vals)
        return var < 30.0
    except Exception:
        # 렌더 실패 시 빈 페이지로 오판하면 데이터 손실 → 보수적으로 유지
        return False

def _page_signature(page: Any) -> str:
    """중복 판별용 시그니처 (텍스트 + 저해상도 해시)."""
    text = ""
    try:
        text = " ".join((_as_str(page.get_text("text")) or "").split())
    except Exception:
        text = ""
    digest = hashlib.sha1()
    digest.update(text.encode("utf-8", errors="ignore"))
    try:
        pix = page.get_pixmap(matrix=fitz.Matrix(0.15, 0.15), alpha=False)
        digest.update(bytes(pix.samples[:50000]))
        digest.update(f"{pix.width}x{pix.height}".encode("ascii"))
    except Exception:
        digest.update(b"no-pix")
    return digest.hexdigest()

def _content_bbox(page: Any, *, pad: float = 2.0) -> Any | None:
    """텍스트/이미지/드로잉 합집합 bbox. 콘텐츠 없으면 None."""
    rect = page.rect
    min_x, min_y = rect.x1, rect.y1
    max_x, max_y = rect.x0, rect.y0
    found = False

    try:
        for block in page.get_text("blocks") or []:
            if len(block) < 5:
                continue
            # type 0 text, 1 image in blocks format when full
            x0, y0, x1, y1 = float(block[0]), float(block[1]), float(block[2]), float(block[3])
            if x1 <= x0 or y1 <= y0:
                continue
            found = True
            min_x, min_y = min(min_x, x0), min(min_y, y0)
            max_x, max_y = max(max_x, x1), max(max_y, y1)
    except Exception:
        pass

    try:
        for img in page.get_images(full=True) or []:
            xref = int(img[0])
            for r in page.get_image_rects(xref) or []:
                found = True
                min_x, min_y = min(min_x, r.x0), min(min_y, r.y0)
                max_x, max_y = max(max_x, r.x1), max(max_y, r.y1)
    except Exception:
        pass

    try:
        get_drawings = getattr(page, "get_drawings", None)
        if callable(get_drawings):
            drawings = cast(list[Any], get_drawings() or [])
            for path in drawings:
                r = path.get("rect") if isinstance(path, dict) else None
                if r is None:
                    continue
                found = True
                min_x, min_y = min(min_x, float(r.x0)), min(min_y, float(r.y0))
                max_x, max_y = max(max_x, float(r.x1)), max(max_y, float(r.y1))
    except Exception:
        pass

    if not found:
        return None

    bbox = fitz.Rect(min_x - pad, min_y - pad, max_x + pad, max_y + pad)
    return bbox & rect

def _collect_heading_toc(
    doc: Any,
    *,
    min_size: float = _HEADING_MIN_SIZE,
    check_cancelled: Any | None = None,
) -> list[list[Any]]:
    """폰트 크기 휴리스틱으로 목차 후보 생성."""
    size_counter: Counter[float] = Counter()
    candidates: list[tuple[int, float, str]] = []

    for page_index in range(len(doc)):
        if callable(check_cancelled):
            check_cancelled()
        page = doc[page_index]
        try:
            text_dict = page.get_text("dict") or {}
        except Exception:
            continue
        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                spans = line.get("spans") or []
                if not spans:
                    continue
                text = "".join(str(s.get("text") or "") for s in spans).strip()
                if not text or len(text) > 120:
                    continue
                # 번호·한 줄 제목 위주
                if text.endswith(".") and len(text) > 80:
                    continue
                size = max(float(s.get("size") or 0.0) for s in spans)
                if size < min_size:
                    continue
                rounded = round(size, 1)
                size_counter[rounded] += 1
                candidates.append((page_index + 1, rounded, text))

    if not candidates:
        return []

    # 본문보다 큰 상위 크기만 제목으로
    body_size = size_counter.most_common(1)[0][0] if size_counter else min_size
    heading_sizes = sorted(
        (s for s in size_counter if s >= body_size + _HEADING_SIZE_GAP or s >= min_size + 2),
        reverse=True,
    )
    if not heading_sizes:
        heading_sizes = sorted({s for _, s, _ in candidates}, reverse=True)[:2]

    size_to_level = {s: idx + 1 for idx, s in enumerate(heading_sizes[:3])}
    toc: list[list[Any]] = []
    seen: set[tuple[int, str]] = set()
    for page_num, size, text in candidates:
        level = size_to_level.get(size)
        if level is None:
            continue
        key = (page_num, text.casefold())
        if key in seen:
            continue
        seen.add(key)
        toc.append([level, text, page_num])
    return toc
