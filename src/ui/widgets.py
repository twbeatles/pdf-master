import os
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QPushButton, QFileDialog, 
    QListWidget, QListWidgetItem, QAbstractItemView, QMenu, 
    QToolButton, QHBoxLayout, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QEvent
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from ..core.settings import load_settings

class WheelEventFilter(QObject):
    """QSpinBox, QComboBox 등에서 스크롤 휠로 값이 변경되는 것을 방지"""
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            return True  # 휠 이벤트 차단
        return super().eventFilter(obj, event)

class DropZoneWidget(QFrame):
    """시각적 드래그 앤 드롭 영역 (테마 대응)"""
    fileDropped = pyqtSignal(str)
    
    def __init__(self, accept_extensions=['.pdf'], parent=None):
        super().__init__(parent)
        self.accept_extensions = accept_extensions
        self.setAcceptDrops(True)
        self.setMinimumHeight(100)
        self._current_path = ""
        self._is_dragging = False
        self._is_dark_theme = True
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(4)
        
        self.icon_label = QLabel("📄")
        self.icon_label.setStyleSheet("font-size: 32px; background: transparent; border: none;")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.text_label = QLabel("PDF 파일을 여기에 드래그하세요")
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.hint_label = QLabel("또는 아래 버튼으로 선택")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.path_label = QLabel("")
        self.path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.path_label.setWordWrap(True)
        
        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        layout.addWidget(self.hint_label)
        layout.addWidget(self.path_label)
        
        self._apply_theme_style()
    
    def set_theme(self, is_dark):
        self._is_dark_theme = is_dark
        self._apply_theme_style()
    
    def _apply_theme_style(self):
        if self._is_dark_theme:
            self.setStyleSheet("""
                DropZoneWidget {
                    border: 2px dashed #555;
                    border-radius: 10px;
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1a1a2e, stop:1 #0f0f23);
                }
                DropZoneWidget:hover { border-color: #e94560; }
            """)
            self.text_label.setStyleSheet("color: #888; font-size: 13px; background: transparent; border: none;")
            self.hint_label.setStyleSheet("color: #555; font-size: 11px; background: transparent; border: none;")
            self.path_label.setStyleSheet("color: #00d9a0; font-size: 12px; background: transparent; border: none;")
        else:
            self.setStyleSheet("""
                DropZoneWidget {
                    border: 2px dashed #ccc;
                    border-radius: 10px;
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff, stop:1 #f5f5f5);
                }
                DropZoneWidget:hover { border-color: #e94560; }
            """)
            self.text_label.setStyleSheet("color: #666; font-size: 13px; background: transparent; border: none;")
            self.hint_label.setStyleSheet("color: #999; font-size: 11px; background: transparent; border: none;")
            self.path_label.setStyleSheet("color: #00a080; font-size: 12px; background: transparent; border: none;")
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile().lower()
                if any(path.endswith(ext) for ext in self.accept_extensions):
                    self._is_dragging = True
                    self.setStyleSheet("""
                        DropZoneWidget {
                            border: 2px solid #e94560;
                            border-radius: 10px;
                            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2a1a3e, stop:1 #1f0f33);
                        }
                    """)
                    self.text_label.setText("✓ 여기에 놓으세요!")
                    self.text_label.setStyleSheet("color: #e94560; font-size: 14px; font-weight: bold; background: transparent; border: none;")
                    event.acceptProposedAction()
                    return
        event.ignore()
    
    def dragLeaveEvent(self, event):
        self._is_dragging = False
        self._apply_theme_style()
        self.text_label.setText("PDF 파일을 여기에 드래그하세요")
        
    def dropEvent(self, event: QDropEvent):
        self._is_dragging = False
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if any(path.lower().endswith(ext) for ext in self.accept_extensions):
                    self._current_path = path
                    self._apply_theme_style()
                    self.text_label.setText("PDF 파일을 여기에 드래그하세요")
                    self.path_label.setText(f"✓ {os.path.basename(path)}")
                    self.icon_label.setText("✅")
                    self.fileDropped.emit(path)
                    event.acceptProposedAction()
                    return
        event.ignore()
        self._apply_theme_style()
    
    def get_path(self): return self._current_path
    def set_path(self, path):
        self._current_path = path
        if path:
            self.path_label.setText(f"✓ {os.path.basename(path)}")
            self.icon_label.setText("✅")
        else:
            self.path_label.setText("")
            self.icon_label.setText("📄")

