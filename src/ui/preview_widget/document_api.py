from __future__ import annotations
from __future__ import annotations
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


class PreviewDocumentApiMixin(object):
    def set_document(self, document: QPdfDocument | None, path: str = ""):
        old_doc = self._doc
        self._doc = document
        self.pdf_view.setDocument(document)
        self.search_model.setDocument(document)
        self.bookmark_model.setDocument(document)

        if document is None:
            self._current_page = 0
            self._total_pages = 0
            self.search_results.clear()
            self.search_input.clear()
            self._active_search_query = ""
            self._pending_restore_search_row = None
            self.set_navigation_enabled(False)
        else:
            self._current_page = 0
            self._total_pages = max(0, document.pageCount())
            self.set_navigation_enabled(self._total_pages > 0)
            self.set_page_state(0, self._total_pages)
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)
            self.bookmark_tree.expandAll()
            self._schedule_search_refresh()

        if old_doc is not None and old_doc is not document:
            try:
                old_doc.close()
            except Exception:
                logger.debug("Failed to close previous preview document", exc_info=True)

        self.btn_print.setEnabled(document is not None and self._total_pages > 0)
        self.btn_page_setup.setEnabled(document is not None and self._total_pages > 0)
        _ = path

    def document(self) -> QPdfDocument | None:
        return self._doc

    def clear(self):
        self.set_document(None)

    def clear_display(self):
        self.set_document(None)

    def set_page_state(self, current_page: int, total_pages: int):
        total_pages = max(0, int(total_pages))
        if total_pages == 0:
            self._current_page = 0
            self._total_pages = 0
            self.page_label.setText("0 / 0")
        else:
            self._total_pages = total_pages
            self._current_page = max(0, min(int(current_page), total_pages - 1))
            self.page_label.setText(f"{self._current_page + 1} / {self._total_pages}")
        self._update_navigation_buttons()

    def set_navigation_enabled(self, enabled: bool):
        self._navigation_enabled = enabled
        self._update_navigation_buttons()

    def display_size(self):
        viewport = self.pdf_view.viewport()
        return viewport.size() if viewport is not None else self.pdf_view.size()

    def capture_view_state(self) -> dict[str, object]:
        zoom_mode = self.pdf_view.zoomMode()
        if zoom_mode == QPdfView.ZoomMode.FitInView:
            zoom_mode_name = "fit_view"
        elif zoom_mode == QPdfView.ZoomMode.FitToWidth:
            zoom_mode_name = "fit_width"
        else:
            zoom_mode_name = "custom"
        return {
            "page": self._current_page,
            "zoom_mode": zoom_mode_name,
            "zoom_factor": float(self.pdf_view.zoomFactor()),
            "search_panel_visible": self._search_panel_visible,
            "side_tab_index": int(self.side_tabs.currentIndex()),
            "search_query": self.search_input.text().strip(),
            "search_result_row": int(self.search_results.currentRow()),
        }

    def restore_view_state(self, state: dict[str, object] | None):
        if not state or self._doc is None or self._total_pages <= 0:
            return
        zoom_mode = state.get("zoom_mode")
        if zoom_mode == "fit_width":
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        elif zoom_mode == "custom":
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)
            raw_zoom = state.get("zoom_factor", 1.0)
            zoom_factor = float(raw_zoom) if isinstance(raw_zoom, (int, float)) else 1.0
            self.pdf_view.setZoomFactor(max(0.1, zoom_factor))
        else:
            self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)
        self.set_search_panel_visible(
            bool(state.get("search_panel_visible", True))
        )
        raw_side_tab_index = state.get("side_tab_index", 0)
        side_tab_index = (
            int(raw_side_tab_index)
            if isinstance(raw_side_tab_index, (int, float))
            else 0
        )
        self.side_tabs.setCurrentIndex(
            max(0, min(self.side_tabs.count() - 1, side_tab_index))
        )
        search_query = str(state.get("search_query", "") or "").strip()
        self.search_input.setText(search_query)
        raw_search_row = state.get("search_result_row", -1)
        self._pending_restore_search_row = (
            int(raw_search_row)
            if isinstance(raw_search_row, (int, float))
            else None
        )
        if search_query:
            self._active_search_query = search_query
            self._on_search_requested()
        else:
            self.search_results.clear()
            self._active_search_query = ""
            self._pending_restore_search_row = None
        raw_page = state.get("page", 0)
        page = int(raw_page) if isinstance(raw_page, (int, float)) else 0
        self.go_to_page(page)

    def closeEvent(self, a0: QCloseEvent | None):
        try:
            self.set_region_select_mode(False)
            self.set_text_placement_mode(False)
            if self._doc is not None:
                self._doc.close()
        except Exception:
            logger.debug("Failed to close preview document on widget shutdown", exc_info=True)
        super().closeEvent(a0)
