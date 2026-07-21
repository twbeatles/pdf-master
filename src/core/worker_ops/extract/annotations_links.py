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


class WorkerExtractAnnotationsLinksMixin(WorkerHost):
    def list_annotations(self):
        file_path = _as_str(self.kwargs.get("file_path"))
        output_path = _as_str(self.kwargs.get("output_path"))
        all_annots: list[dict[str, Any]] = []
        doc = None
        try:
            doc = self._open_pdf_document(file_path)
            total_pages = max(1, len(doc))
            for page_num in range(len(doc)):
                self._check_cancelled()
                page = doc[page_num]
                annots = page.annots()
                if annots:
                    for annot in annots:
                        annot_info = cast(dict[str, Any], annot.info or {})
                        all_annots.append(
                            {
                                "page": page_num + 1,
                                "type": annot.type[1] if annot.type else "Unknown",
                                "content": annot_info.get("content", ""),
                                "title": annot_info.get("title", ""),
                                "rect": [annot.rect.x0, annot.rect.y0, annot.rect.x1, annot.rect.y1],
                            }
                        )
                self._emit_progress_if_due(int((page_num + 1) / total_pages * 100))
        finally:
            if doc:
                doc.close()

        lines = [f"# 주석 목록: {os.path.basename(file_path)}", "", f"총 {len(all_annots)}개 주석", ""]
        for annot in all_annots:
            lines.append(f"## 페이지 {annot['page']} - {annot['type']}")
            if annot["title"]:
                lines.append(f"작성자: {annot['title']}")
            if annot["content"]:
                lines.append(f"내용: {annot['content']}")
            lines.append("")
        self._atomic_text_save(output_path, "\n".join(lines))
        self.kwargs["result_annotations"] = all_annots
        self._set_result_payload(annotations=all_annots)
        self.finished_signal.emit(self._get_msg("msg_annotations_extracted", len(all_annots)))

    def extract_links(self):
        """PDF에서 모든 링크 추출"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))

        doc = self._open_pdf_document(file_path)
        all_links = []
        try:
            total_pages = len(doc)
            for i in range(total_pages):
                page = doc[i]
                self._check_cancelled()  # 취소 체크포인트
                links = page.get_links()
                for link in links:
                    if 'uri' in link:
                        all_links.append({
                            'page': i + 1,
                            'url': link['uri']
                        })
                self._emit_progress_if_due(int((i + 1) / total_pages * 100))
        finally:
            doc.close()

        body = [f"# {os.path.basename(file_path)} - Link List", ""]
        body.extend(f"Page {link['page']}: {link['url']}" for link in all_links)
        self._atomic_text_save(output_path, "\n".join(body).rstrip() + "\n")

        self.finished_signal.emit(self._get_msg("msg_links_extracted", len(all_links)))
