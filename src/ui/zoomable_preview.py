"""
Zoomable Preview Widget for PDF Master v4.0
마우스 휠로 줌, 드래그로 패닝이 가능한 미리보기 위젯입니다.
"""

import logging

from PyQt6.QtCore import QEvent, QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QCloseEvent,
    QEnterEvent,
    QImage,
    QMouseEvent,
    QPainter,
    QPixmap,
    QResizeEvent,
    QWheelEvent,
)
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..core.i18n import tm
from ..core.optional_deps import fitz

logger = logging.getLogger(__name__)


class ZoomableGraphicsView(QGraphicsView):
    """줌/패닝 가능한 QGraphicsView"""

    zoomChanged = pyqtSignal(float)
    viewportResized = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom = 1.0
        self._min_zoom = 0.1
        self._max_zoom = 5.0
        self._zoom_step = 0.1
        self._fit_mode = True
        self._panning = False
        self._pan_start = QPointF()

        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setStyleSheet(
            """
            QGraphicsView {
                background-color: #1a1a2e;
                border: 1px solid #333;
                border-radius: 8px;
            }
            """
        )

        self._pixmap_item: QGraphicsPixmapItem | None = None

    def set_pixmap(self, pixmap: QPixmap, preserve_view: bool = False):
        """이미지를 씬에 설정하고 필요 시 현재 줌 상태를 유지한다."""
        previous_zoom = self._zoom
        viewport = self.viewport()
        previous_center = (
            self.mapToScene(viewport.rect().center()) if viewport is not None else QPointF()
        )
        preserve_custom_view = (
            preserve_view and self._pixmap_item is not None and not self._fit_mode
        )

        self._scene.clear()
        self._pixmap_item = None

        if pixmap and not pixmap.isNull():
            self._pixmap_item = self._scene.addPixmap(pixmap)
            self._scene.setSceneRect(QRectF(pixmap.rect()))
            if preserve_custom_view and previous_zoom > 0:
                self.resetTransform()
                self.scale(previous_zoom, previous_zoom)
                self._zoom = previous_zoom
                self.centerOn(previous_center)
                self.zoomChanged.emit(self._zoom)
            else:
                self.fit_in_view()
            return

        self.resetTransform()
        self._zoom = 1.0
        self._fit_mode = True
        self.zoomChanged.emit(self._zoom)

    def fit_in_view(self):
        """뷰에 맞춤"""
        if self._pixmap_item:
            self._fit_mode = True
            self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
            self._zoom = self.transform().m11()
            self.zoomChanged.emit(self._zoom)

    def set_zoom(self, zoom: float):
        """줌 레벨 설정"""
        zoom = max(self._min_zoom, min(self._max_zoom, zoom))
        if abs(zoom - self._zoom) < 0.001:
            return

        self._fit_mode = False
        scale = zoom / self._zoom
        self.scale(scale, scale)
        self._zoom = zoom
        self.zoomChanged.emit(self._zoom)

    def zoom_in(self):
        self.set_zoom(self._zoom + self._zoom_step)

    def zoom_out(self):
        self.set_zoom(self._zoom - self._zoom_step)

    def reset_zoom(self):
        """줌 리셋 (100%)"""
        self.resetTransform()
        self._fit_mode = False
        self._zoom = 1.0
        self.zoomChanged.emit(self._zoom)

    @property
    def zoom_level(self) -> float:
        return self._zoom

    def wheelEvent(self, event: QWheelEvent | None):
        if event is None:
            return
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom_in()
        elif delta < 0:
            self.zoom_out()
        event.accept()

    def mousePressEvent(self, event: QMouseEvent | None):
        if event is None:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent | None):
        if event is None:
            return
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            hbar = self.horizontalScrollBar()
            vbar = self.verticalScrollBar()
            if hbar is not None:
                hbar.setValue(int(hbar.value() - delta.x()))
            if vbar is not None:
                vbar.setValue(int(vbar.value() - delta.y()))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent | None):
        if event is None:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._panning = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def enterEvent(self, event: QEnterEvent | None):
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().enterEvent(event)

    def leaveEvent(self, a0: QEvent | None):
        self.unsetCursor()
        super().leaveEvent(a0)

    def resizeEvent(self, event: QResizeEvent | None):
        super().resizeEvent(event)
        if self._fit_mode and self._pixmap_item:
            self.fit_in_view()
        self.viewportResized.emit()


