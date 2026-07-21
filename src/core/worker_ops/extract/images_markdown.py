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


class WorkerExtractImagesMarkdownMixin(WorkerHost):
    def extract_images(self):
        """PDF에서 모든 이미지 추출"""
        import json
        file_path = _as_str(self.kwargs.get('file_path'))
        output_dir = _as_str(self.kwargs.get('output_dir'))
        include_info = _as_bool(self.kwargs.get('include_info'), True)  # v3.2: 상세 정보 포함
        deduplicate = _as_bool(self.kwargs.get('deduplicate'), True)  # v3.2: 중복 제거

        doc = self._open_pdf_document(file_path)
        image_count = 0
        image_info_list = []  # v3.2: 이미지 정보 목록
        seen_xrefs = set()  # v3.2: 중복 추적

        try:
            total_pages = len(doc)
            for page_num in range(len(doc)):
                page = doc[page_num]
                self._check_cancelled()  # 취소 체크포인트
                images = page.get_images()
                for img_idx, img in enumerate(images):
                    xref = img[0]

                    # v3.2: 중복 제거
                    if deduplicate and xref in seen_xrefs:
                        continue
                    seen_xrefs.add(xref)

                    try:
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]

                        image_path = os.path.join(output_dir, f"page{page_num + 1}_img{img_idx + 1}.{image_ext}")
                        self._atomic_binary_save(image_path, image_bytes)

                        # v3.2: 상세 정보 수집
                        if include_info:
                            info = {
                                "filename": os.path.basename(image_path),
                                "page": page_num + 1,
                                "xref": xref,
                                "width": base_image.get("width", 0),
                                "height": base_image.get("height", 0),
                                "colorspace": str(base_image.get("colorspace", "unknown")),
                                "bpc": base_image.get("bpc", 0),  # bits per component
                                "size_bytes": len(image_bytes),
                                "format": image_ext
                            }
                            image_info_list.append(info)

                        image_count += 1
                    except Exception as e:
                        logger.error(f"Image extraction error on page {page_num + 1}: {e}")

                self._emit_progress_if_due(int((page_num + 1) / total_pages * 100))

            # v3.2: 정보 파일 저장
            if include_info and image_info_list:
                info_path = os.path.join(output_dir, "_images_info.json")
                self._atomic_text_save(
                    info_path,
                    json.dumps(image_info_list, indent=2, ensure_ascii=False) + "\n",
                )

        finally:
            doc.close()
        dedup_msg = self._get_msg("msg_dedup_removed_suffix") if deduplicate else ""
        self.finished_signal.emit(self._get_msg("msg_images_extracted", dedup_msg, image_count))

    def extract_markdown(self):
        """PDF를 Markdown으로 추출"""
        file_path = _as_str(self.kwargs.get('file_path'))
        output_path = _as_str(self.kwargs.get('output_path'))
        markdown_mode = _as_str(self.kwargs.get('markdown_mode'), 'auto')
        if markdown_mode not in {'auto', 'native', 'text'}:
            markdown_mode = 'auto'
        include_front_matter = _as_bool(self.kwargs.get('include_front_matter'), False)
        include_page_markers = _as_bool(self.kwargs.get('include_page_markers'), True)
        include_asset_placeholders = _as_bool(self.kwargs.get('include_asset_placeholders'), False)

        doc = self._open_pdf_document(file_path)
        markdown_chunks: list[str] = []
        total_pages = 0

        try:
            total_pages = len(doc)
            if include_front_matter:
                markdown_chunks.append(_markdown_front_matter(file_path, doc))

            metadata = doc.metadata if isinstance(getattr(doc, "metadata", None), dict) else {}
            document_title = _as_str(metadata.get("title")) or os.path.basename(file_path)
            markdown_chunks.append(f"# {document_title}\n\n")

            for page_num in range(total_pages):
                page = doc[page_num]
                self._check_cancelled()

                if page_num > 0:
                    markdown_chunks.append("\n")
                if include_page_markers:
                    markdown_chunks.append(f"---\n\n## Page {page_num + 1}\n\n")
                if include_asset_placeholders:
                    placeholders = _page_asset_placeholders(page)
                    if placeholders:
                        markdown_chunks.append("\n".join(placeholders))
                        markdown_chunks.append("\n\n")

                if markdown_mode == 'text':
                    markdown_text = _fallback_markdown_from_text(page)
                else:
                    try:
                        markdown_text = _extract_page_markdown(page, markdown_mode)
                    except RuntimeError as exc:
                        self.error_signal.emit(str(exc))
                        return

                if markdown_text:
                    markdown_chunks.append(markdown_text)
                    markdown_chunks.append("\n\n")
                self._emit_progress_if_due(int((page_num + 1) / total_pages * 100))
        finally:
            doc.close()

        markdown_text = "".join(markdown_chunks)
        self._atomic_text_save(output_path, markdown_text)

        self.finished_signal.emit(self._get_msg("msg_markdown_extracted", total_pages))
