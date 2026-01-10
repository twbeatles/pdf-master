"""
Zoomable Preview Widget for PDF Master v4.0
마우스 휠로 줌, 드래그로 패닝이 가능한 미리보기 위젯입니다.
"""
import fitz
import logging
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QWidget,
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider
)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF
from PyQt6.QtGui import QPixmap, QImage, QWheelEvent, QMouseEvent, QPainter

logger = logging.getLogger(__name__)


class ZoomableGraphicsView(QGraphicsView):
    """줌/패닝 가능한 QGraphicsView"""
    
    zoomChanged = pyqtSignal(float)  # 줌 레벨 변경 시그널
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom = 1.0
        self._min_zoom = 0.1
        self._max_zoom = 5.0
        self._zoom_step = 0.1
        self._panning = False
        self._pan_start = QPointF()
        
        # 그래픽스 씬 설정
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        
        # 렌더링 품질 설정
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | 
            QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        
        # 스타일
        self.setStyleSheet("""
            QGraphicsView {
                background-color: #1a1a2e;
                border: 1px solid #333;
                border-radius: 8px;
            }
        """)
        
        self._pixmap_item: QGraphicsPixmapItem = None
    
    def set_pixmap(self, pixmap: QPixmap):
        """이미지 설정"""
        self._scene.clear()
        if pixmap and not pixmap.isNull():
            self._pixmap_item = self._scene.addPixmap(pixmap)
            self._scene.setSceneRect(QRectF(pixmap.rect()))
            self.fit_in_view()
    
    def fit_in_view(self):
        """뷰에 맞춤"""
        if self._pixmap_item:
            self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
            # 현재 줌 레벨 계산
            self._zoom = self.transform().m11()
            self.zoomChanged.emit(self._zoom)
    
    def set_zoom(self, zoom: float):
        """줌 레벨 설정"""
        zoom = max(self._min_zoom, min(self._max_zoom, zoom))
        if abs(zoom - self._zoom) < 0.001:
            return
            
        scale = zoom / self._zoom
        self.scale(scale, scale)
        self._zoom = zoom
        self.zoomChanged.emit(self._zoom)
    
    def zoom_in(self):
        """줌 인"""
        self.set_zoom(self._zoom + self._zoom_step)
    
    def zoom_out(self):
        """줌 아웃"""
        self.set_zoom(self._zoom - self._zoom_step)
    
    def reset_zoom(self):
        """줌 리셋 (100%)"""
        self.resetTransform()
        self._zoom = 1.0
        self.zoomChanged.emit(self._zoom)
    
    @property
    def zoom_level(self) -> float:
        return self._zoom
    
    def wheelEvent(self, event: QWheelEvent):
        """마우스 휠로 줌"""
        delta = event.angleDelta().y()
        if delta > 0:
            self.zoom_in()
        elif delta < 0:
            self.zoom_out()
        event.accept()
    
    def mousePressEvent(self, event: QMouseEvent):
        """마우스 드래그 시작 (패닝)"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """마우스 드래그 (패닝)"""
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            
            # 스크롤바를 이용한 패닝
            h_bar = self.horizontalScrollBar()
            v_bar = self.verticalScrollBar()
            h_bar.setValue(int(h_bar.value() - delta.x()))
            v_bar.setValue(int(v_bar.value() - delta.y()))
            event.accept()
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """마우스 드래그 종료"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._panning = False
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)
    
    def enterEvent(self, event):
        """마우스 진입 시 커서 변경"""
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """마우스 이탈 시 커서 복원"""
        self.unsetCursor()
        super().leaveEvent(event)


