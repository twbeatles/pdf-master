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


class PreviewRegionInteractionMixin(PreviewWidgetHost):
    def is_region_select_mode(self) -> bool:
        return bool(self._region_select_mode)

    def set_region_select_mode(self, enabled: bool) -> None:
        """미리보기에서 드래그로 사각형 영역을 고르는 모드."""
        next_enabled = bool(enabled) and self._doc is not None and self._total_pages > 0
        if next_enabled and self._text_placement_mode:
            # 텍스트 배치 모드와 동시 사용 불가
            self.set_text_placement_mode(False)
        if self._region_select_mode == next_enabled and (
            self._region_overlay is None or self._region_overlay.is_active() == next_enabled
        ):
            return
        self._region_select_mode = next_enabled
        if self._region_overlay is not None:
            self._sync_region_overlay_geometry()
            self._region_overlay.set_active(next_enabled)
        self.regionSelectModeChanged.emit(next_enabled)

    def _sync_region_overlay_geometry(self) -> None:
        # pdf_view 전체 위에 덮음 (viewport 스크롤 포함 좌표계는 변환 시 보정)
        geo = self.pdf_view.rect()
        if self._region_overlay is not None:
            self._region_overlay.setGeometry(geo)
            if self._region_select_mode:
                self._region_overlay.raise_()
        if self._queue_ghost_overlay is not None:
            self._queue_ghost_overlay.setGeometry(geo)
            if self._queue_ghost_boxes:
                self._queue_ghost_overlay.raise_()
        if self._text_placement_overlay is not None:
            self._text_placement_overlay.setGeometry(geo)
            if self._text_placement_mode:
                self._text_placement_overlay.raise_()

    def _page_display_rect_in_view(self) -> QRectF | None:
        if self._doc is None or self._total_pages <= 0:
            return None
        page = max(0, min(self._current_page, self._total_pages - 1))
        try:
            page_size = self._doc.pagePointSize(page)
        except Exception:
            logger.debug("pagePointSize failed", exc_info=True)
            return None
        pw = float(page_size.width())
        ph = float(page_size.height())
        if pw <= 0 or ph <= 0:
            return None

        margins = self.pdf_view.documentMargins()
        hbar = self.pdf_view.horizontalScrollBar()
        vbar = self.pdf_view.verticalScrollBar()
        scroll_x = float(hbar.value()) if hbar is not None else 0.0
        scroll_y = float(vbar.value()) if vbar is not None else 0.0
        # 오버레이는 pdf_view 기준 — viewport 원점을 보정
        vp = self.pdf_view.viewport()
        if vp is not None:
            origin = vp.mapTo(self.pdf_view, vp.rect().topLeft())
            viewport = QRectF(origin.x(), origin.y(), vp.width(), vp.height())
        else:
            viewport = QRectF(self.pdf_view.rect())

        return compute_page_display_rect(
            viewport=viewport,
            page_width_pts=pw,
            page_height_pts=ph,
            zoom_factor=float(self.pdf_view.zoomFactor() or 1.0),
            margin_left=float(margins.left()),
            margin_top=float(margins.top()),
            margin_right=float(margins.right()),
            margin_bottom=float(margins.bottom()),
            scroll_x=scroll_x,
            scroll_y=scroll_y,
        )

    def _on_region_selection_finished(self, rect) -> None:
        if self._doc is None or not self._region_select_mode:
            return
        page_display = self._page_display_rect_in_view()
        if page_display is None:
            logger.warning("Could not resolve page display rect for region select")
            return
        page = max(0, min(self._current_page, self._total_pages - 1))
        try:
            page_size = self._doc.pagePointSize(page)
        except Exception:
            return
        selection = QRectF(rect)
        mapped = map_viewport_rect_to_page_points(
            selection,
            page_display,
            float(page_size.width()),
            float(page_size.height()),
        )
        if mapped is None:
            logger.info("Region selection too small or outside page")
            return
        # 선택 완료 후 모드 종료 (한 번 고르면 필드에 반영)
        self.set_region_select_mode(False)
        x0, y0, x1, y1 = mapped
        self.regionSelected.emit(page + 1, x0, y0, x1, y1)

    def _on_region_selection_cancelled(self) -> None:
        self.set_region_select_mode(False)
