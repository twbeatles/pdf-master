"""
Thumbnail Grid Widget for PDF Master v4.0
PDF의 모든 페이지를 그리드 형태로 표시하는 위젯입니다.
"""
import fitz
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
    QScrollArea, QPushButton, QFrame, QSpinBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QThread, pyqtSlot
from PyQt6.QtGui import QPixmap, QImage, QCursor

logger = logging.getLogger(__name__)


class ThumbnailLoaderThread(QThread):
    """백그라운드에서 썸네일을 로드하는 스레드"""
    thumbnail_ready = pyqtSignal(int, QPixmap)  # (page_index, pixmap)
    loading_complete = pyqtSignal()
    progress = pyqtSignal(int)  # 0-100
    
    def __init__(self, pdf_path: str, size: int = 150):
        super().__init__()
        self.pdf_path = pdf_path
        self.size = size
        self._is_cancelled = False
        
    def cancel(self):
        self._is_cancelled = True
    
    def run(self):
        doc = None
        try:
            doc = fitz.open(self.pdf_path)
            total = len(doc)
            
            for i in range(total):
                if self._is_cancelled:
                    break
                    
                page = doc[i]
                # 썸네일 크기에 맞게 스케일 조정
                scale = self.size / max(page.rect.width, page.rect.height)
                mat = fitz.Matrix(scale, scale)
                pix = page.get_pixmap(matrix=mat)
                
                # QPixmap으로 변환
                img_data = bytes(pix.samples)
                fmt = QImage.Format.Format_RGBA8888 if pix.alpha else QImage.Format.Format_RGB888
                img = QImage(img_data, pix.width, pix.height, pix.stride, fmt)
                pixmap = QPixmap.fromImage(img.copy())
                
                self.thumbnail_ready.emit(i, pixmap)
                self.progress.emit(int((i + 1) / total * 100))
                
            self.loading_complete.emit()
            
        except Exception as e:
            logger.error(f"Thumbnail loading failed: {e}")
        finally:
            if doc:
                doc.close()


class ThumbnailLabel(QFrame):
    """클릭 가능한 썸네일 라벨"""
    clicked = pyqtSignal(int)  # page_index
    
    def __init__(self, page_index: int, parent=None):
        super().__init__(parent)
        self.page_index = page_index
        self._selected = False
        
        self.setFixedSize(160, 200)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)
        
        # 썸네일 이미지
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(140, 160)
        self.image_label.setStyleSheet("background: #1a1a2e; border-radius: 4px;")
        layout.addWidget(self.image_label)
        
        # 페이지 번호
        self.page_label = QLabel(f"Page {page_index + 1}")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.page_label)
        
        self._update_style()
    
    def set_pixmap(self, pixmap: QPixmap):
        """썸네일 이미지 설정"""
        scaled = pixmap.scaled(
            140, 160,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)
    
    def set_selected(self, selected: bool):
        """선택 상태 설정"""
        self._selected = selected
        self._update_style()
    
    def _update_style(self):
        """스타일 업데이트"""
        if self._selected:
            self.setStyleSheet("""
                ThumbnailLabel {
                    background: rgba(79, 140, 255, 0.2);
                    border: 2px solid #4f8cff;
                    border-radius: 8px;
                }
            """)
            self.page_label.setStyleSheet("color: #4f8cff; font-size: 11px; font-weight: bold;")
        else:
            self.setStyleSheet("""
                ThumbnailLabel {
                    background: rgba(30, 30, 50, 0.5);
                    border: 1px solid #333;
                    border-radius: 8px;
                }
                ThumbnailLabel:hover {
                    background: rgba(79, 140, 255, 0.1);
                    border-color: #4f8cff;
                }
            """)
            self.page_label.setStyleSheet("color: #888; font-size: 11px;")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.page_index)
        super().mousePressEvent(event)


