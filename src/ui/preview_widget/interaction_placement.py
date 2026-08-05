from __future__ import annotations

from .._typing import PreviewWidgetHost
import logging
from PyQt6.QtCore import QEvent, QModelIndex, QPointF, QRect, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QColor
from PyQt6.QtPdf import QPdfBookmarkModel, QPdfDocument, QPdfSearchModel
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QTreeView,
    QVBoxLayout,
    QWidget,
)
from ...core.i18n import tm
logger = logging.getLogger(__name__)
from .region_select import (
    RegionSelectOverlay,
    compute_page_display_rect,
    format_rect_coords,
    map_page_points_to_viewport_rect,
    map_viewport_rect_to_page_points,
)
from .queue_overlay import QueueGhostOverlay
from .search import PreviewSearchLineEdit
from .text_placement import TextPlacementOverlay


class PreviewPlacementInteractionMixin(PreviewWidgetHost):
    def is_text_placement_mode(self) -> bool:
        return bool(self._text_placement_mode)

    def set_text_placement_mode(
        self,
        enabled: bool,
        *,
        text: str = "",
        rect_pts: tuple[float, float, float, float] | list[float] | None = None,
        color: tuple[float, float, float] | list[float] | None = None,
        fontsize: float = 14.0,
        align: int = 0,
        opacity: float = 1.0,
    ) -> None:
        """미리보기에 텍스트 상자를 표시하고 드래그·리사이즈로 배치를 조정한다."""
        next_enabled = bool(enabled) and self._doc is not None and self._total_pages > 0
        if next_enabled and self._region_select_mode:
            self.set_region_select_mode(False)

        if next_enabled:
            self._text_placement_text = text or self._text_placement_text or " "
            if rect_pts is not None and len(rect_pts) >= 4:
                self._text_placement_pts = (
                    float(rect_pts[0]),
                    float(rect_pts[1]),
                    float(rect_pts[2]),
                    float(rect_pts[3]),
                )
            elif self._text_placement_pts is None:
                self._text_placement_pts = (100.0, 100.0, 300.0, 150.0)
            if color is not None and len(color) >= 3:
                r, g, b = float(color[0]), float(color[1]), float(color[2])
                self._text_placement_color = QColor(
                    int(max(0, min(255, r * 255))),
                    int(max(0, min(255, g * 255))),
                    int(max(0, min(255, b * 255))),
                )
            self._text_placement_fontsize = max(6.0, float(fontsize))
            self._text_placement_align = max(0, min(2, int(align)))
            self._text_placement_opacity = max(0.1, min(1.0, float(opacity)))

        was = self._text_placement_mode
        self._text_placement_mode = next_enabled
        if self._text_placement_overlay is not None:
            self._sync_region_overlay_geometry()
            if next_enabled:
                self._refresh_text_placement_overlay()
                self._text_placement_overlay.set_active(True)
            else:
                self._text_placement_overlay.set_active(False)
        if was != next_enabled:
            self.textPlacementModeChanged.emit(next_enabled)

    def update_text_placement_content(
        self,
        *,
        text: str | None = None,
        rect_pts: tuple[float, float, float, float] | list[float] | None = None,
        color: tuple[float, float, float] | list[float] | None = None,
        fontsize: float | None = None,
        align: int | None = None,
        opacity: float | None = None,
    ) -> None:
        """배치 모드 중 텍스트/스타일/좌표를 갱신한다."""
        if text is not None:
            self._text_placement_text = text
        if rect_pts is not None and len(rect_pts) >= 4:
            self._text_placement_pts = (
                float(rect_pts[0]),
                float(rect_pts[1]),
                float(rect_pts[2]),
                float(rect_pts[3]),
            )
        if color is not None and len(color) >= 3:
            r, g, b = float(color[0]), float(color[1]), float(color[2])
            self._text_placement_color = QColor(
                int(max(0, min(255, r * 255))),
                int(max(0, min(255, g * 255))),
                int(max(0, min(255, b * 255))),
            )
        if fontsize is not None:
            self._text_placement_fontsize = max(6.0, float(fontsize))
        if align is not None:
            self._text_placement_align = max(0, min(2, int(align)))
        if opacity is not None:
            self._text_placement_opacity = max(0.1, min(1.0, float(opacity)))
        if self._text_placement_mode:
            self._refresh_text_placement_overlay()

    def eventFilter(self, a0, a1):  # type: ignore[no-untyped-def]
        if a1 is not None and a1.type() == QEvent.Type.Resize:
            if a0 is self.pdf_view or a0 is self.pdf_view.viewport():
                self._sync_region_overlay_geometry()
                if self._text_placement_mode:
                    self._refresh_text_placement_overlay()
                if self._queue_ghost_boxes:
                    self._refresh_queue_ghost_overlay()
        return super().eventFilter(a0, a1)

    def _refresh_text_placement_overlay(self) -> None:
        if self._text_placement_overlay is None or not self._text_placement_mode:
            return
        pts = self._text_placement_pts
        if pts is None:
            return
        page_display = self._page_display_rect_in_view()
        if page_display is None or self._doc is None:
            return
        page = max(0, min(self._current_page, self._total_pages - 1))
        try:
            page_size = self._doc.pagePointSize(page)
        except Exception:
            return
        view_rect = map_page_points_to_viewport_rect(
            pts[0],
            pts[1],
            pts[2],
            pts[3],
            page_display,
            float(page_size.width()),
            float(page_size.height()),
        )
        if view_rect is None:
            return
        zoom = float(self.pdf_view.zoomFactor() or 1.0)
        font_px = max(8, int(round(self._text_placement_fontsize * zoom)))
        # 화면 픽셀 기준 최소 크기 (PDF 포인트 최소와 대략 정합)
        min_h_pts = max(14.0, float(self._text_placement_fontsize) * 1.4 + 4.0)
        min_w_pts = max(40.0, float(self._text_placement_fontsize) * 2.0)
        min_h_px = max(18, int(round(min_h_pts * zoom)))
        min_w_px = max(24, int(round(min_w_pts * zoom)))
        box = QRect(
            int(round(view_rect.x())),
            int(round(view_rect.y())),
            max(min_w_px, int(round(view_rect.width()))),
            max(min_h_px, int(round(view_rect.height()))),
        )
        self._text_placement_overlay.set_content(
            text=self._text_placement_text,
            box=box,
            color=self._text_placement_color,
            font_px=font_px,
            align=self._text_placement_align,
            opacity=self._text_placement_opacity,
            min_w=min_w_px,
            min_h=min_h_px,
        )

    def _on_text_placement_box_moved(self, box: QRect) -> None:
        if self._doc is None or not self._text_placement_mode:
            return
        page_display = self._page_display_rect_in_view()
        if page_display is None:
            return
        page = max(0, min(self._current_page, self._total_pages - 1))
        try:
            page_size = self._doc.pagePointSize(page)
        except Exception:
            return
        mapped = map_viewport_rect_to_page_points(
            QRectF(box),
            page_display,
            float(page_size.width()),
            float(page_size.height()),
            min_size_pts=1.0,
        )
        if mapped is None:
            return
        self._text_placement_pts = mapped
        self.textPlacementMoved.emit(page + 1, mapped[0], mapped[1], mapped[2], mapped[3])

    def _on_text_placement_cancelled(self) -> None:
        self.set_text_placement_mode(False)

    def _on_text_placement_text_edited(self, text: str) -> None:
        self._text_placement_text = text or ""
        self.textPlacementTextEdited.emit(self._text_placement_text)
