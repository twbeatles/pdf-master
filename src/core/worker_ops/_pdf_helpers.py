from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from typing import Any, cast

from ..optional_deps import fitz
from ..worker_runtime.args import _as_str

logger = logging.getLogger(__name__)


def _sample_diff_text(lines: list[str], max_items: int = 2) -> str:
    visible = [line.strip() for line in lines if isinstance(line, str) and line.strip()]
    return " | ".join(visible[:max_items]) if visible else "∅"

def _normalize_stroke_points(raw_points: Any) -> list[list[float]]:
    if not isinstance(raw_points, (list, tuple)):
        raise ValueError("points must be a sequence")

    normalized_points: list[list[float]] = []
    for raw_point in raw_points:
        if not isinstance(raw_point, (list, tuple)) or len(raw_point) < 2:
            raise ValueError("invalid stroke point")
        normalized_points.append([float(raw_point[0]), float(raw_point[1])])

    if len(normalized_points) < 2:
        raise ValueError("stroke requires at least two points")

    return normalized_points

def _fallback_markdown_from_text(page: Any) -> str:
    text = _as_str(page.get_text("text"))
    page_chunks: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped:
            page_chunks.append(stripped)
    return "\n\n".join(page_chunks).strip()

def _extract_native_markdown(page: Any) -> str:
    for option in ("markdown", "md"):
        try:
            extracted = page.get_text(option)
        except Exception:
            extracted = ""
        if isinstance(extracted, str) and extracted.strip():
            return extracted.strip()
    return ""

def _extract_page_markdown(page: Any, markdown_mode: str) -> str:
    if markdown_mode in {"auto", "native"}:
        native_markdown = _extract_native_markdown(page)
        if native_markdown:
            return native_markdown
        if markdown_mode == "native":
            raise RuntimeError("Native Markdown extraction is not available for this document/runtime.")
    return _fallback_markdown_from_text(page)

def _page_asset_placeholders(page: Any) -> list[str]:
    placeholders: list[str] = []
    try:
        image_count = len(page.get_images(full=True))
    except Exception:
        image_count = 0
    if image_count > 0:
        placeholders.append(f"_[Images detected: {image_count}]_")

    try:
        find_tables = getattr(page, "find_tables", None)
        tables = find_tables() if callable(find_tables) else None
        table_list = getattr(tables, "tables", tables)
        if table_list is not None and hasattr(table_list, "__len__"):
            table_count = len(cast(Any, table_list))
        else:
            table_count = 0
    except Exception:
        table_count = 0
    if table_count > 0:
        placeholders.append(f"_[Tables detected: {table_count}]_")
    return placeholders

def _markdown_front_matter(file_path: str, doc: Any) -> str:
    metadata = doc.metadata if isinstance(getattr(doc, "metadata", None), dict) else {}
    title = _as_str(metadata.get("title"))
    author = _as_str(metadata.get("author"))
    page_count = len(doc)
    lines = [
        "---",
        f"file_name: {json.dumps(os.path.basename(file_path), ensure_ascii=False)}",
        f"title: {json.dumps(title, ensure_ascii=False)}",
        f"author: {json.dumps(author, ensure_ascii=False)}",
        f"page_count: {page_count}",
        "---",
        "",
        "",
    ]
    return "\n".join(lines)


def _pixmap_for_reencode(pix: Any, *, grayscale: bool) -> Any:
    """알파/CMYK를 정리하고 필요 시 그레이스케일로 변환한다."""
    current = pix
    # CMYK 등 4채널 이상 → RGB
    if current.n - current.alpha >= 4:
        current = fitz.Pixmap(fitz.csRGB, current)
    if current.alpha:
        current = fitz.Pixmap(current, 0)  # 알파 제거 (JPEG 불가)
    if grayscale and current.n != 1:
        current = fitz.Pixmap(fitz.csGRAY, current)
    return current


def _image_display_size_pt(page: Any, xref: int, fallback_w: float, fallback_h: float) -> tuple[float, float]:
    """페이지 위 이미지 표시 크기(포인트). 없으면 메타데이터 기반 폴백."""
    max_w = 0.0
    max_h = 0.0
    try:
        rects = page.get_image_rects(xref)
    except Exception:
        rects = None
    if rects:
        for rect in rects:
            max_w = max(max_w, float(getattr(rect, "width", 0.0) or 0.0))
            max_h = max(max_h, float(getattr(rect, "height", 0.0) or 0.0))
    if max_w <= 1.0 or max_h <= 1.0:
        # 표시 영역을 못 구하면 원본 픽셀을 96dpi로 가정
        max_w = max(fallback_w * 72.0 / 96.0, 1.0)
        max_h = max(fallback_h * 72.0 / 96.0, 1.0)
    return max_w, max_h


