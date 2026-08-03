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

from .document_api import PreviewDocumentApiMixin
from .navigation import PreviewNavigationMixin
from .zoom import PreviewZoomMixin
from .search_panel import PreviewSearchPanelMixin
from .theme_api import PreviewThemeMixin
from .interaction_overlays import PreviewInteractionMixin


class ZoomablePreviewWidget(PreviewDocumentApiMixin, PreviewNavigationMixin, PreviewZoomMixin, PreviewSearchPanelMixin, PreviewThemeMixin, PreviewInteractionMixin, QWidget):
    zoomChanged = pyqtSignal(float)
    pageChanged = pyqtSignal(int)
    printRequested = pyqtSignal()
    pageSetupRequested = pyqtSignal()
    searchVisibilityChanged = pyqtSignal(bool)
    # 1-based page, x0,y0,x1,y1 in PDF points
    regionSelected = pyqtSignal(int, float, float, float, float)
    regionSelectModeChanged = pyqtSignal(bool)
    # 이동 가능한 텍스트 배치 박스 (1-based page + PDF points)
    textPlacementMoved = pyqtSignal(int, float, float, float, float)
    textPlacementModeChanged = pyqtSignal(bool)
    textPlacementTextEdited = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._doc: QPdfDocument | None = None
        self._current_page = 0
        self._total_pages = 0
        self._navigation_enabled = False
        self._search_panel_visible = True
        self._active_search_query = ""
        self._pending_restore_search_row: int | None = None
        self._region_select_mode = False
        self._region_overlay: RegionSelectOverlay | None = None
        self._text_placement_mode = False
        self._text_placement_overlay: TextPlacementOverlay | None = None
        self._queue_ghost_overlay: QueueGhostOverlay | None = None
        # PDF 포인트 기준 큐 고스트 (page_num 0-based, rect x0y0x1y1, text)
        self._queue_ghost_boxes: list[dict] = []
        # PDF 포인트 기준 현재 배치 사각형 (x0,y0,x1,y1)
        self._text_placement_pts: tuple[float, float, float, float] | None = None
        self._text_placement_text = ""
        self._text_placement_color = QColor(0, 0, 0)
        self._text_placement_fontsize = 14.0
        self._text_placement_align = 0
        self._text_placement_opacity = 1.0

        self._search_refresh_timer = QTimer(self)
        self._search_refresh_timer.setSingleShot(True)
        self._search_refresh_timer.timeout.connect(self._refresh_search_results)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        btn_zoom_out = QPushButton("-")
        btn_zoom_out.setFixedSize(28, 28)
        btn_zoom_out.setToolTip(tm.get("tooltip_zoom_out"))
        btn_zoom_out.clicked.connect(self._on_zoom_out)
        toolbar.addWidget(btn_zoom_out)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(52)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toolbar.addWidget(self.zoom_label)

        btn_zoom_in = QPushButton("+")
        btn_zoom_in.setFixedSize(28, 28)
        btn_zoom_in.setToolTip(tm.get("tooltip_zoom_in"))
        btn_zoom_in.clicked.connect(self._on_zoom_in)
        toolbar.addWidget(btn_zoom_in)

        self.btn_fit = QPushButton(tm.get("btn_fit_view"))
        self.btn_fit.setFixedHeight(28)
        self.btn_fit.setToolTip(tm.get("tooltip_fit_view"))
        self.btn_fit.clicked.connect(self._on_fit_view)
        toolbar.addWidget(self.btn_fit)

        self.btn_actual = QPushButton("1:1")
        self.btn_actual.setFixedSize(40, 28)
        self.btn_actual.setToolTip(tm.get("tooltip_actual_size"))
        self.btn_actual.clicked.connect(self._on_reset_zoom)
        toolbar.addWidget(self.btn_actual)

        toolbar.addStretch()

        self.btn_toggle_search = QPushButton()
        self.btn_toggle_search.setObjectName("secondaryBtn")
        self.btn_toggle_search.setFixedHeight(28)
        self.btn_toggle_search.clicked.connect(
            lambda: self.set_search_panel_visible(not self._search_panel_visible)
        )
        toolbar.addWidget(self.btn_toggle_search)

        self.btn_page_setup = QPushButton(tm.get("page_setup"))
        self.btn_page_setup.setObjectName("secondaryBtn")
        self.btn_page_setup.setFixedHeight(28)
        self.btn_page_setup.clicked.connect(self.pageSetupRequested.emit)
        toolbar.addWidget(self.btn_page_setup)

        self.btn_print = QPushButton(tm.get("btn_print_preview"))
        self.btn_print.setObjectName("secondaryBtn")
        self.btn_print.setFixedHeight(28)
        self.btn_print.setToolTip(tm.get("tooltip_print_preview"))
        self.btn_print.clicked.connect(self.printRequested.emit)
        toolbar.addWidget(self.btn_print)

        layout.addLayout(toolbar)

        content = QHBoxLayout()
        content.setSpacing(8)

        self.side_tabs = QTabWidget()
        self.side_tabs.setMinimumWidth(240)
        self.side_tabs.setMaximumWidth(320)

        search_tab = QWidget()
        search_layout = QVBoxLayout(search_tab)
        search_bar = QHBoxLayout()
        self.search_input = PreviewSearchLineEdit()
        self.search_input.setPlaceholderText(tm.get("preview_search_placeholder"))
        self.search_input.submitRequested.connect(self._on_search_submit)
        self.search_input.previousRequested.connect(
            lambda: self._select_relative_search_result(-1)
        )
        self.search_input.escapePressed.connect(self._on_search_escape)
        search_bar.addWidget(self.search_input, 1)
        self.btn_search = QPushButton(tm.get("preview_search"))
        self.btn_search.clicked.connect(self._on_search_requested)
        search_bar.addWidget(self.btn_search)
        search_layout.addLayout(search_bar)
        self.search_results = QListWidget()
        self.search_results.currentRowChanged.connect(self._on_search_result_selected)
        search_layout.addWidget(self.search_results, 1)
        self.side_tabs.addTab(search_tab, tm.get("preview_search_tab"))

        bookmark_tab = QWidget()
        bookmark_layout = QVBoxLayout(bookmark_tab)
        self.bookmark_tree = QTreeView()
        self.bookmark_tree.setHeaderHidden(True)
        self.bookmark_tree.clicked.connect(self._on_bookmark_selected)
        bookmark_layout.addWidget(self.bookmark_tree, 1)
        self.side_tabs.addTab(bookmark_tab, tm.get("preview_bookmarks_tab"))

        content.addWidget(self.side_tabs)

        self.pdf_view = QPdfView(self)
        self.pdf_view.setPageMode(QPdfView.PageMode.SinglePage)
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)
        self.pdf_view.zoomFactorChanged.connect(self._on_zoom_changed)
        navigator = self.pdf_view.pageNavigator()
        if navigator is not None:
            navigator.currentPageChanged.connect(self._on_page_changed)
        content.addWidget(self.pdf_view, 1)

        # 드래그 영역 선택 오버레이 (pdf_view 자식)
        self._region_overlay = RegionSelectOverlay(self.pdf_view)
        self._region_overlay.selectionFinished.connect(self._on_region_selection_finished)
        self._region_overlay.selectionCancelled.connect(self._on_region_selection_cancelled)
        # 이동 가능 텍스트 배치 오버레이
        self._text_placement_overlay = TextPlacementOverlay(self.pdf_view)
        self._text_placement_overlay.boxMoved.connect(self._on_text_placement_box_moved)
        self._text_placement_overlay.placementCancelled.connect(self._on_text_placement_cancelled)
        self._text_placement_overlay.textEdited.connect(self._on_text_placement_text_edited)
        self._queue_ghost_overlay = QueueGhostOverlay(self.pdf_view)
        self.pdf_view.installEventFilter(self)
        if self.pdf_view.viewport() is not None:
            self.pdf_view.viewport().installEventFilter(self)
        self._sync_region_overlay_geometry()

        layout.addLayout(content, 1)

        nav_bar = QHBoxLayout()
        nav_bar.setSpacing(8)

        self.btn_prev = QPushButton(tm.get("prev_page"))
        self.btn_prev.setFixedSize(80, 30)
        self.btn_prev.clicked.connect(self._prev_page)
        nav_bar.addWidget(self.btn_prev)

        self.page_label = QLabel("0 / 0")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setStyleSheet("font-weight: bold; min-width: 72px;")
        nav_bar.addWidget(self.page_label)

        self.btn_next = QPushButton(tm.get("next_page"))
        self.btn_next.setFixedSize(80, 30)
        self.btn_next.clicked.connect(self._next_page)
        nav_bar.addWidget(self.btn_next)
        nav_bar.addStretch()

        layout.addLayout(nav_bar)

        self.search_model = QPdfSearchModel(self)
        self.search_model.rowsInserted.connect(self._schedule_search_refresh)
        self.search_model.rowsRemoved.connect(self._schedule_search_refresh)
        self.search_model.modelReset.connect(self._schedule_search_refresh)

        self.bookmark_model = QPdfBookmarkModel(self)
        self.bookmark_tree.setModel(self.bookmark_model)
        self.pdf_view.setSearchModel(self.search_model)
        self.set_navigation_enabled(False)
        self.set_search_panel_visible(True)
        self._on_zoom_changed(self.pdf_view.zoomFactor())

