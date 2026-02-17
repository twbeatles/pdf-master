"""
Thumbnail Grid Widget for PDF Master v4.0
PDF all pages shown as a grid with lazy loading.
"""

import logging

import fitz
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QPixmap, QImage, QCursor
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QScrollArea,
    QFrame,
    QSpinBox,
)

from ..core.perf import PerfTimer

logger = logging.getLogger(__name__)


class ThumbnailLoaderThread(QThread):
    """Background thumbnail loader for selected page indices."""

    thumbnail_ready = pyqtSignal(int, QPixmap)
    loading_complete = pyqtSignal()
    progress = pyqtSignal(int)

    def __init__(self, pdf_path: str, page_indices: list[int], thumb_w: int = 140, thumb_h: int = 160):
        super().__init__()
        self.pdf_path = pdf_path
        self.page_indices = page_indices
        self.thumb_w = thumb_w
        self.thumb_h = thumb_h
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        doc = None
        try:
            with PerfTimer("ui.thumbnail.batch_load", logger=logger, extra={"count": len(self.page_indices)}):
                doc = fitz.open(self.pdf_path)
                if doc.is_encrypted:
                    logger.warning("Encrypted PDF skipped in thumbnail loader: %s", self.pdf_path)
                    self.loading_complete.emit()
                    return

                total = max(1, len(self.page_indices))
                for i, page_index in enumerate(self.page_indices):
                    if self._is_cancelled:
                        break
                    if page_index < 0 or page_index >= len(doc):
                        continue

                    page = doc[page_index]
                    scale = min(self.thumb_w / max(page.rect.width, 1), self.thumb_h / max(page.rect.height, 1))
                    scale = max(0.05, scale)
                    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))

                    img_data = bytes(pix.samples)
                    fmt = QImage.Format.Format_RGBA8888 if pix.alpha else QImage.Format.Format_RGB888
                    img = QImage(img_data, pix.width, pix.height, pix.stride, fmt)
                    pixmap = QPixmap.fromImage(img.copy())

                    self.thumbnail_ready.emit(page_index, pixmap)
                    self.progress.emit(int((i + 1) / total * 100))
        except Exception as e:
            logger.error("Thumbnail loading failed: %s", e)
        finally:
            if doc:
                doc.close()
            self.loading_complete.emit()


