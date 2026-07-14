"""페이지 정리·분할·위생·자동 목차 등 의존성 없는 유틸 작업."""

from __future__ import annotations

import hashlib
import logging
import os
import re
from collections import Counter
from typing import Any, cast

from .._typing import WorkerHost
from ..optional_deps import fitz
from ..worker_runtime.args import (
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
        return True


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


def _collect_heading_toc(doc: Any, *, min_size: float = _HEADING_MIN_SIZE) -> list[list[Any]]:
    """폰트 크기 휴리스틱으로 목차 후보 생성."""
    size_counter: Counter[float] = Counter()
    candidates: list[tuple[int, float, str]] = []

    for page_index in range(len(doc)):
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


class WorkerCleanupOpsMixin(WorkerHost):
    def split_by_bookmarks(self):
        """북마크(목차) 기준으로 PDF 분할."""
        file_path = _as_str(self.kwargs.get("file_path"))
        output_dir = _as_str(self.kwargs.get("output_dir"))
        max_level = _as_int(self.kwargs.get("max_level"), 1)

        doc = self._open_pdf_document(file_path)
        try:
            toc = cast(list[list[Any]], doc.get_toc(simple=True) or [])
            # [level, title, page] 1-based page
            entries = [
                (int(item[0]), str(item[1]).strip(), int(item[2]))
                for item in toc
                if isinstance(item, (list, tuple)) and len(item) >= 3
            ]
            entries = [e for e in entries if e[0] <= max(1, max_level) and e[1] and e[2] >= 1]
            if not entries:
                self.error_signal.emit(self._get_msg("err_no_bookmarks_to_split"))
                return

            page_count = len(doc)
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            os.makedirs(output_dir, exist_ok=True)
            used_stems: set[str] = set()
            created = 0

            for idx, (_level, title, start_page) in enumerate(entries):
                self._check_cancelled()
                start = max(1, min(start_page, page_count))
                if idx + 1 < len(entries):
                    next_start = max(1, min(entries[idx + 1][2], page_count + 1))
                    end = max(start, next_start - 1)
                else:
                    end = page_count
                if end < start:
                    continue

                safe_title = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", title).strip(" .") or f"part_{idx + 1}"
                safe_title = safe_title[:60]
                stem = self._build_unique_output_stem(
                    output_dir,
                    f"{base_name}_{idx + 1:02d}_{safe_title}",
                    ".pdf",
                    used_stems,
                )
                out_path = os.path.join(output_dir, f"{stem}.pdf")
                part = fitz.open()
                try:
                    part.insert_pdf(doc, from_page=start - 1, to_page=end - 1)
                    self._atomic_pdf_save(part, out_path)
                finally:
                    part.close()
                created += 1
                self._emit_progress_if_due(int((idx + 1) / max(1, len(entries)) * 100))

            if created == 0:
                self.error_signal.emit(self._get_msg("err_split_no_valid_ranges"))
                return
            self.finished_signal.emit(self._get_msg("msg_split_by_bookmarks_done", created))
        finally:
            doc.close()

    def remove_blank_pages(self):
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))

        doc = self._open_pdf_document(file_path)
        try:
            keep: list[int] = []
            total = len(doc)
            if total == 0:
                self.error_signal.emit(self._get_msg("err_pdf_has_no_pages"))
                return
            for i in range(total):
                self._check_cancelled()
                page = doc[i]
                if not _is_blank_page(page):
                    keep.append(i)
                self._emit_progress_if_due(int((i + 1) / total * 80))

            if not keep:
                self.error_signal.emit(self._get_msg("err_all_pages_blank"))
                return
            if len(keep) == total:
                # 변경 없음: 그래도 사본 저장
                self._atomic_pdf_save(doc, output_path)
                self._emit_progress_if_due(100)
                self.finished_signal.emit(self._get_msg("msg_remove_blank_none"))
                return

            out = fitz.open()
            try:
                for idx, page_index in enumerate(keep):
                    self._check_cancelled()
                    out.insert_pdf(doc, from_page=page_index, to_page=page_index)
                    self._emit_progress_if_due(80 + int((idx + 1) / len(keep) * 20))
                self._atomic_pdf_save(out, output_path)
            finally:
                out.close()

            removed = total - len(keep)
            self.finished_signal.emit(self._get_msg("msg_remove_blank_done", removed, len(keep)))
        finally:
            doc.close()

    def dedupe_pages(self):
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))

        doc = self._open_pdf_document(file_path)
        try:
            total = len(doc)
            if total == 0:
                self.error_signal.emit(self._get_msg("err_pdf_has_no_pages"))
                return
            seen: set[str] = set()
            keep: list[int] = []
            for i in range(total):
                self._check_cancelled()
                sig = _page_signature(doc[i])
                if sig in seen:
                    self._emit_progress_if_due(int((i + 1) / total * 80))
                    continue
                seen.add(sig)
                keep.append(i)
                self._emit_progress_if_due(int((i + 1) / total * 80))

            if len(keep) == total:
                self._atomic_pdf_save(doc, output_path)
                self.finished_signal.emit(self._get_msg("msg_dedupe_pages_none"))
                return

            out = fitz.open()
            try:
                for idx, page_index in enumerate(keep):
                    self._check_cancelled()
                    out.insert_pdf(doc, from_page=page_index, to_page=page_index)
                    self._emit_progress_if_due(80 + int((idx + 1) / len(keep) * 20))
                self._atomic_pdf_save(out, output_path)
            finally:
                out.close()
            self.finished_signal.emit(
                self._get_msg("msg_dedupe_pages_done", total - len(keep), len(keep))
            )
        finally:
            doc.close()

    def auto_bookmarks(self):
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        min_size = _as_float(self.kwargs.get("min_heading_size"), _HEADING_MIN_SIZE)

        doc = self._open_pdf_document(file_path)
        try:
            toc = _collect_heading_toc(doc, min_size=min_size or _HEADING_MIN_SIZE)
            if not toc:
                self.error_signal.emit(self._get_msg("err_no_headings_for_bookmarks"))
                return
            self._check_cancelled()
            doc.set_toc(toc)
            self._atomic_pdf_save(doc, output_path)
            self._emit_progress_if_due(100)
            self.finished_signal.emit(self._get_msg("msg_auto_bookmarks_done", len(toc)))
        finally:
            doc.close()

    def sanitize_pdf(self):
        """메타데이터·첨부·(옵션) 주석 제거 후 클린 저장."""
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        remove_annotations = _as_bool(self.kwargs.get("remove_annotations"), True)
        remove_attachments = _as_bool(self.kwargs.get("remove_attachments"), True)
        remove_links = _as_bool(self.kwargs.get("remove_links"), False)
        remove_bookmarks = _as_bool(self.kwargs.get("remove_bookmarks"), False)

        doc = self._open_pdf_document(file_path)
        try:
            total = max(1, len(doc))
            # 메타데이터 비우기
            empty_meta = {
                "title": "",
                "author": "",
                "subject": "",
                "keywords": "",
                "creator": "",
                "producer": "",
            }
            try:
                doc.set_metadata(empty_meta)
            except Exception as exc:
                logger.debug("metadata scrub failed: %s", exc)

            # XML metadata
            try:
                if hasattr(doc, "del_xml_metadata"):
                    doc.del_xml_metadata()
                elif hasattr(doc, "set_xml_metadata"):
                    doc.set_xml_metadata("")
            except Exception as exc:
                logger.debug("xml metadata scrub failed: %s", exc)

            if remove_bookmarks:
                try:
                    doc.set_toc([])
                except Exception:
                    pass

            if remove_attachments:
                try:
                    names = list(doc.embfile_names() or [])
                    for name in names:
                        try:
                            doc.embfile_del(name)
                        except Exception:
                            logger.debug("attachment delete failed: %s", name)
                except Exception:
                    pass

            for page_index in range(len(doc)):
                self._check_cancelled()
                page = doc[page_index]
                if remove_annotations:
                    annot = page.first_annot
                    while annot:
                        next_annot = annot.next
                        try:
                            page.delete_annot(annot)
                        except Exception:
                            pass
                        annot = next_annot
                if remove_links:
                    try:
                        links = page.get_links() or []
                        for link in links:
                            try:
                                page.delete_link(link)
                            except Exception:
                                pass
                    except Exception:
                        pass
                self._emit_progress_if_due(int((page_index + 1) / total * 90))

            # open action / JS 가능한 경우 제거
            try:
                if hasattr(doc, "set_open_action"):
                    doc.set_open_action(None)  # type: ignore[arg-type]
            except Exception:
                pass

            self._atomic_pdf_save(doc, output_path, save_profile="compact")
            self._emit_progress_if_due(100)
            self.finished_signal.emit(self._get_msg("msg_sanitize_done"))
        finally:
            doc.close()

    def impose_nup(self):
        """N-up 임포지션 (2 또는 4)."""
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        nup = _as_int(self.kwargs.get("nup"), 2)
        if nup not in (2, 4):
            nup = 2

        doc = self._open_pdf_document(file_path)
        out = fitz.open()
        try:
            total = len(doc)
            if total == 0:
                self.error_signal.emit(self._get_msg("err_pdf_has_no_pages"))
                return

            # 첫 페이지 크기 기준
            src_rect = doc[0].rect
            if nup == 2:
                cols, rows = 2, 1
                sheet_w = src_rect.width * 2
                sheet_h = src_rect.height
            else:
                cols, rows = 2, 2
                sheet_w = src_rect.width * 2
                sheet_h = src_rect.height * 2

            per_sheet = cols * rows
            sheet_count = (total + per_sheet - 1) // per_sheet

            for sheet_idx in range(sheet_count):
                self._check_cancelled()
                new_page = out.new_page(width=sheet_w, height=sheet_h)
                for slot in range(per_sheet):
                    page_index = sheet_idx * per_sheet + slot
                    if page_index >= total:
                        break
                    col = slot % cols
                    row = slot // cols
                    target = fitz.Rect(
                        col * src_rect.width,
                        row * src_rect.height,
                        (col + 1) * src_rect.width,
                        (row + 1) * src_rect.height,
                    )
                    # 원본 페이지 비율 유지 fit
                    page = doc[page_index]
                    pr = page.rect
                    scale = min(target.width / max(pr.width, 1), target.height / max(pr.height, 1))
                    rw, rh = pr.width * scale, pr.height * scale
                    ox = target.x0 + (target.width - rw) / 2
                    oy = target.y0 + (target.height - rh) / 2
                    fit = fitz.Rect(ox, oy, ox + rw, oy + rh)
                    new_page.show_pdf_page(fit, doc, page_index)
                self._emit_progress_if_due(int((sheet_idx + 1) / sheet_count * 100))

            self._atomic_pdf_save(out, output_path)
            self.finished_signal.emit(self._get_msg("msg_impose_nup_done", nup, sheet_count))
        finally:
            out.close()
            doc.close()
