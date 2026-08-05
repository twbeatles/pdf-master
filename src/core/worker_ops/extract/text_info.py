from __future__ import annotations
import csv
import io
import json
import logging
import os
from collections import Counter
from typing import Any, cast
from ..._typing import WorkerHost
from ...constants import (
    DEFAULT_PAGE_SIZE,
    PAGE_SIZES,
    WATERMARK_DEFAULTS,
    WATERMARK_TILE_SPACING_X,
    WATERMARK_TILE_SPACING_Y,
)
from ...optional_deps import fitz
from ...worker_runtime.args import (
    _as_bool,
    _as_dict,
    _as_float,
    _as_int,
    _as_list,
    _as_str,
)
from .._pdf_helpers import (
    _extract_page_markdown,
    _fallback_markdown_from_text,
    _markdown_front_matter,
    _normalize_stroke_points,
    _page_asset_placeholders,
    _sample_diff_text,
)
logger = logging.getLogger(__name__)


class WorkerExtractTextInfoMixin(WorkerHost):
    def extract_text(self):
        # 다중 파일 지원
        file_paths = [path for path in (_as_list(self.kwargs.get('file_paths')) or [_as_str(self.kwargs.get('file_path'))]) if isinstance(path, str) and path]
        output_path = _as_str(self.kwargs.get('output_path'))
        output_dir = _as_str(self.kwargs.get('output_dir'))
        include_details = _as_bool(self.kwargs.get('include_details'), False)  # v3.2: 상세 정보 포함 옵션
        use_ocr = _as_bool(self.kwargs.get("use_ocr"), False) or _as_bool(self.kwargs.get("ocr"), False)
        ocr_language = _as_str(self.kwargs.get("ocr_language"), "kor+eng") or "kor+eng"
        ocr_dpi = max(72, _as_int(self.kwargs.get("ocr_dpi"), 200))

        total_files = len(file_paths)
        used_output_stems: set[str] = set()
        ocr_success_pages = 0
        ocr_fail_pages = 0
        ocr_hard_fail: str | None = None
        pages_processed = 0

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        for file_idx, file_path in enumerate(file_paths):
            if not file_path or not os.path.exists(file_path):
                continue
            doc = None
            try:
                doc = self._open_pdf_document(file_path)
                text_chunks = []

                for i in range(len(doc)):
                    page = doc[i]
                    self._check_cancelled()  # 취소 체크포인트
                    text_chunks.append(f"\n--- Page {i+1} ---\n")
                    pages_processed += 1

                    if use_ocr:
                        try:
                            get_tp = getattr(page, "get_textpage_ocr", None)
                            if not callable(get_tp):
                                raise RuntimeError("page.get_textpage_ocr is not available in this PyMuPDF build")
                            tp = get_tp(dpi=ocr_dpi, language=ocr_language, full=True)
                            text_chunks.append(page.get_text("text", textpage=tp) or "")
                            ocr_success_pages += 1
                        except Exception as exc:
                            logger.warning("OCR failed page %s: %s", i + 1, exc, exc_info=True)
                            ocr_hard_fail = str(exc)
                            ocr_fail_pages += 1
                            # 네이티브 레이어 폴백
                            text_chunks.append(page.get_text() or "")
                    elif include_details:
                        # v3.2: 상세 정보 추출 (폰트, 크기, 색상)
                        text_dict = _as_dict(page.get_text("dict"))
                        blocks = cast(list[dict[str, Any]], text_dict.get("blocks", []))
                        for block in blocks:
                            if block.get("type") == 0:  # 텍스트 블록
                                for line in cast(list[dict[str, Any]], block.get("lines", [])):
                                    for span in cast(list[dict[str, Any]], line.get("spans", [])):
                                        text = span.get("text", "")
                                        font = span.get("font", "unknown")
                                        size = span.get("size", 0)
                                        color = span.get("color", 0)
                                        # RGB로 변환
                                        r = (color >> 16) & 0xFF
                                        g = (color >> 8) & 0xFF
                                        b = color & 0xFF
                                        text_chunks.append(
                                            f"[Font: {font}, Size: {size:.1f}pt, Color: RGB({r},{g},{b})] {text}\n"
                                        )
                    else:
                        text_chunks.append(page.get_text())
            finally:
                if doc:
                    doc.close()

            # 출력 경로 결정
            if output_dir:
                base = os.path.splitext(os.path.basename(file_path))[0]
                unique_stem = self._build_unique_output_stem(
                    output_dir,
                    base,
                    ".txt",
                    used_output_stems,
                )
                out_path = os.path.join(output_dir, f"{unique_stem}.txt")
            else:
                out_path = output_path

            full_text = "".join(text_chunks)
            self._atomic_text_save(out_path, full_text)

            self._emit_progress_if_due(int((file_idx + 1) / max(1, total_files) * 100))

        # OCR 요청인데 성공 페이지가 0이면 hard-fail (네이티브 폴백만 남은 경우 포함)
        if use_ocr and pages_processed > 0 and ocr_success_pages == 0:
            detail = ocr_hard_fail or "OCR produced no successful pages"
            self._update_result_payload(
                ocr=True,
                ocr_fallback=True,
                ocr_success_pages=0,
                ocr_fail_pages=ocr_fail_pages,
            )
            self.error_signal.emit(self._get_msg("err_ocr_unavailable", detail))
            return

        if use_ocr and ocr_success_pages > 0:
            # 부분 폴백이 있어도 결과 파일은 저장됨 — 경고 메타 포함
            self._update_result_payload(
                ocr=True,
                ocr_fallback=bool(ocr_fail_pages),
                ocr_success_pages=ocr_success_pages,
                ocr_fail_pages=ocr_fail_pages,
            )
            if ocr_fail_pages:
                self.finished_signal.emit(
                    self._get_msg(
                        "msg_ocr_extract_done_partial",
                        total_files,
                        ocr_fail_pages,
                        ocr_hard_fail or "",
                    )
                )
            else:
                self.finished_signal.emit(self._get_msg("msg_ocr_extract_done", total_files))
            return

        self.finished_signal.emit(
            self._get_msg(
                "msg_extract_text_done",
                total_files,
                self._get_msg("msg_extract_text_detail_suffix") if include_details else "",
            )
        )

    def get_pdf_info(self):
        total_chars = 0
        total_images = 0
        fonts_used: set[str] = set()
        page_count = 0
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        doc = None
        meta: dict[str, Any] = {}
        try:
            doc = self._open_pdf_document(file_path)
            page_count = len(doc)

            for i in range(page_count):
                self._check_cancelled()
                page = doc[i]
                total_chars += len(page.get_text())
                total_images += len(page.get_images())
                for font in page.get_fonts():
                    fonts_used.add(font[3] if len(font) > 3 else font[0])
                self._emit_progress_if_due(int((i + 1) / max(1, page_count) * 100))

            meta = cast(dict[str, Any], doc.metadata or {})
        finally:
            if doc:
                doc.close()

        font_list = ", ".join(sorted(fonts_used)) if fonts_used else self._get_msg("pdf_info_fonts_none")
        file_kb = os.path.getsize(file_path) / 1024
        lines = [
            self._get_msg("pdf_info_title", os.path.basename(file_path)),
            "",
            self._get_msg("pdf_info_section_basic"),
            self._get_msg("pdf_info_pages", page_count),
            self._get_msg("pdf_info_file_size_kb", f"{file_kb:.1f}"),
            self._get_msg("pdf_info_doc_title", meta.get("title") or "-"),
            self._get_msg("pdf_info_author", meta.get("author") or "-"),
            self._get_msg("pdf_info_created", meta.get("creationDate") or "-"),
            "",
            self._get_msg("pdf_info_section_stats"),
            self._get_msg("pdf_info_total_chars", f"{total_chars:,}"),
            self._get_msg("pdf_info_total_images", total_images),
            self._get_msg("pdf_info_fonts", font_list),
            "",
        ]
        self._atomic_text_save(output_path, "\n".join(lines))
        self.finished_signal.emit(self._get_msg("msg_pdf_info_done", page_count, total_chars, total_images))
