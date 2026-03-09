import os
import logging
from typing import Any
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QPushButton, QFileDialog,
    QListWidget, QListWidgetItem, QAbstractItemView, QMenu,
    QToolButton, QHBoxLayout, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QEvent
from PyQt6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent
from ..core.settings import load_settings

logger = logging.getLogger(__name__)


def _item_user_data(item: QListWidgetItem | None) -> Any | None:
    if item is None:
        return None
    return item.data(Qt.ItemDataRole.UserRole)


def _item_user_path(item: QListWidgetItem | None) -> str | None:
    data = _item_user_data(item)
    return data if isinstance(data, str) else None


def is_valid_pdf(file_path: str) -> bool:
    """
    PDF 파일 유효성 검사 (PDF 헤더 확인)
    
    Args:
        file_path: 검사할 파일 경로
        
    Returns:
        유효한 PDF인지 여부
    """
    if not os.path.exists(file_path):
        return False
    
    # 최소/최대 크기 검사
    try:
        file_size = os.path.getsize(file_path)
        if file_size < 100:  # 100바이트 미만은 유효한 PDF가 아님
            logger.warning(f"PDF file too small: {file_path} ({file_size} bytes)")
            return False
        # v4.4: MAX_FILE_SIZE (2GB) 검사
        MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
        if file_size > MAX_FILE_SIZE:
            logger.warning(f"PDF file too large: {file_path} ({file_size / (1024*1024*1024):.2f} GB)")
            return False
    except OSError as e:
        logger.warning(f"Cannot access file: {file_path}: {e}")
        return False
    
    # PDF 헤더 매직 넘버 확인 (%PDF-)
    try:
        with open(file_path, 'rb') as f:
            header = f.read(8)
            if not header.startswith(b'%PDF-'):
                logger.warning(f"Invalid PDF header: {file_path}")
                return False
        return True
    except (IOError, OSError) as e:
        logger.warning(f"Cannot read PDF header: {file_path}: {e}")
        return False


def is_pdf_encrypted(file_path: str) -> bool:
    """
    PDF 파일 암호화 여부 확인 (v4.5: 공용 함수)
    
    Args:
        file_path: 검사할 PDF 파일 경로
        
    Returns:
        암호화된 PDF인지 여부
    """
    if not file_path or not os.path.exists(file_path):
        return False
    
    try:
        import fitz
        doc = fitz.open(file_path)
        try:
            return bool(doc.is_encrypted)
        finally:
            doc.close()
    except Exception as e:
        logger.debug(f"Cannot check PDF encryption: {file_path}: {e}")
        return False

class WheelEventFilter(QObject):
    """QSpinBox, QComboBox 등에서 스크롤 휠로 값이 변경되는 것을 방지"""
    def eventFilter(self, a0: QObject | None, a1: QEvent | None) -> bool:
        if a1 is not None and a1.type() == QEvent.Type.Wheel:
            return True  # 휠 이벤트 차단
        return super().eventFilter(a0, a1)


