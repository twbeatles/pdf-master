import sys
import os
import json
import subprocess
import fitz  # PyMuPDF
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QListWidget, QFileDialog, QMessageBox, 
    QTabWidget, QSpinBox, QComboBox, QLineEdit, QProgressBar,
    QAbstractItemView, QFrame, QScrollArea, QGroupBox, QFormLayout,
    QToolTip, QSplitter, QListWidgetItem, QMenu, QToolButton, QInputDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings, QSize, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QImage, QIcon, QAction, QPainter, QPen, QColor, QFont, QShortcut, QKeySequence

VERSION = "2.2"
APP_NAME = "PDF Master"

# -------------------------------------------------------------------------
# 스타일시트 - 다크 테마
# -------------------------------------------------------------------------
DARK_STYLESHEET = """
QMainWindow, QWidget { background-color: #1a1a2e; color: #eaeaea; font-family: 'Segoe UI', 'Malgun Gothic'; font-size: 13px; }
QTabWidget::pane { border: 1px solid #16213e; background: #16213e; border-radius: 8px; }
QTabBar::tab { background: #0f3460; color: #aaa; padding: 12px 28px; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 3px; font-weight: 500; }
QTabBar::tab:selected { background: #16213e; color: #fff; font-weight: bold; border-bottom: 3px solid #e94560; }
QTabBar::tab:hover { background: #1a4a7a; }
QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e94560, stop:1 #c73e54); color: white; border: none; padding: 10px 20px; border-radius: 6px; font-weight: 600; }
QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff5a7a, stop:1 #e94560); }
QPushButton:pressed { background: #c73e54; }
QPushButton:disabled { background: #555; color: #888; }
QPushButton#secondaryBtn { background: #0f3460; border: 1px solid #1a4a7a; }
QPushButton#secondaryBtn:hover { background: #1a4a7a; }
QPushButton#actionBtn { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00d9a0, stop:1 #00b886); font-size: 15px; padding: 14px; }
QPushButton#actionBtn:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00f0b0, stop:1 #00d9a0); }
QListWidget, QLineEdit, QSpinBox, QComboBox { background-color: #0f0f23; border: 2px solid #16213e; border-radius: 6px; padding: 8px; color: #eaeaea; }
QListWidget::item { padding: 10px; border-bottom: 1px solid #1a1a2e; }
QListWidget::item:selected { background: #e94560; border-radius: 4px; }
QListWidget::item:hover { background: #16213e; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 2px solid #e94560; }
QProgressBar { border: none; border-radius: 6px; text-align: center; background-color: #0f0f23; color: white; font-weight: bold; height: 20px; }
QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e94560, stop:1 #ff7b9a); border-radius: 6px; }
QGroupBox { border: 2px solid #16213e; border-radius: 10px; margin-top: 12px; padding-top: 18px; font-weight: bold; color: #e94560; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 8px; left: 15px; }
QLabel#header { font-size: 28px; font-weight: 800; color: #e94560; }
QLabel#desc { color: #888; font-size: 12px; }
QLabel#stepLabel { color: #00d9a0; font-size: 13px; font-weight: bold; }
QScrollArea { border: none; background: transparent; }
QToolTip { background-color: #16213e; color: #eaeaea; border: 1px solid #e94560; padding: 8px; border-radius: 4px; }
QComboBox::drop-down { border: none; width: 30px; }
QComboBox::down-arrow { image: none; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 6px solid #e94560; }
QComboBox QAbstractItemView { background-color: #0f0f23; border: 1px solid #16213e; selection-background-color: #e94560; }
QSpinBox::up-button, QSpinBox::down-button { background: #16213e; border: none; width: 20px; }
QSpinBox::up-arrow { border-left: 4px solid transparent; border-right: 4px solid transparent; border-bottom: 5px solid #e94560; }
QSpinBox::down-arrow { border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #e94560; }
QSplitter::handle { background: #16213e; }
QMenu { background-color: #16213e; border: 1px solid #0f3460; border-radius: 6px; }
QMenu::item { padding: 8px 25px; }
QMenu::item:selected { background-color: #e94560; }
"""

# -------------------------------------------------------------------------
# 라이트 테마
# -------------------------------------------------------------------------
LIGHT_STYLESHEET = """
QMainWindow, QWidget { background-color: #f5f5f5; color: #333; font-family: 'Segoe UI', 'Malgun Gothic'; font-size: 13px; }
QTabWidget::pane { border: 1px solid #ddd; background: #fff; border-radius: 8px; }
QTabBar::tab { background: #e8e8e8; color: #666; padding: 12px 28px; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 3px; font-weight: 500; }
QTabBar::tab:selected { background: #fff; color: #333; font-weight: bold; border-bottom: 3px solid #e94560; }
QTabBar::tab:hover { background: #f0f0f0; }
QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e94560, stop:1 #c73e54); color: white; border: none; padding: 10px 20px; border-radius: 6px; font-weight: 600; }
QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff5a7a, stop:1 #e94560); }
QPushButton#secondaryBtn { background: #fff; border: 2px solid #ddd; color: #333; }
QPushButton#secondaryBtn:hover { background: #f8f8f8; border-color: #e94560; }
QPushButton#actionBtn { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00d9a0, stop:1 #00b886); font-size: 15px; padding: 14px; }
QListWidget, QLineEdit, QSpinBox, QComboBox { background-color: #fff; border: 2px solid #ddd; border-radius: 6px; padding: 8px; color: #333; }
QListWidget::item:selected { background: #e94560; color: white; }
QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 2px solid #e94560; }
QProgressBar { border: none; border-radius: 6px; text-align: center; background-color: #e8e8e8; color: #333; font-weight: bold; }
QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e94560, stop:1 #ff7b9a); border-radius: 6px; }
QGroupBox { border: 2px solid #ddd; border-radius: 10px; margin-top: 12px; padding-top: 18px; font-weight: bold; color: #e94560; }
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 8px; left: 15px; }
QLabel#header { font-size: 28px; font-weight: 800; color: #e94560; }
QLabel#desc { color: #888; }
QLabel#stepLabel { color: #00a080; font-size: 13px; font-weight: bold; }
QToolTip { background-color: #fff; color: #333; border: 1px solid #e94560; padding: 8px; border-radius: 4px; }
QComboBox QAbstractItemView { background-color: #fff; border: 1px solid #ddd; selection-background-color: #e94560; color: #333; }
QMenu { background-color: #fff; border: 1px solid #ddd; }
QMenu::item:selected { background-color: #e94560; color: white; }
"""

SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".pdf_master_settings.json")

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {"theme": "dark", "recent_files": []}

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except: pass

# -------------------------------------------------------------------------
# 드래그 앤 드롭 영역 위젯
# -------------------------------------------------------------------------
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
        
        self.btn_clear = QPushButton("✕")
        self.btn_clear.setObjectName("secondaryBtn")
        self.btn_clear.setFixedWidth(40)
        self.btn_clear.setToolTip("선택 해제")
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

# -------------------------------------------------------------------------
# 멀티 파일 드래그 앤 드롭 리스트
# -------------------------------------------------------------------------
class FileListWidget(QListWidget):
    """다중 파일 드래그 앤 드롭 리스트 (PDF)"""
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
            for url in event.mimeData().urls():
                path = str(url.toLocalFile())
                if path.lower().endswith('.pdf'):
                    # 중복 체크 (UserRole 데이터로 경로 비교)
                    exists = any(self.item(i).data(Qt.ItemDataRole.UserRole) == path for i in range(self.count()))
                    if not exists:
                        item = QListWidgetItem(f"📄 {os.path.basename(path)}")
                        item.setData(Qt.ItemDataRole.UserRole, path)
                        item.setToolTip(path)
                        self.addItem(item)
        else:
            super().dropEvent(event)

    def get_all_paths(self):
        return [self.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.count())]


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

