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
from .search import PreviewSearchLineEdit
from .text_placement import TextPlacementOverlay

class ZoomablePreviewWidget(QWidget):
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
        # PDF 포인트 기준 현재 배치 사각형 (x0,y0,x1,y1)
        self._text_placement_pts: tuple[float, float, float, float] | None = None
        self._text_placement_text = ""
        self._text_placement_color = QColor(0, 0, 0)
        self._text_placement_fontsize = 14.0

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

    def _current_zoom_factor(self) -> float:
        zoom = float(self.pdf_view.zoomFactor() or 1.0)
        return max(0.1, min(5.0, zoom))

    def _set_custom_zoom(self, zoom: float):
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.Custom)
        self.pdf_view.setZoomFactor(max(0.1, min(5.0, zoom)))

    def _on_zoom_in(self):
        self._set_custom_zoom(self._current_zoom_factor() + 0.1)

    def _on_zoom_out(self):
        self._set_custom_zoom(self._current_zoom_factor() - 0.1)

    def _on_fit_view(self):
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)

    def _on_reset_zoom(self):
        self._set_custom_zoom(1.0)

    def _on_zoom_changed(self, zoom: float):
        if self._text_placement_mode:
            self._refresh_text_placement_overlay()
        percent = int(max(zoom, 0.1) * 100)
        self.zoom_label.setText(f"{percent}%")
        self.zoomChanged.emit(max(zoom, 0.1))

    def _on_page_changed(self, page: int):
        if self._total_pages <= 0:
            return
        self.set_page_state(page, self._total_pages)
        if self._text_placement_mode:
            self._refresh_text_placement_overlay()
        self.pageChanged.emit(page)

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

    def set_theme(self, is_dark: bool):
        if is_dark:
            base_style = """
                QPdfView, QListWidget, QTreeView {
                    background: #161b22;
                    border: 1px solid #30363d;
                    border-radius: 8px;
                    color: #e6edf3;
                }
            """
        else:
            base_style = """
                QPdfView, QListWidget, QTreeView {
                    background: #ffffff;
                    border: 1px solid #d0d7de;
                    border-radius: 8px;
                    color: #1f2328;
                }
            """
        self.pdf_view.setStyleSheet(base_style)
        self.search_results.setStyleSheet(base_style)
        self.bookmark_tree.setStyleSheet(base_style)

    # --- 드래그 영역 선택 (교정 등) ---

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

    # --- 이동 가능 텍스트 배치 ---

    def is_text_placement_mode(self) -> bool:
        return bool(self._text_placement_mode)

    def set_text_placement_mode(
        self,
        enabled: bool,
        *,
        text: str = "",
        rect_pts: tuple[float, float, float, float] | list[float] | None = None,
        color: tuple[float, float, float] | list[float] | None = None,
        fontsize: float = 14.0,
    ) -> None:
        """미리보기에 텍스트 상자를 표시하고 드래그로 위치를 조정한다."""
        next_enabled = bool(enabled) and self._doc is not None and self._total_pages > 0
        if next_enabled and self._region_select_mode:
            self.set_region_select_mode(False)

        if next_enabled:
            self._text_placement_text = text or self._text_placement_text or " "
            if rect_pts is not None and len(rect_pts) >= 4:
                self._text_placement_pts = (
                    float(rect_pts[0]),
                    float(rect_pts[1]),
                    float(rect_pts[2]),
                    float(rect_pts[3]),
                )
            elif self._text_placement_pts is None:
                self._text_placement_pts = (100.0, 100.0, 300.0, 150.0)
            if color is not None and len(color) >= 3:
                r, g, b = float(color[0]), float(color[1]), float(color[2])
                self._text_placement_color = QColor(
                    int(max(0, min(255, r * 255))),
                    int(max(0, min(255, g * 255))),
                    int(max(0, min(255, b * 255))),
                )
            self._text_placement_fontsize = max(6.0, float(fontsize))

        was = self._text_placement_mode
        self._text_placement_mode = next_enabled
        if self._text_placement_overlay is not None:
            self._sync_region_overlay_geometry()
            if next_enabled:
                self._refresh_text_placement_overlay()
                self._text_placement_overlay.set_active(True)
            else:
                self._text_placement_overlay.set_active(False)
        if was != next_enabled:
            self.textPlacementModeChanged.emit(next_enabled)

    def update_text_placement_content(
        self,
        *,
        text: str | None = None,
        rect_pts: tuple[float, float, float, float] | list[float] | None = None,
        color: tuple[float, float, float] | list[float] | None = None,
        fontsize: float | None = None,
    ) -> None:
        """배치 모드 중 텍스트/스타일/좌표를 갱신한다."""
        if text is not None:
            self._text_placement_text = text
        if rect_pts is not None and len(rect_pts) >= 4:
            self._text_placement_pts = (
                float(rect_pts[0]),
                float(rect_pts[1]),
                float(rect_pts[2]),
                float(rect_pts[3]),
            )
        if color is not None and len(color) >= 3:
            r, g, b = float(color[0]), float(color[1]), float(color[2])
            self._text_placement_color = QColor(
                int(max(0, min(255, r * 255))),
                int(max(0, min(255, g * 255))),
                int(max(0, min(255, b * 255))),
            )
        if fontsize is not None:
            self._text_placement_fontsize = max(6.0, float(fontsize))
        if self._text_placement_mode:
            self._refresh_text_placement_overlay()

    def eventFilter(self, a0, a1):  # type: ignore[no-untyped-def]
        if a1 is not None and a1.type() == QEvent.Type.Resize:
            if a0 is self.pdf_view or a0 is self.pdf_view.viewport():
                self._sync_region_overlay_geometry()
                if self._text_placement_mode:
                    self._refresh_text_placement_overlay()
        return super().eventFilter(a0, a1)

    def _sync_region_overlay_geometry(self) -> None:
        # pdf_view 전체 위에 덮음 (viewport 스크롤 포함 좌표계는 변환 시 보정)
        geo = self.pdf_view.rect()
        if self._region_overlay is not None:
            self._region_overlay.setGeometry(geo)
            if self._region_select_mode:
                self._region_overlay.raise_()
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

    def _refresh_text_placement_overlay(self) -> None:
        if self._text_placement_overlay is None or not self._text_placement_mode:
            return
        pts = self._text_placement_pts
        if pts is None:
            return
        page_display = self._page_display_rect_in_view()
        if page_display is None or self._doc is None:
            return
        page = max(0, min(self._current_page, self._total_pages - 1))
        try:
            page_size = self._doc.pagePointSize(page)
        except Exception:
            return
        view_rect = map_page_points_to_viewport_rect(
            pts[0],
            pts[1],
            pts[2],
            pts[3],
            page_display,
            float(page_size.width()),
            float(page_size.height()),
        )
        if view_rect is None:
            return
        zoom = float(self.pdf_view.zoomFactor() or 1.0)
        font_px = max(8, int(round(self._text_placement_fontsize * zoom)))
        box = QRect(
            int(round(view_rect.x())),
            int(round(view_rect.y())),
            max(24, int(round(view_rect.width()))),
            max(18, int(round(view_rect.height()))),
        )
        self._text_placement_overlay.set_content(
            text=self._text_placement_text,
            box=box,
            color=self._text_placement_color,
            font_px=font_px,
        )

    def _on_text_placement_box_moved(self, box: QRect) -> None:
        if self._doc is None or not self._text_placement_mode:
            return
        page_display = self._page_display_rect_in_view()
        if page_display is None:
            return
        page = max(0, min(self._current_page, self._total_pages - 1))
        try:
            page_size = self._doc.pagePointSize(page)
        except Exception:
            return
        mapped = map_viewport_rect_to_page_points(
            QRectF(box),
            page_display,
            float(page_size.width()),
            float(page_size.height()),
            min_size_pts=1.0,
        )
        if mapped is None:
            return
        self._text_placement_pts = mapped
        self.textPlacementMoved.emit(page + 1, mapped[0], mapped[1], mapped[2], mapped[3])

    def _on_text_placement_cancelled(self) -> None:
        self.set_text_placement_mode(False)

    def closeEvent(self, a0: QCloseEvent | None):
        try:
            self.set_region_select_mode(False)
            self.set_text_placement_mode(False)
            if self._doc is not None:
                self._doc.close()
        except Exception:
            logger.debug("Failed to close preview document on widget shutdown", exc_info=True)
        super().closeEvent(a0)
