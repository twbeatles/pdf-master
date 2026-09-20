"""WorkerCompareOpsMixin — compare 단계 오케스트레이션 facade.

실제 단계 구현은 `text_diff` / `visual_diff` / `report` 믹스인에 있다.
public surface (`compare_pdfs`, `_legacy_compare_pdfs`) 는 그대로 유지된다.
"""
from __future__ import annotations

import os
from typing import Any

from ...worker_runtime.args import (
    _as_bool,
    _as_float,
    _as_str,
)
from .report import WorkerCompareReportMixin
from .text_diff import WorkerCompareTextMixin
from .visual_diff import WorkerCompareVisualMixin


class WorkerCompareOpsMixin(
    WorkerCompareTextMixin,
    WorkerCompareVisualMixin,
    WorkerCompareReportMixin,
):
    def _legacy_compare_pdfs(self):
        file_path1 = _as_str(self.kwargs.get("file_path1"))
        file_path2 = _as_str(self.kwargs.get("file_path2"))
        output_path = _as_str(self.kwargs.get("output_path"))
        # text | visual | both — visual은 픽셀 비교로 스캔본 차이 탐지
        compare_mode = _as_str(self.kwargs.get("compare_mode"), "text").lower()
        if compare_mode not in {"text", "visual", "both"}:
            compare_mode = "text"
        do_text = compare_mode in {"text", "both"}
        do_visual = compare_mode in {"visual", "both"}
        generate_visual_diff = _as_bool(
            self.kwargs.get("generate_visual_diff"),
            default=do_visual,  # visual/both 모드는 기본으로 visual PDF 생성
        )
        visual_dpi = max(36.0, min(150.0, _as_float(self.kwargs.get("visual_dpi"), 72.0) or 72.0))
        visual_threshold = max(0.0, min(1.0, _as_float(self.kwargs.get("visual_threshold"), 0.02) or 0.02))

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

                text1 = _as_str(page1.get_text()) if do_text or do_visual else ""
                text2 = _as_str(page2.get_text()) if do_text or do_visual else ""
                text_same = text1 == text2

                visual_ratio = 0.0
                visual_diff = False
                visual_error: str | None = None
                if do_visual:
                    visual_ratio, visual_diff, visual_error = self._measure_visual_diff(
                        page1,
                        page2,
                        page_number=index + 1,
                        visual_dpi=visual_dpi,
                        visual_threshold=visual_threshold,
                    )

                if visual_error is not None:
                    results.append(
                        {
                            "page": index + 1,
                            "status": "visual_error",
                            "added": 0,
                            "deleted": 0,
                            "modified": 0,
                            "samples": [f"visual_error={visual_error}"],
                            "visual_ratio": 0.0,
                        }
                    )
                    continue

                if do_text and not do_visual and text_same:
                    continue
                if do_visual and not do_text and not visual_diff:
                    continue
                if do_text and do_visual and text_same and not visual_diff:
                    continue

                # 텍스트 동일 + 시각 차이만 있는 경우
                if text_same and visual_diff:
                    results.append(
                        {
                            "page": index + 1,
                            "status": "visual_diff",
                            "added": 0,
                            "deleted": 0,
                            "modified": 0,
                            "samples": [f"pixel_diff={visual_ratio:.3f}"],
                            "visual_ratio": visual_ratio,
                        }
                    )
                    # 전체 페이지 오버레이용 빈 블록 대신 페이지 전체 rect
                    full1 = [{"text": "", "rect": page1.rect}]
                    full2 = [{"text": "", "rect": page2.rect}]
                    diff_pages.append(
                        {
                            "page_index": index,
                            "page1": page1,
                            "page2": page2,
                            "file1_only": full1 if visual_diff else [],
                            "file2_only": full2 if visual_diff else [],
                        }
                    )
                    continue

                if do_text and text_same and not do_visual:
                    continue
                if do_text and text_same:
                    # both 모드에서 텍스트 같고 시각 차이 없으면 위에서 continue
                    continue

                text_stats = self._diff_page_texts(text1, text2)
                file1_only, file2_only = self._collect_page_diff_blocks(page1, page2)

                results.append(
                    {
                        "page": index + 1,
                        "status": "diff",
                        "added": text_stats["added"],
                        "deleted": text_stats["deleted"],
                        "modified": text_stats["modified"],
                        "samples": text_stats["samples"],
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
                self._write_visual_diff_pdf(diff_pages, doc1, doc2, visual_diff_path)

            report_lines = self._build_compare_report_lines(
                file_path1=file_path1,
                file_path2=file_path2,
                results=results,
                visual_diff_path=visual_diff_path,
            )
            self._atomic_text_save(output_path, "\n".join(report_lines))

            self._finish_compare(
                results=results,
                output_path=output_path,
                visual_diff_path=visual_diff_path,
            )
        finally:
            if doc1:
                doc1.close()
            if doc2:
                doc2.close()

    def compare_pdfs(self):
        """두 PDF 비교"""
        return self._legacy_compare_pdfs()


__all__ = ["WorkerCompareOpsMixin"]
