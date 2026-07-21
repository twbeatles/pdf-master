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

        total_files = len(file_paths)
        used_output_stems: set[str] = set()

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

                    if include_details:
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

        lines = [
            f"# PDF 정보: {os.path.basename(file_path)}",
            "",
            "## 기본 정보",
            f"- 페이지 수: {page_count}",
            f"- 파일 크기: {os.path.getsize(file_path) / 1024:.1f} KB",
            f"- 제목: {meta.get('title', '-')}",
            f"- 작성자: {meta.get('author', '-')}",
            f"- 생성일: {meta.get('creationDate', '-')}",
            "",
            "## 통계",
            f"- 총 글자 수: {total_chars:,}",
            f"- 총 이미지 수: {total_images}",
            f"- 사용 폰트: {', '.join(sorted(fonts_used)) if fonts_used else '없음'}",
            "",
        ]
        self._atomic_text_save(output_path, "\n".join(lines))
        self.finished_signal.emit(self._get_msg("msg_pdf_info_done", page_count, total_chars, total_images))
