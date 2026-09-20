"""시각(픽셀) diff 단계 + visual diff PDF 생성."""
from __future__ import annotations

import logging
from typing import Any

from ..._typing import WorkerHost
from ...optional_deps import fitz
from .helpers import draw_overlay_rect, pixel_diff_ratio, scale_rect

logger = logging.getLogger(__name__)


class WorkerCompareVisualMixin(WorkerHost):
    def _measure_visual_diff(
        self,
        page1: Any,
        page2: Any,
        *,
        page_number: int,
        visual_dpi: float,
        visual_threshold: float,
    ) -> tuple[float, bool, str | None]:
        """픽셀 diff 측정 → (ratio, 차이 여부, 에러 메시지|None)."""
        try:
            ratio = pixel_diff_ratio(page1, page2, visual_dpi=visual_dpi)
            return ratio, ratio > visual_threshold, None
        except Exception as exc:
            logger.warning("visual compare failed page %s: %s", page_number, exc)
            return 0.0, False, str(exc)[:160]

    def _write_visual_diff_pdf(
        self,
        diff_pages: list[dict[str, Any]],
        doc1: Any,
        doc2: Any,
        visual_diff_path: str,
    ) -> None:
        """양방향 블록 오버레이 + 범례가 있는 visual diff PDF 저장."""
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
                    draw_overlay_rect(new_page, canvas_rect, stroke=(0.1, 0.2, 0.8), fill=(0.7, 0.8, 1.0))
                elif page2 is None and page1 is not None:
                    draw_overlay_rect(new_page, canvas_rect, stroke=(0.9, 0.1, 0.1), fill=(1.0, 0.8, 0.8))
                else:
                    for block in diff_page["file1_only"]:
                        draw_overlay_rect(
                            new_page,
                            scale_rect(block["rect"], rect1, canvas_rect),
                            stroke=(0.9, 0.1, 0.1),
                            fill=(1.0, 0.8, 0.8),
                        )
                    for block in diff_page["file2_only"]:
                        draw_overlay_rect(
                            new_page,
                            scale_rect(block["rect"], rect2, canvas_rect),
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


__all__ = ["WorkerCompareVisualMixin"]
