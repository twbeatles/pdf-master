from __future__ import annotations

from .._typing import ThumbnailGridHost
import logging
from typing import Iterable
from PyQt6.QtCore import QThread, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QCloseEvent, QCursor, QImage, QMouseEvent, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from ...core.i18n import tm
from ...core.optional_deps import fitz
from ...core.perf import PerfTimer
logger = logging.getLogger(__name__)
from .document import _open_thumbnail_document
from .loader import ThumbnailLoaderThread
from .tile import ThumbnailLabel


class ThumbnailGridLayoutMixin(ThumbnailGridHost):
    def _clear_thumbnails(self):
        for thumb in self._thumbnails:
            thumb.deleteLater()
        self._thumbnails.clear()
        self._active_index = -1
        self._selected_indices.clear()
        self._selection_anchor_index = -1
        self._loaded_indices.clear()
        self._requested_indices.clear()
        self._pending_indices.clear()
        self._active_batch_indices = []
        self._total_pages = 0

        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                if widget is self.loading_label:
                    self.loading_label.hide()
                    continue
                widget.deleteLater()

    def clear(self):
        self._cleanup_loader_thread()
        self._pdf_path = ""
        self._pdf_password = None
        self._pdf_mtime_ns = 0
        lru = getattr(self, "_pixmap_lru", None)
        if lru is not None:
            lru.clear()
        self._clear_thumbnails()
        self._set_loading_message(tm.get("thumb_select_pdf"))

    def _arrange_grid(self):
        for i in reversed(range(self.grid_layout.count())):
            self.grid_layout.takeAt(i)

        for i, thumb in enumerate(self._thumbnails):
            row = i // self._columns
            col = i % self._columns
            self.grid_layout.addWidget(thumb, row, col)

        if self._thumbnails:
            self.loading_label.hide()
        else:
            self._set_loading_message(tm.get("thumb_select_pdf"))

    def _visible_index_window(self) -> tuple[int, int]:
        if not self._thumbnails:
            return 0, -1
        scrollbar = self.scroll_area.verticalScrollBar()
        viewport = self.scroll_area.viewport()
        viewport_h = max(1, viewport.height()) if viewport is not None else self._ROW_HEIGHT
        top = scrollbar.value() if scrollbar is not None else 0
        bottom = top + viewport_h
        start_row = max(0, (top // self._ROW_HEIGHT) - self._PREFETCH_ROWS)
        end_row = (bottom // self._ROW_HEIGHT) + self._PREFETCH_ROWS
        start_idx = start_row * self._columns
        end_idx = min(len(self._thumbnails) - 1, ((end_row + 1) * self._columns) - 1)
        return start_idx, end_idx

    def _request_visible_thumbnails(self):
        start_idx, end_idx = self._visible_index_window()
        if end_idx < start_idx:
            return
        needed = [
            idx
            for idx in range(start_idx, end_idx + 1)
            if idx not in self._loaded_indices and idx not in self._requested_indices
        ]
        if not needed:
            return
        self._pending_indices.update(needed)
        self._start_next_loader()
