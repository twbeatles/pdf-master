from __future__ import annotations

import csv
import io
import json
import logging
import os
from collections import Counter
from typing import Any, cast

from .._typing import WorkerHost
from ..constants import (
    DEFAULT_PAGE_SIZE,
    WATERMARK_DEFAULTS,
    WATERMARK_TILE_SPACING_X,
    WATERMARK_TILE_SPACING_Y,
)
from ..optional_deps import fitz
from ..worker_runtime.args import (
    _as_bool,
    _as_dict,
    _as_float,
    _as_int,
    _as_list,
    _as_str,
)
from ._pdf_helpers import (
    _extract_page_markdown,
    _fallback_markdown_from_text,
    _markdown_front_matter,
    _normalize_stroke_points,
    _page_asset_placeholders,
    _sample_diff_text,
)

logger = logging.getLogger(__name__)


class WorkerCompareOpsMixin(WorkerHost):
    def _legacy_compare_pdfs(self):
        import difflib

        def _normalize_block_text(text: Any) -> str:
            return " ".join(str(text or "").split()).casefold()

        def _collect_text_blocks(page: Any) -> list[dict[str, Any]]:
            blocks: list[dict[str, Any]] = []
            for block in page.get_text("blocks"):
                if len(block) < 7 or block[6] != 0:
                    continue
                normalized = _normalize_block_text(block[4])
                if not normalized:
                    continue
                blocks.append({"text": normalized, "rect": fitz.Rect(block[:4])})
            return blocks

        def _diff_blocks(source_blocks: list[dict[str, Any]], target_blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
            source_counter = Counter(block["text"] for block in source_blocks)
            target_counter = Counter(block["text"] for block in target_blocks)
            remaining = source_counter - target_counter
            consumed: Counter[str] = Counter()
            diff_blocks: list[dict[str, Any]] = []
            for block in source_blocks:
                key = block["text"]
                if remaining[key] <= consumed[key]:
                    continue
                consumed[key] += 1
                diff_blocks.append(block)
            return diff_blocks

        def _scale_rect(rect: Any, source_rect: Any, canvas_rect: Any) -> Any:
            width_scale = canvas_rect.width / source_rect.width if source_rect.width else 1.0
            height_scale = canvas_rect.height / source_rect.height if source_rect.height else 1.0
            return fitz.Rect(
                rect.x0 * width_scale,
                rect.y0 * height_scale,
                rect.x1 * width_scale,
                rect.y1 * height_scale,
            )

        def _draw_overlay_rect(page: Any, rect: Any, *, stroke: tuple[float, float, float], fill: tuple[float, float, float]):
            page.draw_rect(rect, color=stroke, width=1.5)
            shape = page.new_shape()
            shape.draw_rect(rect)
            shape.finish(color=stroke, fill=fill, fill_opacity=0.25)
            shape.commit()

        file_path1 = _as_str(self.kwargs.get("file_path1"))
        file_path2 = _as_str(self.kwargs.get("file_path2"))
        output_path = _as_str(self.kwargs.get("output_path"))
        generate_visual_diff = _as_bool(self.kwargs.get("generate_visual_diff"), False)

        doc1 = None
        doc2 = None
        try:
            doc1 = self._open_pdf_document(file_path1)
            doc2 = self._open_pdf_document(file_path2)

            results: list[dict[str, Any]] = []
            diff_pages: list[dict[str, Any]] = []
            max_pages = max(len(doc1), len(doc2))

            for index in range(max_pages):
                self._check_cancelled()
                self._emit_progress_if_due(int((index + 1) / max(1, max_pages) * 100))

                page1 = doc1[index] if index < len(doc1) else None
                page2 = doc2[index] if index < len(doc2) else None
                if page1 is None:
                    results.append({"page": index + 1, "status": "missing_file1"})
                    diff_pages.append({"page_index": index, "page1": None, "page2": page2, "file1_only": [], "file2_only": []})
                    continue
                if page2 is None:
                    results.append({"page": index + 1, "status": "missing_file2"})
                    diff_pages.append({"page_index": index, "page1": page1, "page2": None, "file1_only": [], "file2_only": []})
                    continue

                text1 = _as_str(page1.get_text())
                text2 = _as_str(page2.get_text())
                if text1 == text2:
                    continue

                lines1 = text1.splitlines()
                lines2 = text2.splitlines()
                matcher = difflib.SequenceMatcher(a=lines1, b=lines2)
                added = 0
                deleted = 0
                modified = 0
                samples: list[str] = []
                first_added_text = ""
                first_deleted_text = ""

                for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                    if tag == "equal":
                        continue
                    if tag == "insert":
                        added += j2 - j1
                        if not first_added_text:
                            first_added_text = _sample_diff_text(lines2[j1:j2])
                    elif tag == "delete":
                        deleted += i2 - i1
                        if not first_deleted_text:
                            first_deleted_text = _sample_diff_text(lines1[i1:i2])
                    elif tag == "replace":
                        modified += max(i2 - i1, j2 - j1)
                        if len(samples) < 3:
                            before = _sample_diff_text(lines1[i1:i2], 2)
                            after = _sample_diff_text(lines2[j1:j2], 2)
                            paired_sample = f"~ {before} -> {after}"
                            if paired_sample not in samples:
                                samples.append(paired_sample)

                before_page_sample = _sample_diff_text(lines1, 2)
                after_page_sample = _sample_diff_text(lines2, 2)
                if before_page_sample != after_page_sample:
                    page_sample = f"~ {before_page_sample} -> {after_page_sample}"
                    if page_sample not in samples:
                        samples.insert(0, page_sample)
                        samples = samples[:3]

                if first_added_text and len(samples) < 3:
                    samples.append(f"+ {first_added_text}")
                if first_deleted_text and len(samples) < 3:
                    samples.append(f"- {first_deleted_text}")

                file1_blocks = _collect_text_blocks(page1)
                file2_blocks = _collect_text_blocks(page2)
                file1_only = _diff_blocks(file1_blocks, file2_blocks)
                file2_only = _diff_blocks(file2_blocks, file1_blocks)

                results.append(
                    {
                        "page": index + 1,
                        "status": "diff",
                        "added": added,
                        "deleted": deleted,
                        "modified": modified,
                        "samples": samples,
                    }
                )
                diff_pages.append(
                    {
                        "page_index": index,
                        "page1": page1,
                        "page2": page2,
                        "file1_only": file1_only,
                        "file2_only": file2_only,
                    }
                )

            visual_diff_path = None
            if generate_visual_diff and diff_pages:
                base_output_path, _ext = os.path.splitext(output_path)
                visual_diff_path = f"{base_output_path}_visual_diff.pdf"
                diff_doc = fitz.open()
                try:
                    for diff_page in diff_pages:
                        page1 = diff_page["page1"]
                        page2 = diff_page["page2"]
                        rect1 = page1.rect if page1 is not None else None
                        rect2 = page2.rect if page2 is not None else None
                        canvas_width = max(rect1.width if rect1 else 0, rect2.width if rect2 else 0, 1)
                        canvas_height = max(rect1.height if rect1 else 0, rect2.height if rect2 else 0, 1)
                        new_page = diff_doc.new_page(width=canvas_width, height=canvas_height)
                        canvas_rect = new_page.rect

                        if page1 is not None:
                            new_page.show_pdf_page(canvas_rect, doc1, diff_page["page_index"])
                        elif page2 is not None:
                            new_page.show_pdf_page(canvas_rect, doc2, diff_page["page_index"])

                        if page1 is None and page2 is not None:
                            _draw_overlay_rect(new_page, canvas_rect, stroke=(0.1, 0.2, 0.8), fill=(0.7, 0.8, 1.0))
                        elif page2 is None and page1 is not None:
                            _draw_overlay_rect(new_page, canvas_rect, stroke=(0.9, 0.1, 0.1), fill=(1.0, 0.8, 0.8))
                        else:
                            for block in diff_page["file1_only"]:
                                _draw_overlay_rect(
                                    new_page,
                                    _scale_rect(block["rect"], rect1, canvas_rect),
                                    stroke=(0.9, 0.1, 0.1),
                                    fill=(1.0, 0.8, 0.8),
                                )
                            for block in diff_page["file2_only"]:
                                _draw_overlay_rect(
                                    new_page,
                                    _scale_rect(block["rect"], rect2, canvas_rect),
                                    stroke=(0.1, 0.2, 0.8),
                                    fill=(0.7, 0.8, 1.0),
                                )

                        legend_rect = fitz.Rect(18, 18, min(canvas_width - 18, 280), min(canvas_height - 18, 72))
                        new_page.draw_rect(legend_rect, color=(0.3, 0.3, 0.3), fill=(1, 1, 1), fill_opacity=0.85)
                        new_page.insert_text(
                            fitz.Point(26, 36),
                            self._get_msg("visual_diff_legend_removed"),
                            fontsize=9,
                            color=(0.9, 0.1, 0.1),
                        )
                        new_page.insert_text(
                            fitz.Point(26, 54),
                            self._get_msg("visual_diff_legend_added"),
                            fontsize=9,
                            color=(0.1, 0.2, 0.8),
                        )
                    self._atomic_pdf_save(diff_doc, visual_diff_path)
                finally:
                    diff_doc.close()

            report_lines = ["# PDF 비교 결과", "", f"파일1: {os.path.basename(file_path1)}", f"파일2: {os.path.basename(file_path2)}", ""]
            if results:
                for result in results:
                    page_number = result["page"]
                    status = result["status"]
                    report_lines.append(f"## 페이지 {page_number}")
                    if status == "missing_file1":
                        report_lines.append("- 파일1에 해당 페이지가 없습니다.")
                    elif status == "missing_file2":
                        report_lines.append("- 파일2에 해당 페이지가 없습니다.")
                    else:
                        report_lines.append(f"- 추가: {result['added']}줄")
                        report_lines.append(f"- 삭제: {result['deleted']}줄")
                        report_lines.append(f"- 변경: {result['modified']}줄")
                        for sample in result.get("samples", []):
                            report_lines.append(f"- 예시: {sample}")
                    report_lines.append("")
            else:
                report_lines.append("두 파일의 텍스트 내용이 동일합니다.")
            if visual_diff_path:
                report_lines.extend(["", f"- 시각 비교 PDF: {os.path.basename(visual_diff_path)}"])
            report_lines.append("")
            self._atomic_text_save(output_path, "\n".join(report_lines))

            diff_count = sum(1 for result in results if result["status"] != "same")
            self._set_result_payload(
                diff_count=diff_count,
                results=results,
                report_path=output_path,
                visual_diff_path=visual_diff_path or "",
            )
            self.finished_signal.emit(
                self._get_msg(
                    "msg_compare_pdfs_done",
                    diff_count,
                    self._get_msg("msg_compare_pdfs_visual_diff_suffix") if visual_diff_path else "",
                )
            )
        finally:
            if doc1:
                doc1.close()
            if doc2:
                doc2.close()

    def compare_pdfs(self):
        """두 PDF 비교"""
        return self._legacy_compare_pdfs()