class ZoomablePreviewWidget(QWidget):
    """
    줌/패닝 컨트롤이 포함된 미리보기 위젯
    
    Features:
        - 마우스 휠 줌
        - 드래그 패닝
        - 줌 슬라이더
        - 뷰에 맞춤/100% 버튼
    """
    
    zoomChanged = pyqtSignal(float)
    pageChanged = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pdf_path = ""
        self._current_page = 0
        self._total_pages = 0
        self._doc = None
        
        self._setup_ui()
        
        # Note: 리소스 정리는 closeEvent에서 수행됨\n        # destroyed 시그널은 객체가 이미 삭제된 후에 발생하므로 사용하지 않음
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 줌 컨트롤 바
        zoom_bar = QHBoxLayout()
        zoom_bar.setSpacing(8)
        
        # 줌 버튼
        btn_zoom_out = QPushButton("−")
        btn_zoom_out.setFixedSize(28, 28)
        btn_zoom_out.setToolTip("줌 아웃")
        btn_zoom_out.clicked.connect(self._on_zoom_out)
        zoom_bar.addWidget(btn_zoom_out)
        
        # 줌 슬라이더
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 500)  # 10% ~ 500%
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(120)
        self.zoom_slider.valueChanged.connect(self._on_slider_changed)
        zoom_bar.addWidget(self.zoom_slider)
        
        btn_zoom_in = QPushButton("+")
        btn_zoom_in.setFixedSize(28, 28)
        btn_zoom_in.setToolTip("줌 인")
        btn_zoom_in.clicked.connect(self._on_zoom_in)
        zoom_bar.addWidget(btn_zoom_in)
        
        # 줌 레벨 표시
        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(50)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_label.setStyleSheet("color: #888;")
        zoom_bar.addWidget(self.zoom_label)
        
        zoom_bar.addStretch()
        
        # 뷰에 맞춤 버튼
        btn_fit = QPushButton("🔲 맞춤")
        btn_fit.setFixedHeight(28)
        btn_fit.setToolTip("뷰에 맞춤")
        btn_fit.clicked.connect(self._on_fit_view)
        zoom_bar.addWidget(btn_fit)
        
        # 100% 버튼
        btn_100 = QPushButton("1:1")
        btn_100.setFixedSize(40, 28)
        btn_100.setToolTip("100%")
        btn_100.clicked.connect(self._on_reset_zoom)
        zoom_bar.addWidget(btn_100)
        
        layout.addLayout(zoom_bar)
        
        # 그래픽스 뷰
        self.graphics_view = ZoomableGraphicsView()
        self.graphics_view.zoomChanged.connect(self._on_zoom_changed)
        layout.addWidget(self.graphics_view, 1)
        
        # 페이지 네비게이션
        nav_bar = QHBoxLayout()
        
        self.btn_prev = QPushButton("◀ PREV")
        self.btn_prev.setFixedSize(80, 30)
        self.btn_prev.clicked.connect(self._prev_page)
        nav_bar.addWidget(self.btn_prev)
        
        self.page_label = QLabel("1 / 1")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setStyleSheet("font-weight: bold; min-width: 60px; color: #eaeaea;")
        nav_bar.addWidget(self.page_label)
        
        self.btn_next = QPushButton("NEXT ▶")
        self.btn_next.setFixedSize(80, 30)
        self.btn_next.clicked.connect(self._next_page)
        nav_bar.addWidget(self.btn_next)
        
        layout.addLayout(nav_bar)
    
    def load_pdf(self, pdf_path: str):
        """PDF 파일 로드"""
        self._close_doc()
        
        if not pdf_path:
            return
            
        try:
            self._doc = fitz.open(pdf_path)
            self._pdf_path = pdf_path
            self._total_pages = len(self._doc)
            self._current_page = 0
            self._render_current_page()
        except Exception as e:
            logger.error(f"Failed to load PDF: {e}")
    
    def _close_doc(self):
        """문서 닫기 (안전하게)"""
        if self._doc:
            try:
                self._doc.close()
                logger.debug("ZoomablePreviewWidget: document closed")
            except Exception as e:
                logger.warning(f"Error closing document: {e}")
            finally:
                self._doc = None
    
    def clear(self):
        """리소스 해제 및 디스플레이 초기화"""
        self._close_doc()
        self._pdf_path = ""
        self._current_page = 0
        self._total_pages = 0
        self.graphics_view.set_pixmap(QPixmap())
        self.page_label.setText("0 / 0")
    
    def _render_current_page(self):
        """현재 페이지 렌더링"""
        if not self._doc or self._current_page >= len(self._doc):
            return
            
        page = self._doc[self._current_page]
        
        # 고해상도 렌더링 (줌에 대응, 메모리 제한을 위해 최대 4.0으로 제한)
        zoom = min(4.0, max(2.0, self.graphics_view.zoom_level * 2))
        
        # 대용량 페이지 메모리 보호: 렌더링 결과가 너무 크면 줌 감소
        page_width = page.rect.width * zoom
        page_height = page.rect.height * zoom
        max_dimension = 8000  # 최대 8000px
        if page_width > max_dimension or page_height > max_dimension:
            zoom = max_dimension / max(page.rect.width, page.rect.height)
        
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # QPixmap 변환
        img_data = bytes(pix.samples)
        fmt = QImage.Format.Format_RGBA8888 if pix.alpha else QImage.Format.Format_RGB888
        img = QImage(img_data, pix.width, pix.height, pix.stride, fmt)
        pixmap = QPixmap.fromImage(img.copy())
        
        self.graphics_view.set_pixmap(pixmap)
        self.page_label.setText(f"{self._current_page + 1} / {self._total_pages}")
    
    def _prev_page(self):
        """이전 페이지"""
        if self._current_page > 0:
            self._current_page -= 1
            self._render_current_page()
            self.pageChanged.emit(self._current_page)
    
    def _next_page(self):
        """다음 페이지"""
        if self._current_page < self._total_pages - 1:
            self._current_page += 1
            self._render_current_page()
            self.pageChanged.emit(self._current_page)
    
    def go_to_page(self, page_index: int):
        """특정 페이지로 이동"""
        if 0 <= page_index < self._total_pages:
            self._current_page = page_index
            self._render_current_page()
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
        """슬라이더 값 변경"""
        zoom = value / 100.0
        self.graphics_view.set_zoom(zoom)
    
    def _on_zoom_changed(self, zoom: float):
        """줌 레벨 변경 시"""
        percent = int(zoom * 100)
        self.zoom_label.setText(f"{percent}%")
        
        # 슬라이더 업데이트 (시그널 루프 방지)
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(percent)
        self.zoom_slider.blockSignals(False)
        
        self.zoomChanged.emit(zoom)
    
    def set_theme(self, is_dark: bool):
        """테마 설정"""
        if is_dark:
            self.graphics_view.setStyleSheet("""
                QGraphicsView {
                    background-color: #1a1a2e;
                    border: 1px solid #333;
                    border-radius: 8px;
                }
            """)
            self.page_label.setStyleSheet("font-weight: bold; min-width: 60px; color: #eaeaea;")
        else:
            self.graphics_view.setStyleSheet("""
                QGraphicsView {
                    background-color: #f0f0f0;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                }
            """)
            self.page_label.setStyleSheet("font-weight: bold; min-width: 60px; color: #333;")
    
    def closeEvent(self, event):
        """정리"""
        self._close_doc()
        super().closeEvent(event)