class FileSelectorWidget(QWidget):
    """파일 선택 위젯 (드롭존 + 버튼)"""
    pathChanged = pyqtSignal(str)
    
    def __init__(self, placeholder="PDF 파일 선택", extensions=['.pdf'], parent=None):
        super().__init__(parent)
        self.extensions = extensions
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        self.drop_zone = DropZoneWidget(extensions, self)
        self.drop_zone.fileDropped.connect(self._on_file_dropped)
        layout.addWidget(self.drop_zone)
        
        btn_layout = QHBoxLayout()
        self.btn_browse = QPushButton("📂 파일 선택")
        self.btn_browse.setObjectName("secondaryBtn")
        self.btn_browse.setToolTip("클릭하여 파일을 선택하세요")
        self.btn_browse.clicked.connect(self.browse_file)
        
        # 최근 파일 버튼
        self.btn_recent = QToolButton()
        self.btn_recent.setText("📋")
        self.btn_recent.setToolTip("최근 파일")
        self.btn_recent.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.btn_recent.setFixedWidth(35)
        self.recent_menu = QMenu(self)
        self.btn_recent.setMenu(self.recent_menu)
        self.btn_recent.aboutToShowMenu = self._update_recent_menu
        self.recent_menu.aboutToShow.connect(self._update_recent_menu)
        
        self.btn_clear = QPushButton("🗑️ 지우기")
        self.btn_clear.setObjectName("secondaryBtn")
        self.btn_clear.setFixedWidth(100)  # 80 -> 100
        self.btn_clear.setToolTip("선택된 파일 해제")
        self.btn_clear.setStyleSheet("""
            QPushButton { 
                background-color: #3e272b; 
                color: #ff6b6b; 
                border: 1px solid #5c3a3a; 
                padding: 10px;
            }
            QPushButton:hover { 
                background-color: #5c3a3a; 
                color: #ff8787; 
            }
        """)
        self.btn_clear.clicked.connect(self.clear_path)
        
        btn_layout.addWidget(self.btn_browse)
        btn_layout.addWidget(self.btn_recent)
        btn_layout.addWidget(self.btn_clear)
        layout.addLayout(btn_layout)
    
    def _update_recent_menu(self):
        """최근 파일 메뉴 업데이트"""
        self.recent_menu.clear()
        settings = load_settings()
        recent = settings.get("recent_files", [])
        if not recent:
            action = self.recent_menu.addAction("(최근 파일 없음)")
            action.setEnabled(False)
        else:
            for path in recent[:10]:
                if os.path.exists(path):
                    action = self.recent_menu.addAction(f"📄 {os.path.basename(path)}")
                    action.setToolTip(path)
                    action.triggered.connect(lambda checked, p=path: self._load_recent(p))
    
    def _load_recent(self, path):
        """최근 파일 로드"""
        self.drop_zone.set_path(path)
        self.pathChanged.emit(path)
        
    def browse_file(self):
        ext_filter = " ".join([f"*{e}" for e in self.extensions])
        f, _ = QFileDialog.getOpenFileName(self, "파일 선택", "", f"파일 ({ext_filter})")
        if f:
            self.drop_zone.set_path(f)
            self.pathChanged.emit(f)
    
    def _on_file_dropped(self, path):
        self.pathChanged.emit(path)
        
    def get_path(self): return self.drop_zone.get_path()
    def set_path(self, path): self.drop_zone.set_path(path)
    def clear_path(self):
        self.drop_zone.set_path("")
        self.pathChanged.emit("")

class FileListWidget(QListWidget):
    """다중 파일 드래그 앤 드롭 리스트 (PDF)"""
    fileAdded = pyqtSignal(str)  # 파일 추가 시그널

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setMinimumHeight(140)
        self.setToolTip("PDF 파일들을 여기에 드래그하세요. 순서 변경도 가능합니다.")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("QListWidget { border: 2px solid #e94560; }")
        else:
            super().dragEnterEvent(event)
    
    def dragLeaveEvent(self, event):
        self.setStyleSheet("")
        super().dragLeaveEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("")
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            last_path = None
            for url in event.mimeData().urls():
                path = str(url.toLocalFile())
                if path.lower().endswith('.pdf'):
                    # 중복 체크
                    exists = any(self.item(i).data(Qt.ItemDataRole.UserRole) == path for i in range(self.count()))
                    if not exists:
                        item = QListWidgetItem(f"📄 {os.path.basename(path)}")
                        item.setData(Qt.ItemDataRole.UserRole, path)
                        item.setToolTip(path)
                        self.addItem(item)
                        last_path = path
            
            if last_path:
                self.fileAdded.emit(last_path)
        else:
            super().dropEvent(event)

    def get_all_paths(self):
        return [self.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.count())]

    def add_file(self, path):
        """파일 추가 (중복 체크 포함)"""
        path = str(path)
        if not path.lower().endswith('.pdf'):
            return
        exists = any(self.item(i).data(Qt.ItemDataRole.UserRole) == path for i in range(self.count()))
        if not exists:
            item = QListWidgetItem(f"📄 {os.path.basename(path)}")
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setToolTip(path)
            self.addItem(item)
            self.fileAdded.emit(path)

class ImageListWidget(QListWidget):
    """이미지 파일 드래그 앤 드롭 리스트"""
    IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp')
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setMinimumHeight(100)
        self.setToolTip("이미지 파일들을 여기에 드래그하세요 (PNG, JPG 등)")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("QListWidget { border: 2px solid #00d9a0; }")
        else:
            super().dragEnterEvent(event)
    
    def dragLeaveEvent(self, event):
        self.setStyleSheet("")
        super().dragLeaveEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("")
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            for url in event.mimeData().urls():
                path = str(url.toLocalFile())
                if path.lower().endswith(self.IMAGE_EXTENSIONS):
                    exists = any(self.item(i).data(Qt.ItemDataRole.UserRole) == path for i in range(self.count()))
                    if not exists:
                        item = QListWidgetItem(f"🖼️ {os.path.basename(path)}")
                        item.setData(Qt.ItemDataRole.UserRole, path)
                        item.setToolTip(path)
                        self.addItem(item)
        else:
            super().dropEvent(event)

    def get_all_paths(self):
        return [self.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.count())]
