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

from .grid_layout import ThumbnailGridLayoutMixin
from .grid_loading import ThumbnailGridLoadingMixin
from .grid_selection import ThumbnailGridSelectionMixin
from .grid_theme import ThumbnailGridThemeMixin


class ThumbnailGridWidget(ThumbnailGridLayoutMixin, ThumbnailGridLoadingMixin, ThumbnailGridSelectionMixin, ThumbnailGridThemeMixin, QWidget):
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

    def closeEvent(self, a0: QCloseEvent | None):
        self._cleanup_loader_thread()
        super().closeEvent(a0)