class ThumbnailLabel(QFrame):
    """Clickable thumbnail item."""

    clicked = pyqtSignal(int)

    def __init__(self, page_index: int, parent=None):
        super().__init__(parent)
        self.page_index = page_index
        self._selected = False

        self.setFixedSize(160, 200)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(140, 160)
        self.image_label.setStyleSheet("background: #1a1a2e; border-radius: 4px;")
        layout.addWidget(self.image_label)

        self.page_label = QLabel(f"Page {page_index + 1}")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.page_label)

        self._update_style()

    def set_pixmap(self, pixmap: QPixmap):
        """Assign pre-sized thumbnail pixmap directly."""
        self.image_label.setPixmap(pixmap)

    def set_selected(self, selected: bool):
        self._selected = selected
        self._update_style()

    def _update_style(self):
        if self._selected:
            self.setStyleSheet(
                """
                ThumbnailLabel {
                    background: rgba(79, 140, 255, 0.2);
                    border: 2px solid #4f8cff;
                    border-radius: 8px;
                }
                """
            )
            self.page_label.setStyleSheet("color: #4f8cff; font-size: 11px; font-weight: bold;")
        else:
            self.setStyleSheet(
                """
                ThumbnailLabel {
                    background: rgba(30, 30, 50, 0.5);
                    border: 1px solid #333;
                    border-radius: 8px;
                }
                ThumbnailLabel:hover {
                    background: rgba(79, 140, 255, 0.1);
                    border-color: #4f8cff;
                }
                """
            )
            self.page_label.setStyleSheet("color: #888; font-size: 11px;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.page_index)
        super().mousePressEvent(event)


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

    _ROW_HEIGHT = 210
    _PREFETCH_ROWS = 2
    _MAX_BATCH_SIZE = 64

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pdf_path = ""
        self._thumbnails: list[ThumbnailLabel] = []
        self._selected_index = -1
        self._columns = 4
        self._loader_thread: ThumbnailLoaderThread | None = None
        self._is_dark_theme = True

        self._loaded_indices: set[int] = set()
        self._requested_indices: set[int] = set()
        self._pending_indices: set[int] = set()
        self._active_batch_indices: list[int] = []
        self._total_pages = 0

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        control_bar = QHBoxLayout()
        control_bar.addWidget(QLabel("열 수"))

        self.columns_spin = QSpinBox()
        self.columns_spin.setRange(2, 8)
        self.columns_spin.setValue(self._columns)
        self.columns_spin.valueChanged.connect(self._on_columns_changed)
        control_bar.addWidget(self.columns_spin)

        control_bar.addStretch()

        self.info_label = QLabel("페이지: 0")
        self.info_label.setStyleSheet("color: #888;")
        control_bar.addWidget(self.info_label)
        layout.addLayout(control_bar)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll_changed)

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)

        self.scroll_area.setWidget(self.grid_container)
        layout.addWidget(self.scroll_area)

        self.loading_label = QLabel("PDF 파일을 선택하세요")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("color: #666; font-size: 14px; padding: 40px;")
        self.grid_layout.addWidget(self.loading_label, 0, 0)

    def load_pdf(self, pdf_path: str):
        if not pdf_path:
            return

        self._cleanup_loader_thread()
        self._pdf_path = pdf_path
        self._clear_thumbnails()

        doc = None
        try:
            doc = fitz.open(pdf_path)
            self._total_pages = len(doc)
            self.info_label.setText(f"페이지: {self._total_pages}")
            for i in range(self._total_pages):
                thumb = ThumbnailLabel(i)
                thumb.clicked.connect(self._on_thumbnail_clicked)
                self._thumbnails.append(thumb)
            self._arrange_grid()
            self._request_visible_thumbnails()
        except Exception as e:
            logger.error("Failed to open PDF: %s", e)
            self.loading_label.setText(f"PDF 로드 실패: {e}")
            self.loading_label.show()
            return
        finally:
            if doc:
                doc.close()

    def _cleanup_loader_thread(self):
        if self._loader_thread:
            try:
                self._loader_thread.thumbnail_ready.disconnect()
                self._loader_thread.progress.disconnect()
                self._loader_thread.loading_complete.disconnect()
            except Exception:
                pass

            if self._loader_thread.isRunning():
                self._loader_thread.cancel()
                if not self._loader_thread.wait(3000):
                    logger.warning("ThumbnailLoaderThread did not finish in time")
                    self._loader_thread.terminate()
                    self._loader_thread.wait(1000)

            self._loader_thread = None

        if self._active_batch_indices:
            self._pending_indices.update(self._active_batch_indices)
            self._requested_indices.difference_update(self._active_batch_indices)
            self._active_batch_indices = []

    def _clear_thumbnails(self):
        for thumb in self._thumbnails:
            thumb.deleteLater()
        self._thumbnails.clear()
        self._selected_index = -1
        self._loaded_indices.clear()
        self._requested_indices.clear()
        self._pending_indices.clear()
        self._active_batch_indices = []
        self._total_pages = 0

        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

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
            self.loading_label.show()

    def _visible_index_window(self) -> tuple[int, int]:
        if not self._thumbnails:
            return 0, -1
        scrollbar = self.scroll_area.verticalScrollBar()
        viewport_h = max(1, self.scroll_area.viewport().height())
        top = scrollbar.value()
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

        self._loader_thread = ThumbnailLoaderThread(self._pdf_path, batch, thumb_w=140, thumb_h=160)
        self._loader_thread.thumbnail_ready.connect(self._on_thumbnail_ready)
        self._loader_thread.progress.connect(self._on_loader_progress)
        self._loader_thread.loading_complete.connect(self._on_loading_complete)
        self._loader_thread.start()

    @pyqtSlot(int, QPixmap)
    def _on_thumbnail_ready(self, index: int, pixmap: QPixmap):
        if index < len(self._thumbnails):
            self._thumbnails[index].set_pixmap(pixmap)
            self._loaded_indices.add(index)
            self._requested_indices.discard(index)
        self.loadingProgress.emit(int((len(self._loaded_indices) / max(1, self._total_pages)) * 100))

    @pyqtSlot(int)
    def _on_loader_progress(self, _value: int):
        self.loadingProgress.emit(int((len(self._loaded_indices) / max(1, self._total_pages)) * 100))

    @pyqtSlot()
    def _on_loading_complete(self):
        logger.debug("Thumbnail batch loading complete")
        self._active_batch_indices = []
        self._loader_thread = None
        self._request_visible_thumbnails()
        self._start_next_loader()

    def _on_columns_changed(self, value: int):
        self._columns = value
        self._arrange_grid()
        self._request_visible_thumbnails()

    def _on_scroll_changed(self, _value: int):
        self._request_visible_thumbnails()

    def _on_thumbnail_clicked(self, page_index: int):
        if 0 <= self._selected_index < len(self._thumbnails):
            self._thumbnails[self._selected_index].set_selected(False)
        self._selected_index = page_index
        if 0 <= page_index < len(self._thumbnails):
            self._thumbnails[page_index].set_selected(True)
        self.pageSelected.emit(page_index)

    def get_selected_page(self) -> int:
        return self._selected_index

    def select_page(self, index: int):
        self._on_thumbnail_clicked(index)
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

    def closeEvent(self, event):
        self._cleanup_loader_thread()
        super().closeEvent(event)