def _target_scale(pix_w: int, pix_h: int, disp_w_pt: float, disp_h_pt: float, max_dpi: float) -> float:
    """표시 크기 대비 현재 DPI가 max_dpi를 넘으면 축소 비율을 반환한다."""
    if pix_w <= 0 or pix_h <= 0 or max_dpi <= 0:
        return 1.0
    dpi_x = pix_w / max(disp_w_pt / 72.0, 1e-6)
    dpi_y = pix_h / max(disp_h_pt / 72.0, 1e-6)
    dpi = max(dpi_x, dpi_y)
    if dpi <= max_dpi:
        return 1.0
    return max(max_dpi / dpi, 0.05)


def optimize_pdf_images(
    doc: Any,
    *,
    max_dpi: float = 150.0,
    jpeg_quality: int = 75,
    grayscale: bool = False,
    min_edge_px: int = 32,
    check_cancelled: Callable[[], None] | None = None,
    progress_cb: Callable[[int, int], None] | None = None,
) -> int:
    """임베디드 이미지를 다운샘플·JPEG 재인코딩한다. 교체 횟수를 반환."""
    # xref -> 문서 전체에서 가장 크게 쓰인 표시 크기
    placement_size: dict[int, tuple[float, float]] = {}
    smask_xrefs: set[int] = set()
    page_count = max(1, len(doc))

    for page_index in range(len(doc)):
        if check_cancelled is not None:
            check_cancelled()
        page = doc[page_index]
        try:
            images = page.get_images(full=True)
        except Exception:
            images = []
        for img in images:
            try:
                xref = int(img[0])
            except (TypeError, ValueError, IndexError):
                continue
            smask = 0
            try:
                smask = int(img[1] or 0)
            except (TypeError, ValueError):
                smask = 0
            if smask:
                smask_xrefs.add(smask)

            try:
                meta_w = float(img[2] or 0)
                meta_h = float(img[3] or 0)
            except (TypeError, ValueError, IndexError):
                meta_w, meta_h = 0.0, 0.0

            disp_w, disp_h = _image_display_size_pt(page, xref, meta_w, meta_h)
            prev_w, prev_h = placement_size.get(xref, (0.0, 0.0))
            placement_size[xref] = (max(prev_w, disp_w), max(prev_h, disp_h))

        if progress_cb is not None:
            progress_cb(page_index + 1, page_count * 2)  # 스캔 단계: 0~50%

    replaced = 0
    xrefs = sorted(placement_size.keys())
    total_xrefs = max(1, len(xrefs))

    for idx, xref in enumerate(xrefs):
        if check_cancelled is not None:
            check_cancelled()
        if xref in smask_xrefs:
            continue

        try:
            pix = fitz.Pixmap(doc, xref)
        except Exception as exc:
            logger.debug("Skip image xref=%s open failed: %s", xref, exc)
            continue

        try:
            if min(pix.width, pix.height) < min_edge_px:
                continue

            try:
                original_stream = doc.xref_stream(xref)
                original_len = len(original_stream) if original_stream else 0
            except Exception:
                original_len = 0

            work = _pixmap_for_reencode(pix, grayscale=grayscale)
            disp_w, disp_h = placement_size.get(xref, (float(work.width), float(work.height)))
            scale = _target_scale(work.width, work.height, disp_w, disp_h, float(max_dpi))
            if scale < 0.99:
                new_w = max(1, int(work.width * scale))
                new_h = max(1, int(work.height * scale))
                if new_w < work.width or new_h < work.height:
                    work = fitz.Pixmap(work, new_w, new_h, None)
                    work = _pixmap_for_reencode(work, grayscale=False)

            quality = max(1, min(95, int(jpeg_quality)))
            try:
                jpeg_bytes = work.tobytes("jpeg", jpg_quality=quality)
            except Exception as exc:
                logger.debug("Skip image xref=%s jpeg encode failed: %s", xref, exc)
                continue

            # 용량 이득이 거의 없으면 유지 (품질 손실 방지)
            if original_len and len(jpeg_bytes) >= int(original_len * 0.98) and scale >= 0.99 and not grayscale:
                continue

            # 교체는 아무 페이지에서나 xref 기준으로 가능
            page0 = doc[0]
            page0.replace_image(xref, stream=jpeg_bytes)
            replaced += 1
        except Exception as exc:
            logger.debug("Skip image xref=%s optimize failed: %s", xref, exc)
        finally:
            if progress_cb is not None:
                progress_cb(page_count + idx + 1, page_count + total_xrefs)

    return replaced


def subset_document_fonts(doc: Any) -> bool:
    """사용 글리프만 남기도록 폰트 서브셋을 시도한다. 성공 여부 반환."""
    subset_fonts = getattr(doc, "subset_fonts", None)
    if not callable(subset_fonts):
        return False
    try:
        subset_fonts(verbose=False)
        return True
    except TypeError:
        # 구버전 시그니처 호환
        try:
            subset_fonts()
            return True
        except Exception as exc:
            logger.warning("Font subset failed: %s", exc)
            return False
    except Exception as exc:
        logger.warning("Font subset failed: %s", exc)
        return False