class ThumbnailGridWidget(QWidget):
    """
    PDF 페이지를 그리드 형태로 표시하는 위젯
    
    Signals:
        pageSelected(int): 페이지가 선택되면 인덱스 emit
        pageDoubleClicked(int): 페이지 더블클릭 시 인덱스 emit
    """
    pageSelected = pyqtSignal(int)
    pageDoubleClicked = pyqtSignal(int)
    loadingProgress = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pdf_path = ""
        self._thumbnails: list[ThumbnailLabel] = []
        self._selected_index = -1
        self._columns = 4
        self._loader_thread: ThumbnailLoaderThread = None
        self._is_dark_theme = True
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 컨트롤 바
        control_bar = QHBoxLayout()
        
        control_bar.addWidget(QLabel("열 수:"))
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
        
        # 스크롤 영역
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        
        self.scroll_area.setWidget(self.grid_container)
        layout.addWidget(self.scroll_area)
        
        # 로딩 상태 표시
        self.loading_label = QLabel("📄 PDF 파일을 선택하세요")
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.setStyleSheet("color: #666; font-size: 14px; padding: 40px;")
        self.grid_layout.addWidget(self.loading_label, 0, 0)
    
    def load_pdf(self, pdf_path: str):
        """PDF 파일 로드 및 썸네일 생성"""
        if not pdf_path:
            return
            
        # 기존 로더 취소
        if self._loader_thread and self._loader_thread.isRunning():
            self._loader_thread.cancel()
            self._loader_thread.wait()
        
        self._pdf_path = pdf_path
        self._clear_thumbnails()
        
        # PDF 페이지 수 확인
        doc = None
        try:
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            self.info_label.setText(f"페이지: {page_count}")
            
            # 썸네일 플레이스홀더 생성
            for i in range(page_count):
                thumb = ThumbnailLabel(i)
                thumb.clicked.connect(self._on_thumbnail_clicked)
                self._thumbnails.append(thumb)
                
            self._arrange_grid()
            
        except Exception as e:
            logger.error(f"Failed to open PDF: {e}")
            self.loading_label.setText(f"❌ PDF 로드 실패: {e}")
            self.loading_label.show()
            return
        finally:
            if doc:
                doc.close()
        
        # 백그라운드 썸네일 로드 시작
        self._loader_thread = ThumbnailLoaderThread(pdf_path, 150)
        self._loader_thread.thumbnail_ready.connect(self._on_thumbnail_ready)
        self._loader_thread.progress.connect(self.loadingProgress.emit)
        self._loader_thread.loading_complete.connect(self._on_loading_complete)
        self._loader_thread.start()
    
    def _clear_thumbnails(self):
        """모든 썸네일 제거"""
        for thumb in self._thumbnails:
            thumb.deleteLater()
        self._thumbnails.clear()
        self._selected_index = -1
        
        # 그리드 레이아웃 클리어
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _arrange_grid(self):
        """그리드 재배열"""
        # 기존 배치 제거 (위젯은 유지)
        for i in reversed(range(self.grid_layout.count())):
            self.grid_layout.takeAt(i)
        
        # 새 배치
        for i, thumb in enumerate(self._thumbnails):
            row = i // self._columns
            col = i % self._columns
            self.grid_layout.addWidget(thumb, row, col)
        
        if self._thumbnails:
            self.loading_label.hide()
        else:
            self.loading_label.show()
    
    @pyqtSlot(int, QPixmap)
    def _on_thumbnail_ready(self, index: int, pixmap: QPixmap):
        """썸네일 로드 완료 시 호출"""
        if index < len(self._thumbnails):
            self._thumbnails[index].set_pixmap(pixmap)
    
    @pyqtSlot()
    def _on_loading_complete(self):
        """모든 썸네일 로드 완료"""
        logger.debug("Thumbnail loading complete")
    
    def _on_columns_changed(self, value: int):
        """열 수 변경 시"""
        self._columns = value
        self._arrange_grid()
    
    def _on_thumbnail_clicked(self, page_index: int):
        """썸네일 클릭 시"""
        # 이전 선택 해제
        if 0 <= self._selected_index < len(self._thumbnails):
            self._thumbnails[self._selected_index].set_selected(False)
        
        # 새 선택
        self._selected_index = page_index
        if 0 <= page_index < len(self._thumbnails):
            self._thumbnails[page_index].set_selected(True)
        
        self.pageSelected.emit(page_index)
    
    def get_selected_page(self) -> int:
        """현재 선택된 페이지 인덱스 반환 (-1이면 선택 없음)"""
        return self._selected_index
    
    def select_page(self, index: int):
        """페이지 선택"""
        self._on_thumbnail_clicked(index)
        
        # 선택된 페이지로 스크롤
        if 0 <= index < len(self._thumbnails):
            self.scroll_area.ensureWidgetVisible(self._thumbnails[index])
    
    def set_theme(self, is_dark: bool):
        """테마 설정"""
        self._is_dark_theme = is_dark
        # 테마에 따른 스타일 업데이트 가능
    
    def closeEvent(self, event):
        """위젯 종료 시 스레드 정리"""
        if self._loader_thread and self._loader_thread.isRunning():
            self._loader_thread.cancel()
            self._loader_thread.wait()
        super().closeEvent(event)