class EmptyStateWidget(QFrame):
    """
    빈 상태 안내 위젯
    
    파일이 없거나 시작 상태일 때 표시되는 친근한 안내 UI
    """
    actionClicked = pyqtSignal()
    
    def __init__(self, icon: str = "📄", title: str | None = None,
                 description: str | None = None,
                 action_text: str | None = None, parent=None):
        super().__init__(parent)
        from ..core.i18n import tm
        
        if title is None:
            title = tm.get("empty_title")
        if description is None:
            description = tm.get("empty_desc")
            
        self._is_dark_theme = True

        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)
        layout.setContentsMargins(30, 40, 30, 40)
        
        # 아이콘
        self.icon_label = QLabel(icon)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 48px; background: transparent;")
        layout.addWidget(self.icon_label)
        
        # 제목
        self.title_label = QLabel(title or "")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        
        # 설명
        self.desc_label = QLabel(description or "")
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)
        
        # 액션 버튼 (선택적)
        if action_text:
            self.action_btn = QPushButton(action_text)
            self.action_btn.setObjectName("secondaryBtn")
            self.action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.action_btn.clicked.connect(self.actionClicked.emit)
            layout.addWidget(self.action_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        self._apply_theme_style()
    
    def _apply_theme_style(self):
        if self._is_dark_theme:
            self.setStyleSheet("""
                EmptyStateWidget {
                    background: transparent;
                    border: 2px dashed #2d3748;
                    border-radius: 16px;
                }
            """)
            self.title_label.setStyleSheet("""
                font-size: 16px;
                font-weight: 600;
                color: #94a3b8;
                background: transparent;
            """)
            self.desc_label.setStyleSheet("""
                font-size: 13px;
                color: #64748b;
                background: transparent;
            """)
        else:
            self.setStyleSheet("""
                EmptyStateWidget {
                    background: transparent;
                    border: 2px dashed #e2e8f0;
                    border-radius: 16px;
                }
            """)
            self.title_label.setStyleSheet("""
                font-size: 16px;
                font-weight: 600;
                color: #475569;
                background: transparent;
            """)
            self.desc_label.setStyleSheet("""
                font-size: 13px;
                color: #94a3b8;
                background: transparent;
            """)
    
    def set_theme(self, is_dark: bool):
        """테마 설정"""
        self._is_dark_theme = is_dark
        self._apply_theme_style()
    
    def set_content(self, icon: str | None = None, title: str | None = None, description: str | None = None):
        """내용 업데이트"""
        if icon:
            self.icon_label.setText(icon)
        if title:
            self.title_label.setText(title)
        if description:
            self.desc_label.setText(description)

class DropZoneWidget(QFrame):
    """시각적 드래그 앤 드롭 영역 (테마 대응)"""
    fileDropped = pyqtSignal(str)

    def __init__(self, accept_extensions: list[str] | tuple[str, ...] | None = None, parent=None):
        super().__init__(parent)
        self.accept_extensions = list(accept_extensions or ['.pdf'])
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
        
        from ..core.i18n import tm
        self.text_label = QLabel(tm.get("drop_title"))
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.hint_label = QLabel(tm.get("drop_hint"))
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.path_label = QLabel("")
        self.path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.path_label.setWordWrap(True)
        
        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        layout.addWidget(self.hint_label)
        layout.addWidget(self.path_label)
        
        self._apply_theme_style()
    
    def set_theme(self, is_dark: bool):
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
        
    def dragEnterEvent(self, a0: QDragEnterEvent | None):
        from ..core.i18n import tm
        mime_data = a0.mimeData() if a0 is not None else None
        if mime_data is not None and mime_data.hasUrls():
            for url in mime_data.urls():
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
                    self.text_label.setText(tm.get("drop_success"))
                    self.text_label.setStyleSheet("color: #4f8cff; font-size: 15px; font-weight: bold; background: transparent; border: none;")
                    if a0 is not None:
                        a0.acceptProposedAction()
                    return
        if a0 is not None:
            a0.ignore()

    def dragLeaveEvent(self, a0: QDragLeaveEvent | None):
        self._is_dragging = False
        self._apply_theme_style()
        from ..core.i18n import tm
        self.text_label.setText(tm.get("drop_title"))
        if a0 is not None:
            super().dragLeaveEvent(a0)

    def dropEvent(self, a0: QDropEvent | None):
        self._is_dragging = False
        mime_data = a0.mimeData() if a0 is not None else None
        if mime_data is not None and mime_data.hasUrls():
            for url in mime_data.urls():
                path = url.toLocalFile()
                if any(path.lower().endswith(ext) for ext in self.accept_extensions):
                    self._current_path = path
                    self._apply_theme_style()
                    from ..core.i18n import tm
                    self.text_label.setText(tm.get("drop_title"))
                    self.path_label.setText(f"✓ {os.path.basename(path)}")
                    self.icon_label.setText("✅")
                    self.fileDropped.emit(path)
                    if a0 is not None:
                        a0.acceptProposedAction()
                    return
        if a0 is not None:
            a0.ignore()
        self._apply_theme_style()

    def get_path(self) -> str:
        return self._current_path

    def set_path(self, path: str):
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

    def __init__(self, placeholder: str = "PDF 파일 선택", extensions: list[str] | tuple[str, ...] | None = None, parent=None):
        super().__init__(parent)
        self.extensions = list(extensions or ['.pdf'])
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        self.drop_zone = DropZoneWidget(extensions, self)
        self.drop_zone.fileDropped.connect(self._on_file_dropped)
        layout.addWidget(self.drop_zone)
        
        btn_layout = QHBoxLayout()
        from ..core.i18n import tm
        self.btn_browse = QPushButton(tm.get("btn_browse"))
        self.btn_browse.setObjectName("secondaryBtn")
        self.btn_browse.setToolTip("클릭하여 파일을 선택하세요")
        self.btn_browse.clicked.connect(self.browse_file)
        
        # 최근 파일 버튼
        self.btn_recent = QToolButton()
        self.btn_recent.setText("📋")
        self.btn_recent.setToolTip(tm.get("recent_files"))
        self.btn_recent.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.btn_recent.setFixedWidth(35)
        self.recent_menu = QMenu(self)
        self.btn_recent.setMenu(self.recent_menu)
        self.recent_menu.aboutToShow.connect(self._update_recent_menu)
        
        self.btn_clear = QPushButton(tm.get("btn_clear"))
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
        settings = self._get_settings_snapshot()
        recent_value = settings.get("recent_files", [])
        recent = recent_value if isinstance(recent_value, list) else []
        if not recent:
            from ..core.i18n import tm
            action = self.recent_menu.addAction(tm.get("no_recent_files"))
            if action is not None:
                action.setEnabled(False)
        else:
            for path in recent[:10]:
                if isinstance(path, str) and os.path.exists(path):
                    action = self.recent_menu.addAction(f"📄 {os.path.basename(path)}")
                    if action is not None:
                        action.setToolTip(path)
                        action.triggered.connect(lambda checked=False, p=path: self._load_recent(p))

    def _get_settings_snapshot(self) -> dict[str, Any]:
        """Prefer shared in-memory settings to avoid repeated disk reads."""
        current: QObject | None = self.parent()
        while current is not None:
            settings = getattr(current, "settings", None)
            if isinstance(settings, dict):
                return settings
            current = current.parent()
        return load_settings()

    def _load_recent(self, path: str):
        """최근 파일 로드"""
        self.drop_zone.set_path(path)
        self.pathChanged.emit(path)
        
    def browse_file(self):
        ext_filter = " ".join([f"*{e}" for e in self.extensions])
        from ..core.i18n import tm
        f, _ = QFileDialog.getOpenFileName(self, tm.get("file"), "", f"{tm.get('file')} ({ext_filter})")
        if f:
            self.drop_zone.set_path(f)
            self.pathChanged.emit(f)
    
    def _on_file_dropped(self, path: str):
        self.pathChanged.emit(path)

    def get_path(self) -> str:
        return self.drop_zone.get_path()

    def set_path(self, path: str):
        self.drop_zone.set_path(path)

    def clear_path(self):
        self.drop_zone.set_path("")
        self.pathChanged.emit("")

    def set_theme(self, is_dark: bool):
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

    def dragEnterEvent(self, e: QDragEnterEvent | None):
        mime_data = e.mimeData() if e is not None else None
        if mime_data is not None and mime_data.hasUrls():
            if e is not None:
                e.acceptProposedAction()
            self.setStyleSheet("QListWidget { border: 2px solid #4f8cff; background: rgba(79, 140, 255, 0.05); }")
        else:
            super().dragEnterEvent(e)

    def dragLeaveEvent(self, e: QDragLeaveEvent | None):
        self.setStyleSheet("")
        super().dragLeaveEvent(e)

    def dragMoveEvent(self, e: QDragMoveEvent | None):
        mime_data = e.mimeData() if e is not None else None
        if mime_data is not None and mime_data.hasUrls():
            if e is not None:
                e.setDropAction(Qt.DropAction.CopyAction)
                e.accept()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, event: QDropEvent | None):
        self.setStyleSheet("")
        mime_data = event.mimeData() if event is not None else None
        if mime_data is not None and mime_data.hasUrls():
            if event is not None:
                event.setDropAction(Qt.DropAction.CopyAction)
                event.accept()
            last_path: str | None = None
            for url in mime_data.urls():
                path = str(url.toLocalFile())

                # 폴더인 경우 내부 PDF 모두 추가
                if os.path.isdir(path):
                    for filename in os.listdir(path):
                        if filename.lower().endswith('.pdf'):
                            file_path = os.path.join(path, filename)
                            if self._add_pdf_item(file_path):
                                last_path = file_path
                # PDF 파일인 경우
                elif path.lower().endswith('.pdf'):
                    if self._add_pdf_item(path):
                        last_path = path

            if last_path is not None:
                self.fileAdded.emit(last_path)
        else:
            super().dropEvent(event)

    def _add_pdf_item(self, path: str) -> bool:
        """PDF 항목 추가 (중복 체크 및 유효성 검사 포함), 성공 시 True 반환"""
        # 유효성 검사
        if not is_valid_pdf(path):
            return False

        # 중복 체크
        exists = any(_item_user_path(self.item(i)) == path for i in range(self.count()))
        if not exists:
            item = QListWidgetItem(f"📄 {os.path.basename(path)}")
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setToolTip(path)
            self.addItem(item)
            return True
        return False

    def get_all_paths(self) -> list[str]:
        return [path for i in range(self.count()) if (path := _item_user_path(self.item(i))) is not None]

    def add_file(self, path: str):
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

    def dragEnterEvent(self, e: QDragEnterEvent | None):
        mime_data = e.mimeData() if e is not None else None
        if mime_data is not None and mime_data.hasUrls():
            if e is not None:
                e.acceptProposedAction()
            self.setStyleSheet("QListWidget { border: 2px solid #00d9a0; }")
        else:
            super().dragEnterEvent(e)

    def dragLeaveEvent(self, e: QDragLeaveEvent | None):
        self.setStyleSheet("")
        super().dragLeaveEvent(e)

    def dragMoveEvent(self, e: QDragMoveEvent | None):
        mime_data = e.mimeData() if e is not None else None
        if mime_data is not None and mime_data.hasUrls():
            if e is not None:
                e.setDropAction(Qt.DropAction.CopyAction)
                e.accept()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, event: QDropEvent | None):
        self.setStyleSheet("")
        mime_data = event.mimeData() if event is not None else None
        if mime_data is not None and mime_data.hasUrls():
            if event is not None:
                event.setDropAction(Qt.DropAction.CopyAction)
                event.accept()
            for url in mime_data.urls():
                path = str(url.toLocalFile())
                if path.lower().endswith(self.IMAGE_EXTENSIONS):
                    exists = any(_item_user_path(self.item(i)) == path for i in range(self.count()))
                    if not exists:
                        item = QListWidgetItem(f"🖼️ {os.path.basename(path)}")
                        item.setData(Qt.ItemDataRole.UserRole, path)
                        item.setToolTip(path)
                        self.addItem(item)
        else:
            super().dropEvent(event)

    def get_all_paths(self) -> list[str]:
        return [path for i in range(self.count()) if (path := _item_user_path(self.item(i))) is not None]