# -------------------------------------------------------------------------
# 워커 스레드 (PDF 작업)
# -------------------------------------------------------------------------
class WorkerThread(QThread):
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, mode, **kwargs):
        super().__init__()
        self.mode = mode
        self.kwargs = kwargs

    def run(self):
        try:
            method = getattr(self, self.mode, None)
            if method:
                method()
            else:
                self.error_signal.emit(f"알 수 없는 작업: {self.mode}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error_signal.emit(str(e))

    def merge(self):
        files = self.kwargs.get('files')
        output_path = self.kwargs.get('output_path')
        doc_merged = fitz.open()
        for idx, path in enumerate(files):
            try:
                doc = fitz.open(path)
                doc_merged.insert_pdf(doc)
                doc.close()
            except Exception as e:
                print(f"Skipping {path}: {e}")
            self.progress_signal.emit(int((idx + 1) / len(files) * 100))
        doc_merged.save(output_path)
        doc_merged.close()
        self.finished_signal.emit(f"✅ 병합 완료!\n{len(files)}개 파일 → 1개 PDF")

    def convert_to_img(self):
        file_path = self.kwargs.get('file_path')
        output_dir = self.kwargs.get('output_dir')
        fmt = self.kwargs.get('fmt', 'png')
        dpi = self.kwargs.get('dpi', 200)
        doc = fitz.open(file_path)
        total = len(doc)
        base = os.path.splitext(os.path.basename(file_path))[0]
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=mat)
            save_path = os.path.join(output_dir, f"{base}_p{i+1:03d}.{fmt}")
            pix.save(save_path)
            self.progress_signal.emit(int((i + 1) / total * 100))
        doc.close()
        self.finished_signal.emit(f"✅ 변환 완료!\n{total}페이지 → {fmt.upper()} 이미지")

    def extract_text(self):
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        doc = fitz.open(file_path)
        total = len(doc)
        full_text = ""
        for i, page in enumerate(doc):
            full_text += f"\n--- Page {i+1} ---\n"
            full_text += page.get_text()
            self.progress_signal.emit(int((i + 1) / total * 100))
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_text)
        doc.close()
        self.finished_signal.emit(f"✅ 텍스트 추출 완료!\n{output_path}")

    def split(self):
        file_path = self.kwargs.get('file_path')
        output_dir = self.kwargs.get('output_dir')
        page_range = self.kwargs.get('page_range')
        doc_src = fitz.open(file_path)
        total_pages = len(doc_src)
        pages_to_keep = []
        parts = page_range.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                s, e = map(int, part.split('-'))
                for p in range(s-1, e):
                    if 0 <= p < total_pages: pages_to_keep.append(p)
            elif part.isdigit():
                p = int(part) - 1
                if 0 <= p < total_pages: pages_to_keep.append(p)
        pages_to_keep = sorted(list(set(pages_to_keep)))
        if not pages_to_keep:
            raise ValueError("유효한 페이지가 없습니다.")
        doc_final = fitz.open()
        for idx, p_num in enumerate(pages_to_keep):
            doc_final.insert_pdf(doc_src, from_page=p_num, to_page=p_num)
            self.progress_signal.emit(int((idx+1)/len(pages_to_keep)*100))
        base = os.path.splitext(os.path.basename(file_path))[0]
        out = os.path.join(output_dir, f"{base}_extracted.pdf")
        doc_final.save(out)
        doc_src.close()
        doc_final.close()
        self.finished_signal.emit(f"✅ 추출 완료!\n{len(pages_to_keep)}페이지 추출됨")

    def delete_pages(self):
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        page_range = self.kwargs.get('page_range')
        doc = fitz.open(file_path)
        total_pages = len(doc)
        pages_to_delete = []
        parts = page_range.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                s, e = map(int, part.split('-'))
                for p in range(s-1, e):
                    if 0 <= p < total_pages: pages_to_delete.append(p)
            elif part.isdigit():
                p = int(part) - 1
                if 0 <= p < total_pages: pages_to_delete.append(p)
        pages_to_delete = sorted(list(set(pages_to_delete)), reverse=True)
        if not pages_to_delete:
            raise ValueError("삭제할 페이지가 없습니다.")
        for p in pages_to_delete:
            doc.delete_page(p)
        doc.save(output_path)
        doc.close()
        self.progress_signal.emit(100)
        self.finished_signal.emit(f"✅ 삭제 완료!\n{len(pages_to_delete)}페이지 삭제됨")

    def rotate(self):
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        angle = self.kwargs.get('angle')
        doc = fitz.open(file_path)
        for i, page in enumerate(doc):
            page.set_rotation(page.rotation + angle)
            self.progress_signal.emit(int((i+1)/len(doc) * 100))
        doc.save(output_path)
        doc.close()
        self.finished_signal.emit(f"✅ 회전 완료!\n{angle}° 회전됨")

    def watermark(self):
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        text = self.kwargs.get('text')
        opacity = self.kwargs.get('opacity', 0.3)
        color = self.kwargs.get('color', (0.5, 0.5, 0.5))
        doc = fitz.open(file_path)
        for i, page in enumerate(doc):
            page.insert_text(
                fitz.Point(page.rect.width/2, page.rect.height/2),
                text, fontsize=40, fontname="helv",
                rotate=45, color=color, fill_opacity=opacity, align=1
            )
            self.progress_signal.emit(int((i+1)/len(doc) * 100))
        doc.save(output_path)
        doc.close()
        self.finished_signal.emit(f"✅ 워터마크 적용 완료!")

    def metadata_update(self):
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        new_meta = self.kwargs.get('metadata')
        doc = fitz.open(file_path)
        meta = doc.metadata
        for k, v in new_meta.items():
            if v: meta[k] = v
        doc.set_metadata(meta)
        doc.save(output_path)
        doc.close()
        self.progress_signal.emit(100)
        self.finished_signal.emit(f"✅ 메타데이터 저장 완료!")

    def protect(self):
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        pw = self.kwargs.get('password')
        doc = fitz.open(file_path)
        perm = int(fitz.PDF_PERM_ACCESSIBILITY | fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY)
        doc.save(output_path, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw=pw, user_pw=pw, permissions=perm)
        doc.close()
        self.progress_signal.emit(100)
        self.finished_signal.emit(f"✅ 암호화 완료!")

    def compress(self):
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        doc = fitz.open(file_path)
        original_size = os.path.getsize(file_path)
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        new_size = os.path.getsize(output_path)
        ratio = (1 - new_size / original_size) * 100 if original_size > 0 else 0
        self.progress_signal.emit(100)
        self.finished_signal.emit(f"✅ 압축 완료!\n{original_size//1024}KB → {new_size//1024}KB ({ratio:.1f}% 감소)")

    def images_to_pdf(self):
        files = self.kwargs.get('files')
        output_path = self.kwargs.get('output_path')
        doc = fitz.open()
        for idx, img_path in enumerate(files):
            img = fitz.open(img_path)
            rect = img[0].rect
            pdf_bytes = img.convert_to_pdf()
            img.close()
            img_pdf = fitz.open("pdf", pdf_bytes)
            doc.insert_pdf(img_pdf)
            img_pdf.close()
            self.progress_signal.emit(int((idx + 1) / len(files) * 100))
        doc.save(output_path)
        doc.close()
        self.finished_signal.emit(f"✅ 이미지 → PDF 변환 완료!\n{len(files)}개 이미지 → 1개 PDF")

    def reorder(self):
        """페이지 순서 변경"""
        file_path = self.kwargs.get('file_path')
        output_path = self.kwargs.get('output_path')
        page_order = self.kwargs.get('page_order')
        
        doc_src = fitz.open(file_path)
        doc_out = fitz.open()
        
        for idx, page_num in enumerate(page_order):
            doc_out.insert_pdf(doc_src, from_page=page_num, to_page=page_num)
            self.progress_signal.emit(int((idx + 1) / len(page_order) * 100))
        
        doc_out.save(output_path)
        doc_src.close()
        doc_out.close()
        self.finished_signal.emit(f"✅ 페이지 순서 변경 완료!\n{len(page_order)}페이지 재정렬됨")

    def batch(self):
        """일괄 처리"""
        files = self.kwargs.get('files')
        output_dir = self.kwargs.get('output_dir')
        operation = self.kwargs.get('operation')
        option = self.kwargs.get('option', '')
        
        success_count = 0
        for idx, file_path in enumerate(files):
            try:
                base = os.path.splitext(os.path.basename(file_path))[0]
                out_path = os.path.join(output_dir, f"{base}_processed.pdf")
                
                doc = fitz.open(file_path)
                
                if "압축" in operation:
                    doc.save(out_path, garbage=4, deflate=True)
                elif "워터마크" in operation and option:
                    for page in doc:
                        page.insert_text(fitz.Point(page.rect.width/2, page.rect.height/2),
                            option, fontsize=40, fontname="helv", rotate=45, 
                            color=(0.5, 0.5, 0.5), fill_opacity=0.3, align=1)
                    doc.save(out_path)
                elif "암호화" in operation and option:
                    perm = int(fitz.PDF_PERM_ACCESSIBILITY | fitz.PDF_PERM_PRINT | fitz.PDF_PERM_COPY)
                    doc.save(out_path, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw=option, user_pw=option, permissions=perm)
                elif "회전" in operation:
                    for page in doc:
                        page.set_rotation(page.rotation + 90)
                    doc.save(out_path)
                else:
                    doc.save(out_path)
                
                doc.close()
                success_count += 1
            except Exception as e:
                print(f"Batch error on {file_path}: {e}")
            
            self.progress_signal.emit(int((idx + 1) / len(files) * 100))
        
        self.finished_signal.emit(f"✅ 일괄 처리 완료!\n{success_count}/{len(files)}개 파일 처리됨")

