"""텍스트 diff 단계 (순수 라인 diff + 블록 수집)."""

from __future__ import annotations

import logging
from typing import Any

from ..._typing import WorkerHost
from ...worker_runtime.args import _as_str
from .._pdf_helpers import _sample_diff_text
from .helpers import collect_text_blocks, diff_blocks

logger = logging.getLogger(__name__)


class WorkerCompareTextMixin(WorkerHost):
    def _extract_page_texts(
        self, page1: Any, page2: Any, page_number: int
    ) -> tuple[str, str, str | None]:
        """페이지 텍스트 추출. 실패해도 중단하지 않고 ('', '', 에러) 반환."""
        try:
            return _as_str(page1.get_text()), _as_str(page2.get_text()), None
        except Exception as exc:
            logger.warning(
                "compare text extraction failed on page %s: %s",
                page_number,
                exc,
            )
            return "", "", (str(exc) or repr(exc))

    def _text_error_result(self, page: int, err: str) -> dict[str, Any]:
        """텍스트 경로 실패 페이지의 격리 결과 (`visual_error`와 동형)."""
        return {
            "page": page, "status": "text_error",
            "added": 0, "deleted": 0, "modified": 0,
            "samples": [f"text_error={err}"], "visual_ratio": 0.0,
        }

    def _compute_page_text_diff(
        self, page1: Any, page2: Any, text1: str, text2: str, page_number: int
    ) -> tuple[Any, list, list, str | None]:
        """라인 diff + 블록 수집. 실패 시 (None, [], [], 에러) 반환."""
        try:
            return (
                self._diff_page_texts(text1, text2),
                *self._collect_page_diff_blocks(page1, page2),
                None,
            )
        except Exception as exc:
            logger.warning(
                "compare diff blocks failed on page %s: %s", page_number, exc
            )
            return None, [], [], (str(exc) or repr(exc))
    def _diff_page_texts(self, text1: str, text2: str) -> dict[str, Any]:
        """두 페이지 텍스트의 라인 diff → added/deleted/modified/samples."""
        import difflib

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
        return {
            "added": added,
            "deleted": deleted,
            "modified": modified,
            "samples": samples,
        }

    def _collect_page_diff_blocks(
        self, page1: Any, page2: Any
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """양방향 블록 오버레이용 file1_only/file2_only."""
        file1_blocks = collect_text_blocks(page1)
        file2_blocks = collect_text_blocks(page2)
        return (
            diff_blocks(file1_blocks, file2_blocks),
            diff_blocks(file2_blocks, file1_blocks),
        )


__all__ = ["WorkerCompareTextMixin"]