class DraggableListWidget(QListWidget):
    """
    드래그 앤 드롭으로 순서 변경이 가능한 리스트 위젯 (v4.4)
    
    CLAUDE.md에 문서화된 대로 itemsReordered 시그널 지원
    """
    itemsReordered = pyqtSignal(list)  # 재정렬된 항목 리스트
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        model = self.model()
        if model is not None:
            model.rowsMoved.connect(self._on_rows_moved)

    def _on_rows_moved(self, *_args: object):
        """행 이동 시 시그널 발생"""
        items = self.get_all_items()
        self.itemsReordered.emit(items)

    def get_all_items(self) -> list[Any]:
        """모든 항목의 데이터 반환"""
        return [_item_user_data(self.item(i)) for i in range(self.count())]

    def add_item(self, text: str, data: Any = None):
        """항목 추가"""
        item = QListWidgetItem(text)
        if data is not None:
            item.setData(Qt.ItemDataRole.UserRole, data)
        self.addItem(item)


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
        
        # 향상된 스타일 (v4.1)
        self.setStyleSheet(f"""
            ToastWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 {bg}, stop:1 rgba(0,0,0,0.95));
                border: 2px solid {fg};
                border-radius: 12px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: 22px; background: transparent;")
        layout.addWidget(icon_label)
        
        msg_label = QLabel(message)
        msg_label.setStyleSheet(f"""
            color: {fg}; 
            font-size: 13px; 
            font-weight: 600; 
            background: transparent;
            letter-spacing: 0.3px;
        """)
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label, 1)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet(f"""
            QPushButton {{ 
                background: transparent; 
                color: {fg}; 
                border: none; 
                font-size: 20px; 
                font-weight: bold;
                border-radius: 13px;
            }}
            QPushButton:hover {{ 
                background: rgba(255,255,255,0.15); 
            }}
        """)
        close_btn.clicked.connect(self.close_toast)
        layout.addWidget(close_btn)
        
        self.setFixedWidth(380)
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
        self._parent_widget = parent_widget  # 부모 윈도우 참조 저장
        ToastWidget._active_toasts.append(self)
        
        if parent_widget:
            parent_geo = parent_widget.geometry()
            x = parent_geo.right() - self.width() - 20
            y = parent_geo.bottom() - 60
            
            # 같은 부모에 속한 토스트만 계산하여 스택 오프셋 적용
            for toast in ToastWidget._active_toasts[:-1]:
                if toast.isVisible() and getattr(toast, '_parent_widget', None) == parent_widget:
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

