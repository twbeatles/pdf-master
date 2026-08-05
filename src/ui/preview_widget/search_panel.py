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


class PreviewSearchPanelMixin(PreviewWidgetHost):
    def set_search_panel_visible(self, visible: bool) -> None:
        next_visible = bool(visible)
        changed = self._search_panel_visible != next_visible
        self._search_panel_visible = next_visible
        self.side_tabs.setVisible(next_visible)
        self._update_search_toggle_text()
        if changed:
            self.searchVisibilityChanged.emit(next_visible)

    def focus_search_input(self, select_all: bool = False) -> None:
        self.set_search_panel_visible(True)
        self.side_tabs.setCurrentIndex(0)
        self.search_input.setFocus(Qt.FocusReason.ShortcutFocusReason)
        if select_all:
            self.search_input.selectAll()

    def _schedule_search_refresh(self, *_args):
        self._search_refresh_timer.start(100)

    def _update_search_toggle_text(self) -> None:
        toggle_key = (
            "btn_preview_search_hide"
            if self._search_panel_visible
            else "btn_preview_search_show"
        )
        tooltip_key = (
            "tooltip_preview_search_hide"
            if self._search_panel_visible
            else "tooltip_preview_search_show"
        )
        self.btn_toggle_search.setText(tm.get(toggle_key))
        self.btn_toggle_search.setToolTip(tm.get(tooltip_key))

    def _on_search_submit(self):
        query = self.search_input.text().strip()
        if not query:
            self._on_search_requested()
            return
        if query == self._active_search_query and self.search_results.count() > 0:
            self._select_relative_search_result(1)
            return
        self._on_search_requested()

    def _on_search_requested(self):
        query = self.search_input.text().strip()
        self.search_results.clear()
        self.search_model.setSearchString(query)
        self._active_search_query = query
        if not query:
            self._pending_restore_search_row = None
            return
        if query:
            self._schedule_search_refresh()

    def _select_relative_search_result(self, step: int) -> None:
        count = self.search_results.count()
        if count <= 0:
            return
        current_row = self.search_results.currentRow()
        if current_row < 0:
            current_row = 0 if step >= 0 else count - 1
        else:
            current_row = (current_row + step) % count
        self.search_results.setCurrentRow(current_row)

    def _on_search_escape(self) -> None:
        if self.search_input.text().strip():
            self.search_input.clear()
            self._on_search_requested()
            return
        if self._search_panel_visible:
            self.set_search_panel_visible(False)

    def _refresh_search_results(self):
        self.search_results.clear()
        query = self.search_input.text().strip()
        if not query:
            return

        role_names = {bytes(name).decode("utf-8"): role for role, name in self.search_model.roleNames().items()}
        row_count = self.search_model.rowCount(QModelIndex())
        for row in range(row_count):
            index = self.search_model.index(row, 0, QModelIndex())
            page = self.search_model.data(index, role_names.get("page", int(Qt.ItemDataRole.UserRole)))
            context_before = self.search_model.data(index, role_names.get("contextBefore", int(Qt.ItemDataRole.UserRole) + 3)) or ""
            context_after = self.search_model.data(index, role_names.get("contextAfter", int(Qt.ItemDataRole.UserRole) + 4)) or ""
            label = f"{int(page) + 1}. {context_before}{query}{context_after}".strip()
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, int(page))
            item.setData(Qt.ItemDataRole.UserRole + 1, row)
            self.search_results.addItem(item)
        if self.search_results.count() <= 0:
            self._pending_restore_search_row = None
            return
        restore_row = self._pending_restore_search_row
        self._pending_restore_search_row = None
        if restore_row is not None and restore_row >= 0:
            self.search_results.setCurrentRow(
                max(0, min(self.search_results.count() - 1, restore_row))
            )

    def _on_search_result_selected(self, row: int):
        if row < 0:
            return
        item = self.search_results.item(row)
        if item is None:
            return
        page = item.data(Qt.ItemDataRole.UserRole)
        self.pdf_view.setCurrentSearchResultIndex(int(item.data(Qt.ItemDataRole.UserRole + 1)))
        if isinstance(page, int):
            self.go_to_page(page)

    def _on_bookmark_selected(self, index):
        page_role = None
        for role, name in self.bookmark_model.roleNames().items():
            if bytes(name).decode("utf-8") == "page":
                page_role = role
                break
        if page_role is None:
            return
        page = self.bookmark_model.data(index, page_role)
        if isinstance(page, int):
            self.go_to_page(page)
