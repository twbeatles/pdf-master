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


class PreviewNavigationMixin(PreviewWidgetHost):
    def go_to_page(self, page_index: int, emit_signal: bool = False):
        _ = emit_signal
        if self._doc is None or self._total_pages <= 0:
            return
        if 0 <= page_index < self._total_pages:
            zoom = self.pdf_view.zoomFactor() if self.pdf_view.zoomMode() == QPdfView.ZoomMode.Custom else 0.0
            navigator = self.pdf_view.pageNavigator()
            if navigator is not None:
                navigator.jump(page_index, QPointF(), zoom)

    def _update_navigation_buttons(self):
        enabled = self._navigation_enabled and self._total_pages > 0
        self.btn_prev.setEnabled(enabled and self._current_page > 0)
        self.btn_next.setEnabled(enabled and self._current_page < self._total_pages - 1)

    def _prev_page(self):
        if self._current_page > 0:
            self.go_to_page(self._current_page - 1, emit_signal=True)

    def _next_page(self):
        if self._current_page < self._total_pages - 1:
            self.go_to_page(self._current_page + 1, emit_signal=True)

    def _on_page_changed(self, page: int):
        if self._total_pages <= 0:
            return
        self.set_page_state(page, self._total_pages)
        if self._text_placement_mode:
            self._refresh_text_placement_overlay()
        if self._queue_ghost_boxes:
            self._refresh_queue_ghost_overlay()
        self.pageChanged.emit(page)