class PreviewSearchLineEdit(QLineEdit):
    submitRequested = pyqtSignal()
    previousRequested = pyqtSignal()
    escapePressed = pyqtSignal()

    def keyPressEvent(self, event):
        if event is None:
            return
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.previousRequested.emit()
            else:
                self.submitRequested.emit()
            event.accept()
            return
        if key == Qt.Key.Key_Escape:
            self.escapePressed.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class ZoomablePreviewWidget(QWidget):
    """
    줌/패닝 컨트롤이 포함된 미리보기 위젯.

    Features:
        - 마우스 휠 줌
        - 드래그 패닝
        - 줌 슬라이더
        - 뷰에 맞춤/100% 버튼
        - 내부 페이지 네비게이션
        - 외부 pixmap 주입 기반 controlled mode
    """

    zoomChanged = pyqtSignal(float)
    pageChanged = pyqtSignal(int)
    renderRequested = pyqtSignal()
    searchRequested = pyqtSignal(str)
    searchStepRequested = pyqtSignal(int)
    searchCleared = pyqtSignal()
    searchVisibilityChanged = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pdf_path = ""
        self._current_page = 0
        self._total_pages = 0
        self._navigation_enabled = False
        self._controlled_mode = False
        self._search_visible = False
        self._search_available = False
        self._active_search_query = ""
        self._doc = None

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self.renderRequested.emit)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        zoom_bar = QHBoxLayout()
        zoom_bar.setSpacing(8)

        btn_zoom_out = QPushButton("−")
        btn_zoom_out.setFixedSize(28, 28)
        btn_zoom_out.setToolTip(tm.get("tooltip_zoom_out"))
        btn_zoom_out.clicked.connect(self._on_zoom_out)
        zoom_bar.addWidget(btn_zoom_out)

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 500)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(120)
        self.zoom_slider.valueChanged.connect(self._on_slider_changed)
        zoom_bar.addWidget(self.zoom_slider)

        btn_zoom_in = QPushButton("+")
        btn_zoom_in.setFixedSize(28, 28)
        btn_zoom_in.setToolTip(tm.get("tooltip_zoom_in"))
        btn_zoom_in.clicked.connect(self._on_zoom_in)
        zoom_bar.addWidget(btn_zoom_in)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(50)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_label.setStyleSheet("color: #888;")
        zoom_bar.addWidget(self.zoom_label)
        zoom_bar.addStretch()

        self.btn_toggle_search = QPushButton()
        self.btn_toggle_search.setObjectName("secondaryBtn")
        self.btn_toggle_search.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
        )
        self.btn_toggle_search.clicked.connect(self._toggle_search_panel)
        zoom_bar.addWidget(self.btn_toggle_search)

        btn_fit = QPushButton(tm.get("btn_fit_view"))
        btn_fit.setFixedHeight(28)
        btn_fit.setToolTip(tm.get("tooltip_fit_view"))
        btn_fit.clicked.connect(self._on_fit_view)
        zoom_bar.addWidget(btn_fit)

        btn_100 = QPushButton("1:1")
        btn_100.setFixedSize(40, 28)
        btn_100.setToolTip(tm.get("tooltip_actual_size"))
        btn_100.clicked.connect(self._on_reset_zoom)
        zoom_bar.addWidget(btn_100)

        layout.addLayout(zoom_bar)

        self.search_bar = QFrame()
        search_layout = QHBoxLayout(self.search_bar)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(8)

        self.search_input = PreviewSearchLineEdit()
        self.search_input.setPlaceholderText(tm.get("ph_preview_search"))
        self.search_input.setClearButtonEnabled(True)
        self.search_input.submitRequested.connect(self._on_search_submit)
        self.search_input.previousRequested.connect(self._on_search_prev_requested)
        self.search_input.escapePressed.connect(self._handle_search_escape)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        search_layout.addWidget(self.search_input, 1)

        self.btn_search_apply = QPushButton(tm.get("btn_preview_search"))
        self.btn_search_apply.setObjectName("secondaryBtn")
        self.btn_search_apply.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
        )
        self.btn_search_apply.clicked.connect(self._emit_search_request)
        search_layout.addWidget(self.btn_search_apply)

        self.search_status_label = QLabel()
        self.search_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.search_status_label.setMinimumWidth(88)
        self.search_status_label.setStyleSheet("color: #888; font-size: 12px;")
        search_layout.addWidget(self.search_status_label)

        self.btn_search_prev = QPushButton("◀")
        self.btn_search_prev.setObjectName("iconBtn")
        self.btn_search_prev.setToolTip(tm.get("tooltip_preview_search_prev"))
        self.btn_search_prev.clicked.connect(lambda: self.searchStepRequested.emit(-1))
        search_layout.addWidget(self.btn_search_prev)

        self.btn_search_next = QPushButton("▶")
        self.btn_search_next.setObjectName("iconBtn")
        self.btn_search_next.setToolTip(tm.get("tooltip_preview_search_next"))
        self.btn_search_next.clicked.connect(lambda: self.searchStepRequested.emit(1))
        search_layout.addWidget(self.btn_search_next)

        self.btn_search_clear = QPushButton("✕")
        self.btn_search_clear.setObjectName("iconBtn")
        self.btn_search_clear.setToolTip(tm.get("tooltip_preview_search_clear"))
        self.btn_search_clear.clicked.connect(self._clear_search)
        search_layout.addWidget(self.btn_search_clear)

        layout.addWidget(self.search_bar)

        self.graphics_view = ZoomableGraphicsView()
        self.graphics_view.zoomChanged.connect(self._on_zoom_changed)
        self.graphics_view.viewportResized.connect(self._on_viewport_resized)
        layout.addWidget(self.graphics_view, 1)

        nav_bar = QHBoxLayout()

        self.btn_prev = QPushButton(tm.get("prev_page"))
        self.btn_prev.setMinimumHeight(30)
        self.btn_prev.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.btn_prev.clicked.connect(self._prev_page)
        nav_bar.addWidget(self.btn_prev)

        self.page_label = QLabel("0 / 0")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setStyleSheet(
            "font-weight: bold; min-width: 60px; color: #eaeaea;"
        )
        nav_bar.addWidget(self.page_label)

        self.btn_next = QPushButton(tm.get("next_page"))
        self.btn_next.setMinimumHeight(30)
        self.btn_next.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.btn_next.clicked.connect(self._next_page)
        nav_bar.addWidget(self.btn_next)

        layout.addLayout(nav_bar)
        self.set_navigation_enabled(False)
        self.set_search_available(False)
        self.set_controlled_mode(False)
        self.set_search_panel_visible(False)

    def load_pdf(self, pdf_path: str):
        """Standalone mode: widget가 직접 PDF를 연다."""
        self.set_controlled_mode(False)
        self._close_doc()

        if not pdf_path:
            self.clear()
            return

        try:
            self._doc = fitz.open(pdf_path)
            self._pdf_path = pdf_path
            self._total_pages = len(self._doc)
            self.set_navigation_enabled(self._total_pages > 0)
            self.go_to_page(0, emit_signal=False)
            self._render_current_page()
        except Exception as exc:
            logger.error("Failed to load PDF: %s", exc)

    def _close_doc(self):
        if self._doc:
            try:
                self._doc.close()
                logger.debug("ZoomablePreviewWidget: document closed")
            except Exception as exc:
                logger.warning("Error closing document: %s", exc)
            finally:
                self._doc = None

    def clear(self):
        self._close_doc()
        self._pdf_path = ""
        self.set_controlled_mode(False)
        self.graphics_view.set_pixmap(QPixmap())
        self.set_page_state(0, 0)
        self.set_navigation_enabled(False)
        self.clear_search_state(clear_query=True)

    def clear_display(self):
        """Controlled mode에서 표시 상태만 비운다."""
        self.graphics_view.set_pixmap(QPixmap())
        self.set_page_state(0, 0)
        self.set_navigation_enabled(False)

    def set_controlled_mode(self, enabled: bool = True):
        self._controlled_mode = bool(enabled)
        if not self._controlled_mode:
            self._search_visible = False
        self.btn_toggle_search.setVisible(self._controlled_mode)
        self.search_bar.setVisible(self._controlled_mode and self._search_visible)
        self._update_search_toggle_text()

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

    def set_search_available(self, enabled: bool):
        self._search_available = bool(enabled)
        self.search_input.setEnabled(self._search_available)
        self.btn_search_apply.setEnabled(
            self._search_available and bool(self.search_input.text().strip())
        )
        if not self._search_available:
            self.btn_search_prev.setEnabled(False)
            self.btn_search_next.setEnabled(False)
            self.btn_search_clear.setEnabled(bool(self.search_input.text().strip()))
            self.search_status_label.setText(tm.get("preview_search_status_unavailable"))
        elif not self._active_search_query:
            self.search_status_label.setText(tm.get("preview_search_status_idle"))

    def set_search_panel_visible(self, visible: bool):
        next_visible = bool(visible)
        if self._search_visible == next_visible:
            self.search_bar.setVisible(self._controlled_mode and next_visible)
            self.btn_toggle_search.setVisible(self._controlled_mode)
            self._update_search_toggle_text()
            return
        self._search_visible = next_visible
        self.search_bar.setVisible(self._controlled_mode and next_visible)
        self.btn_toggle_search.setVisible(self._controlled_mode)
        self._update_search_toggle_text()
        if self._controlled_mode and next_visible:
            self.focus_search_input(select_all=True)
        self.searchVisibilityChanged.emit(self._search_visible)

    def set_search_query(self, query: str):
        self.search_input.blockSignals(True)
        self.search_input.setText(query)
        self.search_input.blockSignals(False)
        self.btn_search_apply.setEnabled(
            self._search_available and bool(self.search_input.text().strip())
        )
        self.btn_search_clear.setEnabled(bool(self.search_input.text().strip()))

    def clear_search_state(self, clear_query: bool = False, message: str | None = None):
        if clear_query:
            self.set_search_query("")
        self._active_search_query = ""
        if message is not None:
            self.search_status_label.setText(message)
        elif self._search_available:
            self.search_status_label.setText(tm.get("preview_search_status_idle"))
        else:
            self.search_status_label.setText(tm.get("preview_search_status_unavailable"))
        self.btn_search_prev.setEnabled(False)
        self.btn_search_next.setEnabled(False)
        self.btn_search_clear.setEnabled(bool(self.search_input.text().strip()))

    def set_search_result_state(
        self,
        current_result: int | None,
        total_results: int,
        *,
        query: str | None = None,
        message: str | None = None,
    ):
        if query is not None:
            self._active_search_query = query.strip()
        total_results = max(0, int(total_results))
        if message is not None:
            self.search_status_label.setText(message)
        elif total_results <= 0:
            self.search_status_label.setText(tm.get("preview_search_status_no_results"))
        else:
            current_index = 1
            if current_result is not None:
                current_index = max(1, min(int(current_result) + 1, total_results))
            self.search_status_label.setText(
                tm.get("preview_search_status_count", current_index, total_results)
            )
        has_results = self._search_available and total_results > 0
        self.btn_search_prev.setEnabled(has_results)
        self.btn_search_next.setEnabled(has_results)
        self.btn_search_clear.setEnabled(
            bool(self.search_input.text().strip()) or total_results > 0
        )

    def set_preview_pixmap(
        self,
        pixmap: QPixmap,
        current_page: int | None = None,
        total_pages: int | None = None,
        preserve_view: bool = True,
    ):
        """Controlled mode: 외부에서 렌더한 pixmap을 주입한다."""
        self.set_controlled_mode(True)
        next_current = self._current_page if current_page is None else current_page
        next_total = self._total_pages if total_pages is None else total_pages
        self.set_page_state(next_current, next_total)
        self.graphics_view.set_pixmap(pixmap, preserve_view=preserve_view)

    def display_size(self):
        viewport = self.graphics_view.viewport()
        if viewport is None:
            return self.graphics_view.size()
        return viewport.size()

    def _update_navigation_buttons(self):
        enabled = self._navigation_enabled and self._total_pages > 0
        self.btn_prev.setEnabled(enabled and self._current_page > 0)
        self.btn_next.setEnabled(enabled and self._current_page < self._total_pages - 1)

    def _render_current_page(self):
        if not self._doc or self._current_page >= len(self._doc):
            return

        page = self._doc[self._current_page]

        zoom = min(4.0, max(2.0, self.graphics_view.zoom_level * 2))
        page_width = page.rect.width * zoom
        page_height = page.rect.height * zoom
        max_dimension = 8000
        if page_width > max_dimension or page_height > max_dimension:
            zoom = max_dimension / max(page.rect.width, page.rect.height)

        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        img_data = bytes(pix.samples)
        fmt = (
            QImage.Format.Format_RGBA8888
            if pix.alpha
            else QImage.Format.Format_RGB888
        )
        img = QImage(img_data, pix.width, pix.height, pix.stride, fmt)
        pixmap = QPixmap.fromImage(img.copy())

        self.set_page_state(self._current_page, self._total_pages)
        self.graphics_view.set_pixmap(pixmap, preserve_view=False)

    def _prev_page(self):
        if self._current_page > 0:
            self.go_to_page(self._current_page - 1, emit_signal=True)

    def _next_page(self):
        if self._current_page < self._total_pages - 1:
            self.go_to_page(self._current_page + 1, emit_signal=True)

    def go_to_page(self, page_index: int, emit_signal: bool = False):
        if 0 <= page_index < self._total_pages:
            self._current_page = page_index
            self.set_page_state(self._current_page, self._total_pages)
            if self._doc and not self._controlled_mode:
                self._render_current_page()
            if emit_signal:
                self.pageChanged.emit(self._current_page)

    def _on_zoom_in(self):
        self.graphics_view.zoom_in()

    def _on_zoom_out(self):
        self.graphics_view.zoom_out()

    def _on_fit_view(self):
        self.graphics_view.fit_in_view()

    def _on_reset_zoom(self):
        self.graphics_view.reset_zoom()

    def _on_slider_changed(self, value: int):
        self.graphics_view.set_zoom(value / 100.0)

    def _on_zoom_changed(self, zoom: float):
        percent = int(zoom * 100)
        self.zoom_label.setText(f"{percent}%")
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(percent)
        self.zoom_slider.blockSignals(False)
        self.zoomChanged.emit(zoom)

    def _on_viewport_resized(self):
        if self._controlled_mode and self._total_pages > 0:
            self._resize_timer.start(150)

    def _toggle_search_panel(self):
        self.set_search_panel_visible(not self._search_visible)

    def _update_search_toggle_text(self):
        toggle_key = (
            "btn_preview_search_hide"
            if self._search_visible
            else "btn_preview_search_show"
        )
        tooltip_key = (
            "tooltip_preview_search_hide"
            if self._search_visible
            else "tooltip_preview_search_show"
        )
        self.btn_toggle_search.setText(tm.get(toggle_key))
        self.btn_toggle_search.setToolTip(tm.get(tooltip_key))

    def _emit_search_request(self):
        query = self.search_input.text().strip()
        if not query:
            self._clear_search()
            return
        self.searchRequested.emit(query)

    def _clear_search(self):
        self.search_input.clear()

    def focus_search_input(self, select_all: bool = False):
        if not self._controlled_mode:
            return
        self.search_input.setFocus(Qt.FocusReason.ShortcutFocusReason)
        if select_all:
            self.search_input.selectAll()

    def _on_search_submit(self):
        query = self.search_input.text().strip()
        if not query:
            self._clear_search()
            return
        if query == self._active_search_query and self.btn_search_next.isEnabled():
            self.searchStepRequested.emit(1)
            return
        if query != self._active_search_query:
            self.searchRequested.emit(query)

    def _on_search_prev_requested(self):
        if self.btn_search_prev.isEnabled():
            self.searchStepRequested.emit(-1)

    def _handle_search_escape(self):
        if self.search_input.text().strip():
            self.search_input.clear()
            return
        if self._search_visible:
            self.set_search_panel_visible(False)

    def _on_search_text_changed(self, text: str):
        query = text.strip()
        self.btn_search_apply.setEnabled(self._search_available and bool(query))
        self.btn_search_clear.setEnabled(bool(query) or bool(self._active_search_query))
        if not query:
            self._active_search_query = ""
            self.searchCleared.emit()
            return
        if query != self._active_search_query:
            self.search_status_label.setText(tm.get("preview_search_status_pending"))
            self.btn_search_prev.setEnabled(False)
            self.btn_search_next.setEnabled(False)

    def set_theme(self, is_dark: bool):
        if is_dark:
            self.graphics_view.setStyleSheet(
                """
                QGraphicsView {
                    background-color: #1a1a2e;
                    border: 1px solid #333;
                    border-radius: 8px;
                }
                """
            )
            self.page_label.setStyleSheet(
                "font-weight: bold; min-width: 60px; color: #eaeaea;"
            )
            self.search_status_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        else:
            self.graphics_view.setStyleSheet(
                """
                QGraphicsView {
                    background-color: #f0f0f0;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                }
                """
            )
            self.page_label.setStyleSheet(
                "font-weight: bold; min-width: 60px; color: #333;"
            )
            self.search_status_label.setStyleSheet("color: #64748b; font-size: 12px;")

    def closeEvent(self, a0: QCloseEvent | None):
        self._close_doc()
        super().closeEvent(a0)
