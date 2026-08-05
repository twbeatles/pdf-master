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


class PreviewQueueGhostMixin(PreviewWidgetHost):
    def set_queue_ghost_boxes(self, boxes: list[dict] | None) -> None:
        """큐 항목 목록(dict: page_num 0-based, rect[4], text)을 고스트로 표시."""
        self._queue_ghost_boxes = list(boxes or [])
        self._sync_region_overlay_geometry()
        self._refresh_queue_ghost_overlay()

    def clear_queue_ghost_boxes(self) -> None:
        self._queue_ghost_boxes = []
        if self._queue_ghost_overlay is not None:
            self._queue_ghost_overlay.clear()

    def _refresh_queue_ghost_overlay(self) -> None:
        if self._queue_ghost_overlay is None:
            return
        if self._doc is None or not self._queue_ghost_boxes:
            self._queue_ghost_overlay.clear()
            return
        page_display = self._page_display_rect_in_view()
        if page_display is None:
            self._queue_ghost_overlay.clear()
            return
        page = max(0, min(self._current_page, self._total_pages - 1))
        try:
            page_size = self._doc.pagePointSize(page)
        except Exception:
            self._queue_ghost_overlay.clear()
            return
        pw = float(page_size.width())
        ph = float(page_size.height())
        items: list[tuple[QRect, str]] = []
        for idx, box in enumerate(self._queue_ghost_boxes, start=1):
            try:
                pn = int(box.get("page_num", -1))
            except (TypeError, ValueError):
                continue
            if pn != page:
                continue
            rect = box.get("rect")
            if not isinstance(rect, (list, tuple)) or len(rect) < 4:
                continue
            view_rect = map_page_points_to_viewport_rect(
                float(rect[0]),
                float(rect[1]),
                float(rect[2]),
                float(rect[3]),
                page_display,
                pw,
                ph,
            )
            if view_rect is None:
                continue
            qr = QRect(
                int(round(view_rect.x())),
                int(round(view_rect.y())),
                max(8, int(round(view_rect.width()))),
                max(8, int(round(view_rect.height()))),
            )
            raw = str(box.get("text", "") or "").replace("\n", " ").strip()
            label = f"#{idx} {raw[:24]}" if raw else f"#{idx}"
            items.append((qr, label))
        self._queue_ghost_overlay.set_items(items)
