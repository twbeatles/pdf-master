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
                    border: 2px dashed #4f8cff;
                    border-radius: 12px;
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(22, 27, 34, 0.9), stop:1 rgba(13, 17, 23, 0.95));
                }
                DropZoneWidget:hover { 
                    border-color: #6ba0ff; 
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(30, 40, 55, 0.95), stop:1 rgba(22, 27, 34, 0.95));
                }
            """)
            self.text_label.setStyleSheet("color: #8b949e; font-size: 13px; background: transparent; border: none;")
            self.hint_label.setStyleSheet("color: #6e7681; font-size: 11px; background: transparent; border: none;")
            self.path_label.setStyleSheet("color: #00d9a0; font-size: 12px; font-weight: bold; background: transparent; border: none;")
        else:
            self.setStyleSheet("""
                DropZoneWidget {
                    border: 2px dashed #4f8cff;
                    border-radius: 12px;
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255, 255, 255, 0.95), stop:1 rgba(246, 248, 250, 0.9));
                }
                DropZoneWidget:hover { 
                    border-color: #6ba0ff;
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255, 255, 255, 1), stop:1 rgba(240, 245, 250, 0.95));
                }
            """)
            self.text_label.setStyleSheet("color: #656d76; font-size: 13px; background: transparent; border: none;")
            self.hint_label.setStyleSheet("color: #8c959f; font-size: 11px; background: transparent; border: none;")
            self.path_label.setStyleSheet("color: #00a080; font-size: 12px; font-weight: bold; background: transparent; border: none;")
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile().lower()
                if any(path.endswith(ext) for ext in self.accept_extensions):
                    self._is_dragging = True
                    self.setStyleSheet("""
                        DropZoneWidget {
                            border: 3px solid #4f8cff;
                            border-radius: 12px;
                            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(79, 140, 255, 0.15), stop:1 rgba(58, 122, 232, 0.1));
                        }
                    """)
                    self.text_label.setText("✅ 여기에 놓으세요!")
                    self.text_label.setStyleSheet("color: #4f8cff; font-size: 15px; font-weight: bold; background: transparent; border: none;")
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
    
    def set_theme(self, is_dark):
        """테마 변경 시 위젯 스타일 동기화"""
        self.drop_zone.set_theme(is_dark)
        if is_dark:
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
        else:
            self.btn_clear.setStyleSheet("""
                QPushButton { 
                    background-color: #ffe0e0; 
                    color: #d32f2f; 
                    border: 1px solid #ffcdd2; 
                    padding: 10px;
                }
                QPushButton:hover { 
                    background-color: #ffcdd2; 
                    color: #c62828; 
                }
            """)

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
            self.setStyleSheet("QListWidget { border: 2px solid #4f8cff; background: rgba(79, 140, 255, 0.05); }")
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
            added_count = 0
            for url in event.mimeData().urls():
                path = str(url.toLocalFile())
                
                # 폴더인 경우 내부 PDF 모두 추가
                if os.path.isdir(path):
                    for filename in os.listdir(path):
                        if filename.lower().endswith('.pdf'):
                            file_path = os.path.join(path, filename)
                            if self._add_pdf_item(file_path):
                                last_path = file_path
                                added_count += 1
                # PDF 파일인 경우
                elif path.lower().endswith('.pdf'):
                    if self._add_pdf_item(path):
                        last_path = path
                        added_count += 1
            
            if last_path:
                self.fileAdded.emit(last_path)
        else:
            super().dropEvent(event)
    
    def _add_pdf_item(self, path):
        """PDF 항목 추가 (중복 체크 포함), 성공 시 True 반환"""
        exists = any(self.item(i).data(Qt.ItemDataRole.UserRole) == path for i in range(self.count()))
        if not exists:
            item = QListWidgetItem(f"📄 {os.path.basename(path)}")
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setToolTip(path)
            self.addItem(item)
            return True
        return False

    def get_all_paths(self):
        return [self.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.count())]

    def add_file(self, path):
        """파일 추가 (중복 체크 포함)"""
        path = str(path)
        if not path.lower().endswith('.pdf'):
            return
        if self._add_pdf_item(path):
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


class ToastWidget(QFrame):
    """비차단형 토스트 알림 위젯 (페이드 애니메이션 + 스택)"""
    closed = pyqtSignal()
    _active_toasts = []  # 활성 토스트 스택 관리
    
    def __init__(self, message, toast_type='info', duration=3000, parent=None):
        super().__init__(parent)
        self.duration = duration
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # 색상 맵
        colors = {
            'success': ('#00d9a0', '#0a3a2a'),
            'error': ('#ff6b6b', '#3a1a1a'),
            'warning': ('#ffb347', '#3a2a1a'),
            'info': ('#5dade2', '#1a2a3a')
        }
        fg, bg = colors.get(toast_type, colors['info'])
        
        # 아이콘 맵
        icons = {'success': '✅', 'error': '❌', 'warning': '⚠️', 'info': 'ℹ️'}
        icon = icons.get(toast_type, 'ℹ️')
        
        self.setStyleSheet(f"""
            ToastWidget {{
                background-color: {bg};
                border: 2px solid {fg};
                border-radius: 10px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: 20px; background: transparent;")
        layout.addWidget(icon_label)
        
        msg_label = QLabel(message)
        msg_label.setStyleSheet(f"color: {fg}; font-size: 13px; font-weight: 500; background: transparent;")
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label, 1)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet(f"""
            QPushButton {{ 
                background: transparent; 
                color: {fg}; 
                border: none; 
                font-size: 18px; 
                font-weight: bold;
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.1); border-radius: 12px; }}
        """)
        close_btn.clicked.connect(self.close_toast)
        layout.addWidget(close_btn)
        
        self.setFixedWidth(350)
        self.adjustSize()
        
        # Import here to avoid circular import
        from PyQt6.QtCore import QTimer, QPropertyAnimation, QEasingCurve
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        
        # Opacity effect for fade animation
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0.0)
        
        # Fade in animation
        self.fade_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in.setDuration(200)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)
        self.fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Fade out animation
        self.fade_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out.setDuration(300)
        self.fade_out.setStartValue(1.0)
        self.fade_out.setEndValue(0.0)
        self.fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_out.finished.connect(self._on_fade_out_done)
        
        # Auto close timer
        self.close_timer = QTimer(self)
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self.close_toast)
    
    def show_toast(self, parent_widget=None):
        """토스트 표시 (스택 위치 자동 계산)"""
        ToastWidget._active_toasts.append(self)
        
        if parent_widget:
            parent_geo = parent_widget.geometry()
            x = parent_geo.right() - self.width() - 20
            y = parent_geo.bottom() - 60
            
            # 스택 오프셋 계산
            for toast in ToastWidget._active_toasts[:-1]:
                if toast.isVisible():
                    y -= toast.height() + 10
            
            self.move(x, y)
        
        self.show()
        self.fade_in.start()
        self.close_timer.start(self.duration)
    
    def close_toast(self):
        """토스트 닫기 (페이드 아웃)"""
        self.close_timer.stop()
        self.fade_out.start()
    
    def _on_fade_out_done(self):
        """페이드 아웃 완료 후 정리"""
        if self in ToastWidget._active_toasts:
            ToastWidget._active_toasts.remove(self)
        self.closed.emit()
        self.hide()
        self.deleteLater()