# -------------------------------------------------------------------------
# 메인 애플리케이션
# -------------------------------------------------------------------------
class PDFMasterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.worker = None
        self._last_output_path = None  # 마지막 저장 경로 추적
        self._current_preview_page = 0
        self._current_preview_doc = None
        
        self.setWindowTitle(f"{APP_NAME} v{VERSION}")
        self.resize(1200, 850)  # 더 큰 기본 크기
        self.setMinimumSize(950, 700)
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(15, 10, 15, 10)  # 더 컴팩트한 여백
        main_layout.setSpacing(8)
        
        # Header - 컴팩트하게
        header = self._create_header()
        main_layout.addLayout(header)
        
        # Content area with splitter - 더 큰 비율
        self.content_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.content_splitter.setHandleWidth(5)  # 드래그 핸들 더 넘게
        self.content_splitter.setChildrenCollapsible(False)  # 패널 접기 방지
        
        # Tabs (left side)
        tabs_widget = QWidget()
        tabs_layout = QVBoxLayout(tabs_widget)
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        tabs_layout.addWidget(self.tabs)
        self.content_splitter.addWidget(tabs_widget)
        
        # Preview panel (right side)
        preview_widget = self._create_preview_panel()
        self.content_splitter.addWidget(preview_widget)
        self.content_splitter.setSizes([650, 450])  # 미리보기 패널 더 크게
        
        # 사용자 설정 복원
        saved_sizes = self.settings.get("splitter_sizes")
        if saved_sizes:
            self.content_splitter.setSizes(saved_sizes)
        self.content_splitter.splitterMoved.connect(self._save_splitter_state)
        
        main_layout.addWidget(self.content_splitter, 1)  # stretch factor 1로 최대 확장
        
        # Setup tabs
        self.setup_merge_tab()
        self.setup_convert_tab()
        self.setup_page_tab()
        self.setup_reorder_tab()  # NEW: 페이지 순서 변경
        self.setup_edit_sec_tab()
        self.setup_batch_tab()    # NEW: 일괄 처리
        
        # 컴팩트한 상태 바
        status_frame = QFrame()
        status_frame.setMaximumHeight(36)  # 높이 제한
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(8, 4, 8, 4)
        status_layout.setSpacing(10)
        
        self.status_label = QLabel("✨ 준비 완료")
        self.status_label.setStyleSheet("color: #888; font-size: 12px;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        status_layout.addWidget(self.progress_bar)
        
        self.btn_open_folder = QPushButton("📂 폴더")
        self.btn_open_folder.setObjectName("secondaryBtn")
        self.btn_open_folder.setFixedWidth(70)
        self.btn_open_folder.setFixedHeight(24)
        self.btn_open_folder.setVisible(False)
        self.btn_open_folder.clicked.connect(self._open_last_folder)
        status_layout.addWidget(self.btn_open_folder)
        
        main_layout.addWidget(status_frame)
        
        self._apply_theme()
        self._setup_shortcuts()
    
    def _setup_shortcuts(self):
        """Keyboard shortcuts"""
        QShortcut(QKeySequence("Ctrl+O"), self, self._shortcut_open_file)
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)
        QShortcut(QKeySequence("F1"), self, self._show_help)
        QShortcut(QKeySequence("Ctrl+1"), self, lambda: self.tabs.setCurrentIndex(0))
        QShortcut(QKeySequence("Ctrl+2"), self, lambda: self.tabs.setCurrentIndex(1))
        QShortcut(QKeySequence("Ctrl+3"), self, lambda: self.tabs.setCurrentIndex(2))
        QShortcut(QKeySequence("Ctrl+4"), self, lambda: self.tabs.setCurrentIndex(3))
    
    def _shortcut_open_file(self):
        """Open file via shortcut"""
        f, _ = QFileDialog.getOpenFileName(self, "PDF 선택", "", "PDF (*.pdf)")
        if f:
            self._update_preview(f)
            self.status_label.setText(f"📄 {os.path.basename(f)} 로드됨")
    
    def _open_last_folder(self):
        """Open folder containing last output"""
        if self._last_output_path and os.path.exists(self._last_output_path):
            folder = os.path.dirname(self._last_output_path)
            if sys.platform == 'win32':
                subprocess.Popen(['explorer', '/select,', self._last_output_path])
            else:
                subprocess.Popen(['open', folder])
        
    def _save_splitter_state(self):
        """Save splitter position"""
        self.settings["splitter_sizes"] = self.content_splitter.sizes()
        save_settings(self.settings)
        
    def _create_header(self):
        header = QHBoxLayout()
        header.setSpacing(15)
        
        # 컴팩트한 타이틀
        title = QLabel(f"📑 {APP_NAME}")
        title.setObjectName("header")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #e94560;")
        header.addWidget(title)
        
        ver_label = QLabel(f"v{VERSION}")
        ver_label.setStyleSheet("color: #666; font-size: 11px;")
        header.addWidget(ver_label)
        
        header.addStretch()
        
        # Theme toggle
        self.btn_theme = QPushButton("🌙" if self.settings.get("theme") == "dark" else "☀️")
        self.btn_theme.setObjectName("secondaryBtn")
        self.btn_theme.setFixedSize(36, 36)
        self.btn_theme.setToolTip("테마 전환")
        self.btn_theme.clicked.connect(self._toggle_theme)
        header.addWidget(self.btn_theme)
        
        # Help button
        btn_help = QPushButton("❓")
        btn_help.setObjectName("secondaryBtn")
        btn_help.setFixedSize(36, 36)
        btn_help.setToolTip("도움말 (F1)")
        btn_help.clicked.connect(self._show_help)
        header.addWidget(btn_help)
        
        return header
    
    def _create_preview_panel(self):
        panel = QGroupBox("📋 미리보기")
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        self.preview_label = QLabel("PDF 파일을 선택하면\n여기에 정보가 표시됩니다")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("color: #666; padding: 10px; font-size: 12px;")
        self.preview_label.setWordWrap(True)
        self.preview_label.setMaximumHeight(120)  # 정보 영역 높이 제한
        layout.addWidget(self.preview_label)
        
        # 더 큰 미리보기 이미지 영역
        self.preview_image = QLabel()
        self.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image.setMinimumSize(250, 350)
        self.preview_image.setStyleSheet("background: #0f0f23; border-radius: 8px; border: 1px solid #333;")
        self.preview_image.setSizePolicy(self.preview_image.sizePolicy().horizontalPolicy(), 
                                          self.preview_image.sizePolicy().verticalPolicy())
        layout.addWidget(self.preview_image, 1)  # stretch factor
        
        return panel
    
    def _update_preview(self, path):
        if not path or not os.path.exists(path):
            self.preview_label.setText("PDF 파일을 선택하면\n여기에 정보가 표시됩니다")
            self.preview_image.clear()
            return
        
        # 최근 파일 목록 업데이트
        self._add_to_recent_files(path)
        
        try:
            doc = fitz.open(path)
            
            # 암호화된 PDF 처리
            if doc.is_encrypted:
                doc.close()
                password, ok = QInputDialog.getText(
                    self, "🔒 암호 입력", 
                    f"'{os.path.basename(path)}'\n\n비밀번호를 입력하세요:",
                    QLineEdit.EchoMode.Password
                )
                if ok and password:
                    doc = fitz.open(path)
                    if not doc.authenticate(password):
                        doc.close()
                        self.preview_label.setText("❌ 비밀번호가 틀렸습니다")
                        self.preview_image.clear()
                        return
                else:
                    self.preview_label.setText("🔒 암호화된 PDF\n비밀번호가 필요합니다")
                    self.preview_image.clear()
                    return
            
            size_kb = os.path.getsize(path) / 1024
            meta = doc.metadata
            info = f"""📄 {os.path.basename(path)}

📊 페이지: {len(doc)}p  💾 크기: {size_kb:.1f}KB
📝 제목: {meta.get('title', '-') or '-'}
👤 작성자: {meta.get('author', '-') or '-'}"""
            self.preview_label.setText(info)
            
            # Thumbnail
            if len(doc) > 0:
                page = doc[0]
                pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
                img_data = bytes(pix.samples)
                img = QImage(img_data, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(img.copy())
                preview_size = self.preview_image.size()
                target_w = max(280, preview_size.width() - 20)
                target_h = max(400, preview_size.height() - 20)
                scaled = pixmap.scaled(target_w, target_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.preview_image.setPixmap(scaled)
            doc.close()
        except Exception as e:
            self.preview_label.setText(f"미리보기 오류: {e}")
    
    def _add_to_recent_files(self, path):
        """최근 파일 목록에 추가"""
        recent = self.settings.get("recent_files", [])
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self.settings["recent_files"] = recent[:10]  # 최대 10개
        save_settings(self.settings)
    
    def _toggle_theme(self):
        current = self.settings.get("theme", "dark")
        new_theme = "light" if current == "dark" else "dark"
        self.settings["theme"] = new_theme
        save_settings(self.settings)
        self._apply_theme()
        self.btn_theme.setText("🌙" if new_theme == "dark" else "☀️")
    
    def _apply_theme(self):
        theme = self.settings.get("theme", "dark")
        QApplication.instance().setStyleSheet(DARK_STYLESHEET if theme == "dark" else LIGHT_STYLESHEET)
    
    def _show_help(self):
        QMessageBox.information(self, "도움말", f"""📑 {APP_NAME} v{VERSION}

🔹 파일을 드래그하거나 버튼으로 선택하세요
🔹 각 탭에서 원하는 작업을 선택하세요
🔹 작업 완료 시 저장 위치를 지정합니다

주요 기능:
• 📎 병합: 여러 PDF를 하나로
• 🖼️ 변환: PDF ↔ 이미지
• ✂️ 페이지: 추출, 삭제, 회전
• 🔒 보안: 암호화, 워터마크""")
    
    # Worker helpers
    def run_worker(self, mode, output_path=None, **kwargs):
        # output_path 추적 (폴더 열기 기능용)
        if output_path:
            self._last_output_path = output_path
            kwargs['output_path'] = output_path
        elif 'output_path' in kwargs:
            self._last_output_path = kwargs['output_path']
        elif 'output_dir' in kwargs:
            self._last_output_path = kwargs['output_dir']
        
        self.worker = WorkerThread(mode, **kwargs)
        self.worker.progress_signal.connect(self.progress_bar.setValue)
        self.worker.finished_signal.connect(self.on_success)
        self.worker.error_signal.connect(self.on_fail)
        self.progress_bar.setValue(0)
        self.btn_open_folder.setVisible(False)
        self.status_label.setText("⏳ 작업 처리 중...")
        self.set_ui_busy(True)
        self.worker.start()
    
    def on_success(self, msg):
        self.set_ui_busy(False)
        self.status_label.setText("✅ 작업 완료!")
        self.progress_bar.setValue(100)
        self.btn_open_folder.setVisible(True)  # 폴더 열기 버튼 표시
        QMessageBox.information(self, "완료", msg)
        QTimer.singleShot(3000, lambda: self.progress_bar.setValue(0))
    
    def on_fail(self, msg):
        self.set_ui_busy(False)
        self.status_label.setText("❌ 오류 발생")
        self.progress_bar.setValue(0)
        self.btn_open_folder.setVisible(False)
        QMessageBox.critical(self, "오류", f"작업 중 문제가 발생했습니다.\n{msg}")
    
    def set_ui_busy(self, busy):
        self.tabs.setEnabled(not busy)
        self.btn_open_folder.setEnabled(not busy)

    # ===================== Tab 1: 병합 =====================
    def setup_merge_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Guide
        guide = QLabel("📎 여러 PDF 파일을 하나로 합칩니다")
        guide.setObjectName("desc")
        layout.addWidget(guide)
        
        step1 = QLabel("1️⃣ PDF 파일들을 아래에 드래그하세요 (순서 조정 가능)")
        step1.setObjectName("stepLabel")
        layout.addWidget(step1)
        
        self.merge_list = FileListWidget()
        layout.addWidget(self.merge_list)
        
        btn_box = QHBoxLayout()
        b_add = QPushButton("➕ 파일 추가")
        b_add.setObjectName("secondaryBtn")
        b_add.clicked.connect(self._merge_add_files)
        
        b_del = QPushButton("➖ 선택 삭제")
        b_del.setObjectName("secondaryBtn")
        b_del.clicked.connect(lambda: [self.merge_list.takeItem(self.merge_list.row(i)) for i in self.merge_list.selectedItems()])
        
        b_clr = QPushButton("🧹 전체 삭제")
        b_clr.setObjectName("secondaryBtn")
        b_clr.clicked.connect(self.merge_list.clear)
        
        btn_box.addWidget(b_add)
        btn_box.addWidget(b_del)
        btn_box.addWidget(b_clr)
        btn_box.addStretch()
        layout.addLayout(btn_box)
        
        step2 = QLabel("2️⃣ 병합 실행")
        step2.setObjectName("stepLabel")
        layout.addWidget(step2)
        
        b_run = QPushButton("🚀 PDF 병합 실행")
        b_run.setObjectName("actionBtn")
        b_run.clicked.connect(self.action_merge)
        layout.addWidget(b_run)
        
        self.tabs.addTab(tab, "📎 병합")
    
    def _merge_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "PDF 선택", "", "PDF (*.pdf)")
        for f in files:
            item = QListWidgetItem(f"📄 {os.path.basename(f)}")
            item.setData(Qt.ItemDataRole.UserRole, f)
            item.setToolTip(f)
            self.merge_list.addItem(item)
    
    def action_merge(self):
        files = self.merge_list.get_all_paths()
        if len(files) < 2:
            return QMessageBox.warning(self, "알림", "2개 이상의 PDF 파일이 필요합니다.")
        save, _ = QFileDialog.getSaveFileName(self, "저장", "merged.pdf", "PDF (*.pdf)")
        if save:
            self.run_worker("merge", files=files, output_path=save)

    # ===================== Tab 2: 변환 =====================
    def setup_convert_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # PDF → 이미지
        grp_img = QGroupBox("🖼️ PDF → 이미지 변환")
        l_img = QVBoxLayout(grp_img)
        step = QLabel("1️⃣ PDF 파일 선택")
        step.setObjectName("stepLabel")
        l_img.addWidget(step)
        self.sel_img = FileSelectorWidget()
        self.sel_img.pathChanged.connect(self._update_preview)
        l_img.addWidget(self.sel_img)
        
        opt = QHBoxLayout()
        opt.addWidget(QLabel("포맷:"))
        self.cmb_fmt = QComboBox()
        self.cmb_fmt.addItems(["png", "jpg"])
        opt.addWidget(self.cmb_fmt)
        opt.addWidget(QLabel("해상도(DPI):"))
        self.spn_dpi = QSpinBox()
        self.spn_dpi.setRange(72, 600)
        self.spn_dpi.setValue(150)
        opt.addWidget(self.spn_dpi)
        opt.addStretch()
        l_img.addLayout(opt)
        
        b_img = QPushButton("🖼️ 이미지로 변환")
        b_img.clicked.connect(self.action_img)
        l_img.addWidget(b_img)
        content_layout.addWidget(grp_img)
        
        # 이미지 → PDF
        grp_img2pdf = QGroupBox("📄 이미지 → PDF 변환")
        l_i2p = QVBoxLayout(grp_img2pdf)
        step2 = QLabel("1️⃣ 이미지 파일들을 아래에 드래그하세요")
        step2.setObjectName("stepLabel")
        l_i2p.addWidget(step2)
        self.img_list = ImageListWidget()
        l_i2p.addWidget(self.img_list)
        
        btn_i2p = QHBoxLayout()
        b_add_img = QPushButton("➕ 이미지 추가")
        b_add_img.setObjectName("secondaryBtn")
        b_add_img.clicked.connect(self._add_images)
        b_clr_img = QPushButton("🧹 초기화")
        b_clr_img.setObjectName("secondaryBtn")
        b_clr_img.clicked.connect(self.img_list.clear)
        btn_i2p.addWidget(b_add_img)
        btn_i2p.addWidget(b_clr_img)
        btn_i2p.addStretch()
        l_i2p.addLayout(btn_i2p)
        
        b_i2p = QPushButton("📄 PDF로 변환")
        b_i2p.clicked.connect(self.action_img_to_pdf)
        l_i2p.addWidget(b_i2p)
        content_layout.addWidget(grp_img2pdf)
        
        # 텍스트 추출
        grp_txt = QGroupBox("📝 텍스트 추출")
        l_txt = QVBoxLayout(grp_txt)
        self.sel_txt = FileSelectorWidget()
        l_txt.addWidget(self.sel_txt)
        b_txt = QPushButton("📝 텍스트(.txt) 저장")
        b_txt.clicked.connect(self.action_txt)
        l_txt.addWidget(b_txt)
        content_layout.addWidget(grp_txt)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.tabs.addTab(tab, "🔄 변환")
    
    def _add_images(self):
        files, _ = QFileDialog.getOpenFileNames(self, "이미지 선택", "", "이미지 (*.png *.jpg *.jpeg *.bmp *.gif *.webp)")
        for f in files:
            item = QListWidgetItem(f"🖼️ {os.path.basename(f)}")
            item.setData(Qt.ItemDataRole.UserRole, f)
            item.setToolTip(f)
            self.img_list.addItem(item)
    
    def action_img(self):
        path = self.sel_img.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        d = QFileDialog.getExistingDirectory(self, "저장 폴더 선택")
        if d:
            self.run_worker("convert_to_img", file_path=path, output_dir=d, fmt=self.cmb_fmt.currentText(), dpi=self.spn_dpi.value())
    
    def action_img_to_pdf(self):
        files = self.img_list.get_all_paths()
        if not files:
            return QMessageBox.warning(self, "알림", "이미지 파일을 추가하세요.")
        save, _ = QFileDialog.getSaveFileName(self, "저장", "images.pdf", "PDF (*.pdf)")
        if save:
            self.run_worker("images_to_pdf", files=files, output_path=save)
    
    def action_txt(self):
        path = self.sel_txt.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "extracted.txt", "Text (*.txt)")
        if s:
            self.run_worker("extract_text", file_path=path, output_path=s)

    # ===================== Tab 3: 페이지 =====================
    def setup_page_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # 추출
        grp_split = QGroupBox("✂️ 페이지 추출")
        l_s = QVBoxLayout(grp_split)
        self.sel_split = FileSelectorWidget()
        self.sel_split.pathChanged.connect(self._update_preview)
        l_s.addWidget(self.sel_split)
        h = QHBoxLayout()
        h.addWidget(QLabel("추출할 페이지 (예: 1-3, 5):"))
        self.inp_range = QLineEdit()
        self.inp_range.setPlaceholderText("1, 3-5, 8")
        h.addWidget(self.inp_range)
        l_s.addLayout(h)
        b_s = QPushButton("✂️ 추출 실행")
        b_s.clicked.connect(self.action_split)
        l_s.addWidget(b_s)
        content_layout.addWidget(grp_split)
        
        # 삭제
        grp_del = QGroupBox("🗑️ 페이지 삭제")
        l_d = QVBoxLayout(grp_del)
        self.sel_del = FileSelectorWidget()
        l_d.addWidget(self.sel_del)
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("삭제할 페이지 (예: 1, 3-5):"))
        self.inp_del_range = QLineEdit()
        self.inp_del_range.setPlaceholderText("2, 4-6")
        h2.addWidget(self.inp_del_range)
        l_d.addLayout(h2)
        b_d = QPushButton("🗑️ 삭제 실행")
        b_d.clicked.connect(self.action_delete_pages)
        l_d.addWidget(b_d)
        content_layout.addWidget(grp_del)
        
        # 회전
        grp_rot = QGroupBox("🔄 페이지 회전")
        l_r = QVBoxLayout(grp_rot)
        self.sel_rot = FileSelectorWidget()
        l_r.addWidget(self.sel_rot)
        h3 = QHBoxLayout()
        h3.addWidget(QLabel("회전 각도:"))
        self.cmb_rot = QComboBox()
        self.cmb_rot.addItems(["90° 시계방향", "180°", "270° 시계방향"])
        h3.addWidget(self.cmb_rot)
        h3.addStretch()
        l_r.addLayout(h3)
        b_r = QPushButton("🔄 회전 실행")
        b_r.clicked.connect(self.action_rotate)
        l_r.addWidget(b_r)
        content_layout.addWidget(grp_rot)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.tabs.addTab(tab, "✂️ 페이지")
    
    def action_split(self):
        path = self.sel_split.get_path()
        rng = self.inp_range.text()
        if not path or not rng:
            return QMessageBox.warning(self, "알림", "파일과 페이지 범위를 입력하세요.")
        d = QFileDialog.getExistingDirectory(self, "저장 폴더")
        if d:
            self.run_worker("split", file_path=path, output_dir=d, page_range=rng)
    
    def action_delete_pages(self):
        path = self.sel_del.get_path()
        rng = self.inp_del_range.text()
        if not path or not rng:
            return QMessageBox.warning(self, "알림", "파일과 삭제할 페이지를 입력하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "deleted.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("delete_pages", file_path=path, output_path=s, page_range=rng)
    
    def action_rotate(self):
        path = self.sel_rot.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "파일을 선택하세요.")
        angle_map = {"90° 시계방향": 90, "180°": 180, "270° 시계방향": 270}
        angle = angle_map.get(self.cmb_rot.currentText(), 90)
        s, _ = QFileDialog.getSaveFileName(self, "저장", "rotated.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("rotate", file_path=path, output_path=s, angle=angle)

    # ===================== Tab 4: 편집/보안 =====================
    def setup_edit_sec_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # 메타데이터
        grp_meta = QGroupBox("📋 메타데이터 수정")
        l_m = QVBoxLayout(grp_meta)
        self.sel_meta = FileSelectorWidget()
        self.sel_meta.pathChanged.connect(self._load_metadata)
        l_m.addWidget(self.sel_meta)
        form = QFormLayout()
        self.inp_title = QLineEdit()
        self.inp_author = QLineEdit()
        self.inp_subj = QLineEdit()
        form.addRow("제목:", self.inp_title)
        form.addRow("작성자:", self.inp_author)
        form.addRow("주제:", self.inp_subj)
        l_m.addLayout(form)
        b_m = QPushButton("💾 메타데이터 저장")
        b_m.clicked.connect(self.action_metadata)
        l_m.addWidget(b_m)
        content_layout.addWidget(grp_meta)
        
        # 워터마크
        grp_wm = QGroupBox("💧 워터마크 삽입")
        l_w = QVBoxLayout(grp_wm)
        self.sel_wm = FileSelectorWidget()
        l_w.addWidget(self.sel_wm)
        h_w = QHBoxLayout()
        self.inp_wm = QLineEdit()
        self.inp_wm.setPlaceholderText("워터마크 텍스트")
        h_w.addWidget(self.inp_wm)
        self.cmb_wm_color = QComboBox()
        self.cmb_wm_color.addItems(["회색", "검정", "빨강", "파랑"])
        h_w.addWidget(self.cmb_wm_color)
        l_w.addLayout(h_w)
        b_w = QPushButton("💧 워터마크 적용")
        b_w.clicked.connect(self.action_watermark)
        l_w.addWidget(b_w)
        content_layout.addWidget(grp_wm)
        
        # 보안
        grp_sec = QGroupBox("🔒 보안 && 압축")
        l_sec = QVBoxLayout(grp_sec)
        self.sel_sec = FileSelectorWidget()
        l_sec.addWidget(self.sel_sec)
        h_sec = QHBoxLayout()
        self.inp_pw = QLineEdit()
        self.inp_pw.setPlaceholderText("비밀번호 입력")
        self.inp_pw.setEchoMode(QLineEdit.EchoMode.Password)
        h_sec.addWidget(self.inp_pw)
        b_enc = QPushButton("🔒 암호화")
        b_enc.clicked.connect(self.action_protect)
        h_sec.addWidget(b_enc)
        b_comp = QPushButton("📦 압축")
        b_comp.clicked.connect(self.action_compress)
        h_sec.addWidget(b_comp)
        l_sec.addLayout(h_sec)
        content_layout.addWidget(grp_sec)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.tabs.addTab(tab, "🔒 편집/보안")
    
    def _load_metadata(self, path):
        if not path or not os.path.exists(path):
            return
        try:
            doc = fitz.open(path)
            m = doc.metadata
            self.inp_title.setText(m.get('title', '') or '')
            self.inp_author.setText(m.get('author', '') or '')
            self.inp_subj.setText(m.get('subject', '') or '')
            doc.close()
        except: pass
    
    def action_metadata(self):
        path = self.sel_meta.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "파일을 선택하세요.")
        meta = {'title': self.inp_title.text(), 'author': self.inp_author.text(), 'subject': self.inp_subj.text()}
        s, _ = QFileDialog.getSaveFileName(self, "저장", "metadata_updated.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("metadata_update", file_path=path, output_path=s, metadata=meta)
    
    def action_watermark(self):
        path = self.sel_wm.get_path()
        text = self.inp_wm.text()
        if not path or not text:
            return QMessageBox.warning(self, "알림", "파일과 텍스트를 입력하세요.")
        c_map = {"회색": (0.5,0.5,0.5), "검정": (0,0,0), "빨강": (1,0,0), "파랑": (0,0,1)}
        color = c_map.get(self.cmb_wm_color.currentText(), (0.5,0.5,0.5))
        s, _ = QFileDialog.getSaveFileName(self, "저장", "watermarked.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("watermark", file_path=path, output_path=s, text=text, color=color)
    
    def action_protect(self):
        path = self.sel_sec.get_path()
        pw = self.inp_pw.text()
        if not path or not pw:
            return QMessageBox.warning(self, "알림", "파일과 비밀번호를 입력하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "encrypted.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("protect", file_path=path, output_path=s, password=pw)
    
    def action_compress(self):
        path = self.sel_sec.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "compressed.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("compress", file_path=path, output_path=s)

    # ===================== Tab 5: 페이지 순서 변경 =====================
    def setup_reorder_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        guide = QLabel("🔀 PDF 페이지 순서를 변경합니다")
        guide.setObjectName("desc")
        layout.addWidget(guide)
        
        step1 = QLabel("1️⃣ PDF 파일 선택")
        step1.setObjectName("stepLabel")
        layout.addWidget(step1)
        
        self.sel_reorder = FileSelectorWidget()
        self.sel_reorder.pathChanged.connect(self._load_pages_for_reorder)
        layout.addWidget(self.sel_reorder)
        
        step2 = QLabel("2️⃣ 페이지를 드래그하여 순서 변경")
        step2.setObjectName("stepLabel")
        layout.addWidget(step2)
        
        self.reorder_list = QListWidget()
        self.reorder_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.reorder_list.setMinimumHeight(150)
        self.reorder_list.setToolTip("페이지를 드래그하여 순서를 변경하세요")
        layout.addWidget(self.reorder_list)
        
        btn_box = QHBoxLayout()
        b_reverse = QPushButton("🔃 역순 정렬")
        b_reverse.setObjectName("secondaryBtn")
        b_reverse.clicked.connect(self._reverse_pages)
        btn_box.addWidget(b_reverse)
        btn_box.addStretch()
        layout.addLayout(btn_box)
        
        b_run = QPushButton("💾 순서 변경 저장")
        b_run.setObjectName("actionBtn")
        b_run.clicked.connect(self.action_reorder)
        layout.addWidget(b_run)
        
        self.tabs.addTab(tab, "🔀 순서")
    
    def _load_pages_for_reorder(self, path):
        """페이지 목록 로드"""
        self.reorder_list.clear()
        if not path or not os.path.exists(path):
            return
        try:
            doc = fitz.open(path)
            for i in range(len(doc)):
                item = QListWidgetItem(f"📄 페이지 {i+1}")
                item.setData(Qt.ItemDataRole.UserRole, i)
                self.reorder_list.addItem(item)
            doc.close()
        except Exception as e:
            QMessageBox.warning(self, "오류", f"페이지 로드 실패: {e}")
    
    def _reverse_pages(self):
        """페이지 역순 정렬"""
        items = []
        while self.reorder_list.count() > 0:
            items.append(self.reorder_list.takeItem(0))
        for item in reversed(items):
            self.reorder_list.addItem(item)
    
    def action_reorder(self):
        path = self.sel_reorder.get_path()
        if not path or self.reorder_list.count() == 0:
            return QMessageBox.warning(self, "알림", "PDF를 선택하고 페이지를 확인하세요.")
        page_order = [self.reorder_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.reorder_list.count())]
        s, _ = QFileDialog.getSaveFileName(self, "저장", "reordered.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("reorder", file_path=path, output_path=s, page_order=page_order)

    # ===================== Tab 6: 일괄 처리 =====================
    def setup_batch_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        guide = QLabel("📦 여러 PDF에 동일한 작업을 일괄 적용합니다")
        guide.setObjectName("desc")
        content_layout.addWidget(guide)
        
        step1 = QLabel("1️⃣ PDF 파일들 선택")
        step1.setObjectName("stepLabel")
        content_layout.addWidget(step1)
        
        self.batch_list = FileListWidget()
        content_layout.addWidget(self.batch_list)
        
        btn_box = QHBoxLayout()
        b_add = QPushButton("➕ 파일 추가")
        b_add.setObjectName("secondaryBtn")
        b_add.clicked.connect(self._batch_add_files)
        b_folder = QPushButton("📁 폴더 전체")
        b_folder.setObjectName("secondaryBtn")
        b_folder.clicked.connect(self._batch_add_folder)
        b_clr = QPushButton("🧹 초기화")
        b_clr.setObjectName("secondaryBtn")
        b_clr.clicked.connect(self.batch_list.clear)
        btn_box.addWidget(b_add)
        btn_box.addWidget(b_folder)
        btn_box.addWidget(b_clr)
        btn_box.addStretch()
        content_layout.addLayout(btn_box)
        
        step2 = QLabel("2️⃣ 적용할 작업 선택")
        step2.setObjectName("stepLabel")
        content_layout.addWidget(step2)
        
        # 작업 선택
        opt_layout = QHBoxLayout()
        opt_layout.addWidget(QLabel("작업:"))
        self.cmb_batch_op = QComboBox()
        self.cmb_batch_op.addItems(["📦 압축", "💧 워터마크", "🔒 암호화", "🔄 회전(90°)"])
        opt_layout.addWidget(self.cmb_batch_op)
        opt_layout.addStretch()
        content_layout.addLayout(opt_layout)
        
        # 워터마크/암호 옵션
        opt_layout2 = QHBoxLayout()
        opt_layout2.addWidget(QLabel("텍스트/암호:"))
        self.inp_batch_opt = QLineEdit()
        self.inp_batch_opt.setPlaceholderText("워터마크 텍스트 또는 비밀번호")
        opt_layout2.addWidget(self.inp_batch_opt)
        content_layout.addLayout(opt_layout2)
        
        step3 = QLabel("3️⃣ 출력 폴더 선택 및 실행")
        step3.setObjectName("stepLabel")
        content_layout.addWidget(step3)
        
        b_run = QPushButton("🚀 일괄 처리 실행")
        b_run.setObjectName("actionBtn")
        b_run.clicked.connect(self.action_batch)
        content_layout.addWidget(b_run)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.tabs.addTab(tab, "📦 일괄")
    
    def _batch_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "PDF 선택", "", "PDF (*.pdf)")
        for f in files:
            item = QListWidgetItem(f"📄 {os.path.basename(f)}")
            item.setData(Qt.ItemDataRole.UserRole, f)
            item.setToolTip(f)
            self.batch_list.addItem(item)
    
    def _batch_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "폴더 선택")
        if folder:
            for f in os.listdir(folder):
                if f.lower().endswith('.pdf'):
                    path = os.path.join(folder, f)
                    item = QListWidgetItem(f"📄 {f}")
                    item.setData(Qt.ItemDataRole.UserRole, path)
                    item.setToolTip(path)
                    self.batch_list.addItem(item)
    
    def action_batch(self):
        files = self.batch_list.get_all_paths()
        if not files:
            return QMessageBox.warning(self, "알림", "PDF 파일을 추가하세요.")
        out_dir = QFileDialog.getExistingDirectory(self, "출력 폴더 선택")
        if not out_dir:
            return
        op = self.cmb_batch_op.currentText()
        opt = self.inp_batch_opt.text()
        self.run_worker("batch", files=files, output_dir=out_dir, operation=op, option=opt)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFMasterApp()
    window.show()
    sys.exit(app.exec())
