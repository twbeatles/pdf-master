from __future__ import annotations

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

class ThumbnailGridWidget(QWidget):
    """
    Grid of PDF page thumbnails.

    Signals:
        pageSelected(int): emitted when a page is selected
        pageDoubleClicked(int): emitted when a page is double-clicked
    """

    pageSelected = pyqtSignal(int)
    pageDoubleClicked = pyqtSignal(int)
    loadingProgress = pyqtSignal(int)
    selectedPagesChanged = pyqtSignal(list)

    _ROW_HEIGHT = 210
    _PREFETCH_ROWS = 2
    _MAX_BATCH_SIZE = 64

    def __init__(self, parent=None, selection_mode: str = "single"):
        super().__init__(parent)
        self._pdf_path = ""
        self._thumbnails: list[ThumbnailLabel] = []
        self._active_index = -1
        self._selected_indices: set[int] = set()
        self._selection_anchor_index = -1
        self._selection_mode = selection_mode if selection_mode in {"single", "extended"} else "single"
        self._columns = 4
        self._loader_thread: ThumbnailLoaderThread | None = None
        self._is_dark_theme = True

        self._loaded_indices: set[int] = set()
        self._requested_indices: set[int] = set()
        self._pending_indices: set[int] = set()
        self._active_batch_indices: list[int] = []
        self._total_pages = 0
        self._pdf_password: str | None = None

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        control_bar = QHBoxLayout()
        control_bar.addWidget(QLabel(tm.get("thumb_columns_label")))

        self.columns_spin = QSpinBox()
        self.columns_spin.setRange(2, 8)
        self.columns_spin.setValue(self._columns)
        self.columns_spin.valueChanged.connect(self._on_columns_changed)
        control_bar.addWidget(self.columns_spin)

        control_bar.addStretch()

        self.info_label = QLabel(tm.get("thumb_page_count", 0))
        self.info_label.setStyleSheet("color: #888;")
        control_bar.addWidget(self.info_label)
        layout.addLayout(control_bar)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scrollbar = self.scroll_area.verticalScrollBar()
        if scrollbar is not None:
            scrollbar.valueChanged.connect(self._on_scroll_changed)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)

        self.scroll_area.setWidget(self.grid_container)
        layout.addWidget(self.scroll_area)

        self.loading_label = QLabel(tm.get("thumb_select_pdf"))
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("color: #666; font-size: 14px; padding: 40px;")
        self.grid_layout.addWidget(self.loading_label, 0, 0)

    def _set_loading_message(self, message: str):
        if self.grid_layout.indexOf(self.loading_label) < 0:
            self.grid_layout.addWidget(self.loading_label, 0, 0)
        self.info_label.setText(tm.get("thumb_page_count", 0))
        self.loading_label.setText(message)
        self.loading_label.show()

    def show_status_message(self, message: str):
        self._cleanup_loader_thread()
        self._pdf_path = ""
        self._pdf_password = None
        self._clear_thumbnails()
        self._set_loading_message(message)

    def load_pdf(self, pdf_path: str, password: str | None = None):
        if not pdf_path:
            self.clear()
            return

        self._cleanup_loader_thread()
        self._pdf_path = pdf_path
        self._pdf_password = password
        self._clear_thumbnails()

        doc = None
        try:
            doc, error_message = _open_thumbnail_document(pdf_path, password)
            if not doc:
                self._set_loading_message(error_message or tm.get("preview_default"))
                return
            self._total_pages = len(doc)
            self.info_label.setText(tm.get("thumb_page_count", self._total_pages))
            for i in range(self._total_pages):
                thumb = ThumbnailLabel(i)
                thumb.clickedWithModifiers.connect(self._on_thumbnail_clicked)
                self._thumbnails.append(thumb)
            self._arrange_grid()
            self._request_visible_thumbnails()
        except Exception as e:
            logger.error("Failed to open PDF: %s", e)
            self._set_loading_message(tm.get("thumb_load_failed", str(e)))
            return
        finally:
            if doc:
                doc.close()

    def _disconnect_loader_thread(self, thread: ThumbnailLoaderThread):
        try:
            thread.thumbnail_ready.disconnect(self._on_thumbnail_ready)
        except Exception:
            pass
        try:
            thread.progress.disconnect(self._on_loader_progress)
        except Exception:
            pass
        try:
            thread.loading_complete.disconnect(self._on_loading_complete)
        except Exception:
            pass

    def _cleanup_loader_thread(self):
        thread = self._loader_thread
        if thread:
            self._disconnect_loader_thread(thread)

            if thread.isRunning():
                thread.cancel()
                try:
                    thread.finished.connect(thread.deleteLater)
                except Exception:
                    pass
                if not thread.wait(300):
                    logger.info("ThumbnailLoaderThread is stopping in background")
            else:
                thread.deleteLater()

            self._loader_thread = None

        if self._active_batch_indices:
            self._pending_indices.update(self._active_batch_indices)
            self._requested_indices.difference_update(self._active_batch_indices)
            self._active_batch_indices = []

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

    def _start_next_loader(self):
        if self._loader_thread and self._loader_thread.isRunning():
            return
        if not self._pending_indices:
            return

        batch = sorted(self._pending_indices)[: self._MAX_BATCH_SIZE]
        for idx in batch:
            self._pending_indices.discard(idx)
        self._requested_indices.update(batch)
        self._active_batch_indices = batch

        self._loader_thread = ThumbnailLoaderThread(
            self._pdf_path,
            batch,
            password=self._pdf_password,
            thumb_w=140,
            thumb_h=160,
        )
        self._loader_thread.thumbnail_ready.connect(self._on_thumbnail_ready)
        self._loader_thread.progress.connect(self._on_loader_progress)
        self._loader_thread.loading_complete.connect(self._on_loading_complete)
        self._loader_thread.start()

    def _is_active_loader_sender(self) -> bool:
        """현재 활성 로더 스레드에서 온 시그널인지 확인 (잔여 스레드 혼선 방지)."""
        sender = self.sender()
        active = getattr(self, "_loader_thread", None)
        if active is None:
            # cleanup 직후 잔여 시그널은 무시
            return False
        if sender is not None and sender is not active:
            return False
        return True

    @pyqtSlot(int, QPixmap)
    def _on_thumbnail_ready(self, index: int, pixmap: QPixmap):
        if not self._is_active_loader_sender():
            return
        if index < len(self._thumbnails):
            self._thumbnails[index].set_pixmap(pixmap)
            self._loaded_indices.add(index)
            self._requested_indices.discard(index)
        self.loadingProgress.emit(int((len(self._loaded_indices) / max(1, self._total_pages)) * 100))

    @pyqtSlot(int)
    def _on_loader_progress(self, _value: int):
        if not self._is_active_loader_sender():
            return
        self.loadingProgress.emit(int((len(self._loaded_indices) / max(1, self._total_pages)) * 100))

    @pyqtSlot()
    def _on_loading_complete(self):
        if not self._is_active_loader_sender():
            return
        logger.debug("Thumbnail batch loading complete")
        unfinished = [
            index for index in self._active_batch_indices if index not in self._loaded_indices
        ]
        self._requested_indices.difference_update(self._active_batch_indices)
        self._pending_indices.update(unfinished)
        self._active_batch_indices = []
        if self._loader_thread:
            self._loader_thread.deleteLater()
        self._loader_thread = None
        self._request_visible_thumbnails()
        self._start_next_loader()

    def _on_columns_changed(self, value: int):
        self._columns = value
        self._arrange_grid()
        self._request_visible_thumbnails()

    def _on_scroll_changed(self, _value: int):
        self._request_visible_thumbnails()

    def _refresh_thumbnail_states(self):
        for index, thumb in enumerate(self._thumbnails):
            thumb.set_active(index == self._active_index)
            thumb.set_selected(index in self._selected_indices)

    def _emit_selected_pages_changed(self):
        self.selectedPagesChanged.emit(self.get_selected_pages())

    def _set_selected_indices(self, indices: Iterable[int]):
        normalized = {
            index
            for index in indices
            if isinstance(index, int) and 0 <= index < len(self._thumbnails)
        }
        if normalized == self._selected_indices:
            return
        self._selected_indices = normalized
        self._refresh_thumbnail_states()
        self._emit_selected_pages_changed()

    def set_selection_mode(self, selection_mode: str):
        if selection_mode not in {"single", "extended"}:
            selection_mode = "single"
        if selection_mode == self._selection_mode:
            return
        self._selection_mode = selection_mode
        if selection_mode == "single":
            self._set_selected_indices([self._active_index] if self._active_index >= 0 else [])
        self._refresh_thumbnail_states()

    def set_active_page(self, index: int, emit_signal: bool = False):
        if index < 0 or index >= len(self._thumbnails):
            return
        if self._active_index != index:
            self._active_index = index
            self._refresh_thumbnail_states()
        if emit_signal:
            self.pageSelected.emit(index)

    def _apply_single_selection(self, page_index: int):
        if page_index < 0 or page_index >= len(self._thumbnails):
            return
        self._selection_anchor_index = page_index
        self._active_index = page_index
        self._set_selected_indices([page_index])
        self.pageSelected.emit(page_index)

    @pyqtSlot(int, object)
    def _on_thumbnail_clicked(self, page_index: int, modifiers: object):
        if page_index < 0 or page_index >= len(self._thumbnails):
            return

        if self._selection_mode == "single":
            self._apply_single_selection(page_index)
            return

        raw_modifier_value = getattr(modifiers, "value", None)
        if isinstance(raw_modifier_value, int):
            modifier_value = Qt.KeyboardModifier(raw_modifier_value)
        elif isinstance(modifiers, int):
            modifier_value = Qt.KeyboardModifier(modifiers)
        else:
            modifier_value = Qt.KeyboardModifier.NoModifier
        self.set_active_page(page_index, emit_signal=True)

        if modifier_value & Qt.KeyboardModifier.ShiftModifier:
            anchor = self._selection_anchor_index if self._selection_anchor_index >= 0 else page_index
            start = min(anchor, page_index)
            end = max(anchor, page_index)
            self._set_selected_indices(range(start, end + 1))
            return

        if modifier_value & Qt.KeyboardModifier.ControlModifier:
            self._selection_anchor_index = page_index
            updated = set(self._selected_indices)
            if page_index in updated:
                updated.remove(page_index)
            else:
                updated.add(page_index)
            self._set_selected_indices(updated)
            return

        self._selection_anchor_index = page_index

    def get_selected_page(self) -> int:
        if self._selection_mode == "single":
            return self._active_index
        return self._active_index

    @property
    def selection_mode(self) -> str:
        return self._selection_mode

    def get_selected_pages(self) -> list[int]:
        if self._selection_mode == "single":
            return [self._active_index] if self._active_index >= 0 else []
        return sorted(self._selected_indices)

    def get_active_page(self) -> int:
        return self._active_index

    def select_page(self, index: int):
        if index < 0 or index >= len(self._thumbnails):
            return
        if self._selection_mode == "single":
            self._apply_single_selection(index)
        else:
            self.set_active_page(index, emit_signal=True)
        if 0 <= index < len(self._thumbnails):
            self.scroll_area.ensureWidgetVisible(self._thumbnails[index])

    def set_theme(self, is_dark: bool):
        self._is_dark_theme = is_dark
        if is_dark:
            self.scroll_area.setStyleSheet(
                """
                QScrollArea {
                    background: transparent;
                    border: none;
                }
                QScrollBar:vertical {
                    background: #1a1a2e;
                    width: 8px;
                    border-radius: 4px;
                }
                QScrollBar::handle:vertical {
                    background: #4f8cff;
                    border-radius: 4px;
                }
                """
            )
            self.info_label.setStyleSheet("color: #888;")
            self.loading_label.setStyleSheet("color: #666; font-size: 14px; padding: 40px;")
        else:
            self.scroll_area.setStyleSheet(
                """
                QScrollArea {
                    background: transparent;
                    border: none;
                }
                QScrollBar:vertical {
                    background: #f0f0f0;
                    width: 8px;
                    border-radius: 4px;
                }
                QScrollBar::handle:vertical {
                    background: #4f8cff;
                    border-radius: 4px;
                }
                """
            )
            self.info_label.setStyleSheet("color: #666;")
            self.loading_label.setStyleSheet("color: #888; font-size: 14px; padding: 40px;")

    def closeEvent(self, a0: QCloseEvent | None):
        self._cleanup_loader_thread()
        super().closeEvent(a0)
