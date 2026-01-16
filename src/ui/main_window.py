import sys
import os
import json
import fitz
import subprocess
import logging
import shutil
import tempfile
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
    QPushButton, QLabel, QFileDialog, QMessageBox, QComboBox, 
    QSpinBox, QSplitter, QGroupBox, QScrollArea, QApplication, 
    QInputDialog, QLineEdit, QProgressBar, QListWidget, QListWidgetItem,
    QAbstractItemView, QFrame, QFormLayout, QMenuBar, QMenu, QTextEdit,
    QStackedWidget, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QTimer, QSize, QByteArray
from PyQt6.QtGui import QIcon, QAction, QPixmap, QImage, QKeySequence, QShortcut

from ..core.settings import load_settings, save_settings
from ..core.worker import WorkerThread
from ..core.undo_manager import UndoManager
from .widgets import FileSelectorWidget, FileListWidget, ImageListWidget, DropZoneWidget, WheelEventFilter, ToastWidget, EmptyStateWidget
from .styles import DARK_STYLESHEET, LIGHT_STYLESHEET, ThemeColors
from .thumbnail_grid import ThumbnailGridWidget
from .zoomable_preview import ZoomablePreviewWidget
from .progress_overlay import ProgressOverlayWidget
from ..core.i18n import tm  # v4.4: i18n support

logger = logging.getLogger(__name__)

# AI 기능 가용성 - ai_service 모듈에서 체크된 값 사용 (중복 체크 제거)
try:
    from ..core.ai_service import GENAI_AVAILABLE as AI_AVAILABLE
except ImportError:
    AI_AVAILABLE = False
    logger.info("AI service module not available. AI features will be disabled.")

# PDF to Word 변환 기능 삭제 (v4.2 - 의존성 간소화)

APP_NAME = "PDF Master"
VERSION = "4.4"

class PDFMasterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.worker = None
        self._last_output_path = None  # 마지막 저장 경로 추적
        self._current_preview_page = 0
        self._current_preview_doc = None
        
        # v4.0: Undo/Redo 매니저
        self.undo_manager = UndoManager(max_history=50)
        
        # v4.3: Undo 백업 디렉토리 (임시 폴더 사용)
        self._undo_backup_dir = os.path.join(tempfile.gettempdir(), "pdf_master_undo")
        os.makedirs(self._undo_backup_dir, exist_ok=True)
        
        # v4.4: 시작 시 오래된 백업 정리
        self._cleanup_old_undo_backups(max_age_hours=24)
        
        # 휠 이벤트 필터 설치 (스크롤로 값 변경 방지)
        self._wheel_filter = WheelEventFilter(self)
        
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
        
        # Menu bar
        self._create_menu_bar()
        
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
        self.setup_reorder_tab()  # 페이지 순서 변경
        self.setup_edit_sec_tab()
        self.setup_batch_tab()    # 일괄 처리
        self.setup_advanced_tab() # 고급 기능
        self.setup_ai_tab()       # v4.0: AI 요약
        
        # 컴팩트한 상태 바
        status_frame = QFrame()
        status_frame.setMaximumHeight(36)  # 높이 제한
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(8, 4, 8, 4)
        status_layout.setSpacing(10)
        
        self.status_label = QLabel(tm.get("ready"))
        self.status_label.setStyleSheet("color: #888; font-size: 12px;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        status_layout.addWidget(self.progress_bar)
        
        self.btn_open_folder = QPushButton(tm.get("folder"))
        self.btn_open_folder.setObjectName("secondaryBtn")
        self.btn_open_folder.setFixedWidth(70)
        self.btn_open_folder.setFixedHeight(24)
        self.btn_open_folder.setVisible(False)
        self.btn_open_folder.clicked.connect(self._open_last_folder)
        status_layout.addWidget(self.btn_open_folder)
        
        main_layout.addWidget(status_frame)
        
        self._apply_theme()
        self._setup_shortcuts()
        
        # 모든 QSpinBox, QComboBox에 휠 필터 설치
        self._install_wheel_filters()
        
        # v2.7: 윈도우 위치 복원
        self._restore_window_geometry()
        
        # v4.3: 진행 오버레이 위젯 초기화 (개선된 UX)
        self.progress_overlay = ProgressOverlayWidget(central)
        self.progress_overlay.cancelled.connect(self._on_worker_cancelled)
        self.progress_overlay.hide()
    
    def _install_wheel_filters(self):
        """모든 입력 위젯에 휠 이벤트 필터 설치"""
        for widget in self.findChildren(QSpinBox):
            widget.installEventFilter(self._wheel_filter)
        for widget in self.findChildren(QComboBox):
            widget.installEventFilter(self._wheel_filter)
    
    def _setup_shortcuts(self):
        """Keyboard shortcuts"""
        QShortcut(QKeySequence("Ctrl+O"), self, self._shortcut_open_file)
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)
        QShortcut(QKeySequence("Ctrl+T"), self, self._toggle_theme)
        QShortcut(QKeySequence("Ctrl+Z"), self, self._undo_action)  # v4.0: Undo
        QShortcut(QKeySequence("Ctrl+Y"), self, self._redo_action)  # v4.0: Redo
        QShortcut(QKeySequence("F1"), self, self._show_help)
        QShortcut(QKeySequence("Ctrl+1"), self, lambda: self.tabs.setCurrentIndex(0))
        QShortcut(QKeySequence("Ctrl+2"), self, lambda: self.tabs.setCurrentIndex(1))
        QShortcut(QKeySequence("Ctrl+3"), self, lambda: self.tabs.setCurrentIndex(2))
        QShortcut(QKeySequence("Ctrl+4"), self, lambda: self.tabs.setCurrentIndex(3))
        QShortcut(QKeySequence("Ctrl+5"), self, lambda: self.tabs.setCurrentIndex(4))
        QShortcut(QKeySequence("Ctrl+6"), self, lambda: self.tabs.setCurrentIndex(5))
        QShortcut(QKeySequence("Ctrl+7"), self, lambda: self.tabs.setCurrentIndex(6))
        QShortcut(QKeySequence("Ctrl+8"), self, lambda: self.tabs.setCurrentIndex(7))  # v4.0: AI 탭
    
    def _undo_action(self):
        """실행 취소"""
        if self.undo_manager.can_undo:
            record = self.undo_manager.undo()
            if record:
                msg = tm.get("undo_action", record.description)
                self.status_label.setText(msg)
                toast = ToastWidget(msg, toast_type='info', duration=2000)
                toast.show_toast(self)
        else:
            self.status_label.setText(tm.get("undo_empty"))
    
    def _redo_action(self):
        """다시 실행"""
        if self.undo_manager.can_redo:
            record = self.undo_manager.redo()
            if record:
                msg = tm.get("redo_action", record.description)
                self.status_label.setText(msg)
                toast = ToastWidget(msg, toast_type='info', duration=2000)
                toast.show_toast(self)
        else:
            self.status_label.setText(tm.get("redo_empty"))
    
    def _shortcut_open_file(self):
        """Open file via shortcut"""
        f, _ = QFileDialog.getOpenFileName(self, tm.get("open"), "", "PDF (*.pdf)")
        if f:
            self._update_preview(f)
            self.status_label.setText(f"📄 {os.path.basename(f)} loaded")
    
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
    
    def _restore_window_geometry(self):
        """윈도우 위치/크기 복원"""
        geo = self.settings.get("window_geometry")
        if geo:
            try:
                # Try restoration from hex string (standard Qt way)
                if isinstance(geo, str):
                    self.restoreGeometry(QByteArray.fromHex(geo.encode('utf-8')))
                # Fallback for old dict format
                elif isinstance(geo, dict):
                    self.setGeometry(
                        int(geo.get("x", 100)), 
                        int(geo.get("y", 100)), 
                        int(geo.get("width", 1200)), 
                        int(geo.get("height", 850))
                    )
            except Exception as e:
                logger.warning(f"Failed to restore window geometry: {e}")

    
    def closeEvent(self, event):
        """앱 종료 시 리소스 정리 및 설정 저장"""
        # 1. Worker 스레드 안전 종료 (취소 요청 후 대기)
        if self.worker and self.worker.isRunning():
            logger.info("Cancelling and waiting for worker thread to finish...")
            # 먼저 취소 요청 (graceful shutdown)
            if hasattr(self.worker, 'cancel'):
                self.worker.cancel()
            self.worker.quit()
            if not self.worker.wait(3000):  # 3초 대기
                logger.warning("Worker thread did not finish in time, terminating...")
                self.worker.terminate()
                self.worker.wait(1000)
        
        # 2. 미리보기 PDF 문서 닫기
        if self._current_preview_doc:
            try:
                self._current_preview_doc.close()
                self._current_preview_doc = None
                logger.debug("Preview document closed")
            except Exception as e:
                logger.warning(f"Failed to close preview document: {e}")
        
        # 3. 미사용 undo 백업 정리 (v4.4)
        self._cleanup_unused_undo_backups()
        
        # 4. 윈도우 위치 저장
        self.settings["window_geometry"] = {
            "x": self.x(), "y": self.y(),
            "width": self.width(), "height": self.height()
        }
        save_settings(self.settings)
        
        logger.info("Application closed cleanly")
        event.accept()
    
    def _create_menu_bar(self):
        """메뉴 바 생성"""
        menubar = self.menuBar()
        
        # 파일 메뉴
        file_menu = menubar.addMenu(tm.get("menu_file"))
        
        open_action = QAction(tm.get("menu_open"), self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._shortcut_open_file)
        file_menu.addAction(open_action)
        
        # 최근 파일 서브메뉴
        self.recent_menu_bar = file_menu.addMenu(tm.get("menu_recent"))
        self._update_recent_menu_bar()
        
        file_menu.addSeparator()
        
        exit_action = QAction(tm.get("menu_exit"), self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        
        # 언어 메뉴 추가
        self.lang_menu = menubar.addMenu(tm.get("menu_language"))
        
        # Auto
        auto_action = QAction(tm.get("lang_auto"), self)
        auto_action.setCheckable(True)
        auto_action.setData("auto")
        auto_action.setChecked(self.settings.get("language") == "auto")
        auto_action.triggered.connect(lambda: self._change_language("auto"))
        self.lang_menu.addAction(auto_action)
        
        self.lang_menu.addSeparator()
        
        # Korean
        ko_action = QAction(tm.get("lang_ko"), self)
        ko_action.setCheckable(True)
        ko_action.setData("ko")
        ko_action.setChecked(self.settings.get("language") == "ko")
        ko_action.triggered.connect(lambda: self._change_language("ko"))
        self.lang_menu.addAction(ko_action)
        
        # English
        en_action = QAction(tm.get("lang_en"), self)
        en_action.setCheckable(True)
        en_action.setData("en")
        en_action.setChecked(self.settings.get("language") == "en")
        en_action.triggered.connect(lambda: self._change_language("en"))
        self.lang_menu.addAction(en_action)
        
        # 도움말 메뉴
        help_menu = menubar.addMenu(tm.get("menu_help"))
        
        shortcuts_action = QAction(tm.get("menu_shortcuts"), self)
        shortcuts_action.triggered.connect(self._show_shortcuts)
        help_menu.addAction(shortcuts_action)
        
        help_menu.addSeparator()
        
        about_action = QAction(tm.get("menu_about"), self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _change_language(self, lang_code):
        """언어 변경 및 재시작 안내"""
        current = self.settings.get("language", "auto")
        if current == lang_code:
            return

        self.settings["language"] = lang_code
        save_settings(self.settings)
        
        # 메뉴 상태 업데이트 (체크 표시)
        # 메뉴 상태 업데이트 (체크 표시)
        for action in self.lang_menu.actions():
            if action.isSeparator(): continue
            action.setChecked(action.data() == lang_code)
            
        # 재시작 안내
        QMessageBox.information(
            self, 
            tm.get("restart_required"),
            tm.get("restart_required_msg")
        )
    
    def _update_recent_menu_bar(self):
        """최근 파일 메뉴 업데이트"""
        self.recent_menu_bar.clear()
        recent = self.settings.get("recent_files", [])
        if not recent:
            action = self.recent_menu_bar.addAction(tm.get("no_recent_files"))
            action.setEnabled(False)
        else:
            for path in recent[:10]:
                if os.path.exists(path):
                    action = self.recent_menu_bar.addAction(f"📄 {os.path.basename(path)}")
                    action.triggered.connect(lambda checked, p=path: self._update_preview(p))
    
    def _show_shortcuts(self):
        """단축키 안내 대화상자"""
        shortcuts_text = f"""📑 {APP_NAME} v{VERSION} - {tm.get('shortcuts')}
        
{tm.get('shortcut_open')}
{tm.get('shortcut_exit')}
{tm.get('shortcut_theme')}
{tm.get('shortcut_tabs')}
{tm.get('shortcut_help')}"""
        QMessageBox.information(self, tm.get("shortcuts"), shortcuts_text)
    
    def _show_about(self):
        """정보 대화상자"""
        about_text = f"""📑 {APP_NAME} v{VERSION}

{tm.get('about_desc')}

{tm.get('tech_stack')}
  • Python 3.9+
  • PyQt6 (UI Framework)
  • PyMuPDF (PDF Processing)

📧 Made with ❤️
© 2025-2026"""
        QMessageBox.about(self, f"{APP_NAME} {tm.get('about')}", about_text)
        
    def _create_header(self):
        header = QHBoxLayout()
        header.setSpacing(15)
        
        # 컴팩트한 타이틀 - 테마 통일 (파란색)
        title = QLabel(f"📑 {APP_NAME}")
        title.setObjectName("header")
        header.addWidget(title)
        
        ver_label = QLabel(f"v{VERSION}")
        ver_label.setStyleSheet("color: #666; font-size: 11px;")
        header.addWidget(ver_label)
        
        header.addStretch()
        
        # Theme toggle - objectName으로 스타일 적용
        current_theme = self.settings.get("theme")
        theme_text = tm.get("theme_light") if current_theme == "light" else tm.get("theme_dark") # Default to DARK text if dark theme
        # But wait, existing logic: theme_text = "DARK" if self.settings.get("theme") == "dark" else "LIGHT"
        # The button usually shows the CURRENT theme or the TARGET theme?
        # Usually a toggle button shows the current state or what will happen.
        # Original code: "DARK" if dark else "LIGHT". This suggests it shows the current state.
        
        self.btn_theme = QPushButton(theme_text)
        self.btn_theme.setObjectName("accentBtn")
        self.btn_theme.setMinimumSize(70, 32)
        self.btn_theme.clicked.connect(self._toggle_theme)
        header.addWidget(self.btn_theme)
        
        # Help button - objectName으로 스타일 적용
        btn_help = QPushButton(tm.get("help")) # "도움말" or "Help"
        btn_help.setObjectName("accentBtn")
        btn_help.setMinimumSize(60, 32)
        btn_help.clicked.connect(self._show_help)
        header.addWidget(btn_help)
        
        return header
    
    def _create_preview_panel(self):
        panel = QGroupBox(tm.get("preview_title"))
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        self.preview_label = QLabel(tm.get("preview_default"))
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
        layout.addWidget(self.preview_image, 1)
        
        # 페이지 네비게이션 버튼 - objectName 사용
        nav_layout = QHBoxLayout()
        self.btn_prev_page = QPushButton(tm.get("prev_page"))
        self.btn_prev_page.setObjectName("navBtn")
        self.btn_prev_page.setFixedSize(80, 30)
        self.btn_prev_page.clicked.connect(self._prev_preview_page)
        nav_layout.addWidget(self.btn_prev_page)
        
        self.page_counter = QLabel("1 / 1")
        self.page_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_counter.setStyleSheet("font-weight: bold; min-width: 60px; color: #eaeaea;")
        nav_layout.addWidget(self.page_counter)
        
        self.btn_next_page = QPushButton(tm.get("next_page"))
        self.btn_next_page.setObjectName("navBtn")
        self.btn_next_page.setFixedSize(80, 30)
        self.btn_next_page.clicked.connect(self._next_preview_page)
        nav_layout.addWidget(self.btn_next_page)
        layout.addLayout(nav_layout)
        
        return panel
    
    def _prev_preview_page(self):
        if self._current_preview_page > 0:
            self._current_preview_page -= 1
            self._render_preview_page()
    
    def _next_preview_page(self):
        if hasattr(self, '_preview_total_pages') and self._current_preview_page < self._preview_total_pages - 1:
            self._current_preview_page += 1
            self._render_preview_page()
    
    def _render_preview_page(self):
        if not hasattr(self, '_current_preview_path') or not self._current_preview_path:
            return
        doc = None
        try:
            doc = fitz.open(self._current_preview_path)
            if self._current_preview_page < len(doc):
                page = doc[self._current_preview_page]
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                img_data = bytes(pix.samples)
                img = QImage(img_data, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(img.copy())
                preview_size = self.preview_image.size()
                target_w = max(280, preview_size.width() - 20)
                target_h = max(400, preview_size.height() - 20)
                scaled = pixmap.scaled(target_w, target_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.preview_image.setPixmap(scaled)
                self.page_counter.setText(f"{self._current_preview_page + 1} / {self._preview_total_pages}")
        except Exception as e:
            logger.warning(f"Preview render error: {e}")
        finally:
            if doc:
                doc.close()
    
    def _on_list_item_clicked(self, item):
        """리스트 아이템 클릭 시 미리보기 업데이트"""
        path = item.data(Qt.ItemDataRole.UserRole)
        self._update_preview(path)
    
    
    def _update_preview(self, path):
        if not path or not os.path.exists(path):
            self.preview_label.setText(tm.get("preview_default"))
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
            title = meta.get('title', '-') if meta else '-'
            author = meta.get('author', '-') if meta else '-'
            info = f"""📄 {os.path.basename(path)}

📊 페이지: {len(doc)}p  💾 크기: {size_kb:.1f}KB
📝 제목: {title or '-'}
👤 작성자: {author or '-'}"""
            self.preview_label.setText(info)
            
            # 페이지 네비게이션 변수 초기화
            self._current_preview_path = path
            self._preview_total_pages = len(doc)
            self._current_preview_page = 0
            self.page_counter.setText(f"1 / {len(doc)}")
            
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
        self.btn_theme.setText("DARK" if new_theme == "dark" else "LIGHT")
    
    def _apply_theme(self):
        theme = self.settings.get("theme", "dark")
        is_dark = theme == "dark"
        QApplication.instance().setStyleSheet(DARK_STYLESHEET if is_dark else LIGHT_STYLESHEET)
        
        # 모든 DropZone 위젯 테마 동기화
        for widget in self.findChildren(DropZoneWidget):
            widget.set_theme(is_dark)
        
        # EmptyStateWidget 테마 동기화
        for widget in self.findChildren(EmptyStateWidget):
            widget.set_theme(is_dark)
        
        # FileSelectorWidget 테마 동기화
        for widget in self.findChildren(FileSelectorWidget):
            widget.set_theme(is_dark)
        
        # ThumbnailGridWidget 테마 동기화
        for widget in self.findChildren(ThumbnailGridWidget):
            widget.set_theme(is_dark)
        
        # ZoomablePreviewWidget 테마 동기화
        for widget in self.findChildren(ZoomablePreviewWidget):
            widget.set_theme(is_dark)
        
        # 진행 오버레이 테마 동기화
        if hasattr(self, 'progress_overlay'):
            self.progress_overlay.set_theme(is_dark)
        
        # 미리보기 패널 테마 동기화
        if hasattr(self, 'preview_image'):
            if is_dark:
                self.preview_image.setStyleSheet("""
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #141922, stop:1 #0f1318);
                    border-radius: 12px;
                    border: 1px solid #2d3748;
                """)
                self.preview_label.setStyleSheet("color: #94a3b8; padding: 12px; font-size: 13px; background: transparent;")
                self.page_counter.setStyleSheet("font-weight: 700; min-width: 60px; color: #f0f4f8;")
            else:
                self.preview_image.setStyleSheet("""
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #f8fafc);
                    border-radius: 12px;
                    border: 1px solid #e2e8f0;
                """)
                self.preview_label.setStyleSheet("color: #64748b; padding: 12px; font-size: 13px; background: transparent;")
                self.page_counter.setStyleSheet("font-weight: 700; min-width: 60px; color: #1e293b;")
    
    def _show_help(self):
        QMessageBox.information(self, tm.get("help_title"), f"""📑 {APP_NAME} v{VERSION}

{tm.get("help_intro")}

{tm.get("help_features")}""")
    
    # Worker helpers
    def run_worker(self, mode, output_path=None, **kwargs):
        """작업 스레드 실행 (안전한 동시 작업 처리)"""
        # 이전 Worker 시그널 연결 해제 (누적 방지)
        if self.worker:
            try:
                self.worker.progress_signal.disconnect()
                self.worker.finished_signal.disconnect()
                self.worker.error_signal.disconnect()
            except (TypeError, RuntimeError):
                pass  # 이미 해제되었거나 연결이 없는 경우
        
        # 이전 Worker가 실행 중인지 확인
        if self.worker and self.worker.isRunning():
            # 사용자에게 경고
            result = QMessageBox.question(
                self, "작업 진행 중",
                "이전 작업이 아직 진행 중입니다.\n완료될 때까지 기다리시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if result == QMessageBox.StandardButton.Yes:
                self.worker.wait()  # 완료 대기
            else:
                return  # 새 작업 취소
        
        # output_path 추적 (폴더 열기 기능용)
        if output_path:
            self._last_output_path = output_path
            kwargs['output_path'] = output_path
        elif 'output_path' in kwargs:
            self._last_output_path = kwargs['output_path']
        elif 'output_dir' in kwargs:
            self._last_output_path = kwargs['output_dir']
        
        # 작업 모드에 따른 설명 (Undo에서도 사용)
        mode_descriptions = {
            "merge": "PDF 파일 병합",
            "convert_to_img": "PDF → 이미지 변환",
            "images_to_pdf": "이미지 → PDF 변환",
            "extract_text": "텍스트 추출",
            "split": "페이지 추출",
            "delete_pages": "페이지 삭제",
            "rotate": "페이지 회전",
            "add_page_numbers": "페이지 번호 추가",
            "watermark": "워터마크 적용",
            "encrypt": "PDF 암호화",
            "compress": "PDF 압축",
            "ai_summary": "AI PDF 분석"
        }
        
        # v4.3: Undo 지원 작업 - 백업 생성
        self._pending_undo = None  # 초기화
        undo_supported_modes = ['delete_pages', 'rotate', 'add_page_numbers', 'watermark', 'compress']
        if mode in undo_supported_modes:
            source = kwargs.get('file_path', '')
            output = kwargs.get('output_path', '')
            if source and output:
                backup = self._create_backup_for_undo(source)
                if backup:
                    self._pending_undo = {
                        'action_type': mode,
                        'description': mode_descriptions.get(mode, mode),
                        'backup_path': backup,
                        'source_path': source,
                        'output_path': output
                    }
        
        description = mode_descriptions.get(mode, "처리 중") + "..."
        
        self.worker = WorkerThread(mode, **kwargs)
        self.worker.progress_signal.connect(self._on_progress_update)
        self.worker.finished_signal.connect(self.on_success)
        self.worker.error_signal.connect(self.on_fail)
        self.progress_bar.setValue(0)
        self.btn_open_folder.setVisible(False)
        self.status_label.setText(tm.get("processing_status"))
        self.set_ui_busy(True)
        
        # 진행 오버레이 표시 (개선된 UX)
        self.progress_overlay.show_progress("작업 처리 중...", description)
        
        self.worker.start()
    
    def _on_progress_update(self, value: int):
        """진행률 업데이트 (오버레이 + 상태바)"""
        self.progress_bar.setValue(value)
        self.progress_overlay.update_progress(value)
    
    def _on_worker_cancelled(self):
        """작업 취소 처리"""
        if self.worker and self.worker.isRunning():
            if hasattr(self.worker, 'cancel'):
                self.worker.cancel()
            self.status_label.setText(tm.get("cancelling"))
            # 취소 후 정리
            QTimer.singleShot(500, self._cleanup_cancelled_worker)
    
    def _cleanup_cancelled_worker(self):
        """취소된 작업 정리 (임시 파일 포함)"""
        self.set_ui_busy(False)
        self.progress_overlay.hide_progress()
        self.status_label.setText(tm.get("cancelled"))
        self.progress_bar.setValue(0)
        
        # v4.4: 취소된 작업의 미완성 출력 파일 정리
        if hasattr(self, '_last_output_path') and self._last_output_path:
            output_path = self._last_output_path
            # 파일인 경우 삭제 시도
            if os.path.isfile(output_path):
                try:
                    # 최근 생성된 파일만 삭제 (5초 이내)
                    import time
                    if time.time() - os.path.getmtime(output_path) < 5:
                        os.remove(output_path)
                        logger.info(f"Removed incomplete output file: {output_path}")
                except Exception as e:
                    logger.debug(f"Could not remove cancelled output: {e}")
        
        toast = ToastWidget(tm.get("msg_worker_cancelled"), toast_type='warning', duration=3000)
        toast.show_toast(self)
    
    def on_success(self, msg):
        self.set_ui_busy(False)
        self.progress_overlay.hide_progress()  # 오버레이 숨기기
        self.status_label.setText("✅ 작업 완료!")
        self.progress_bar.setValue(100)
        self.btn_open_folder.setVisible(True)  # 폴더 열기 버튼 표시
        
        # v4.0: AI 요약 결과 처리
        if hasattr(self, '_ai_worker_mode') and self._ai_worker_mode:
            self._ai_worker_mode = False
            if self.worker and hasattr(self.worker, 'kwargs'):
                summary = self.worker.kwargs.get('summary_result', '')
                if summary and hasattr(self, 'txt_summary_result'):
                    self.txt_summary_result.setPlainText(summary)
        
        # v4.3: Undo 등록 (파일 수정 작업)
        if hasattr(self, '_pending_undo') and self._pending_undo:
            undo_info = self._pending_undo
            self._pending_undo = None  # 소비
            
            before_state = {
                "backup_path": undo_info['backup_path'],
                "target_path": undo_info['output_path']
            }
            after_state = {
                "output_path": undo_info['output_path'],
                "target_path": undo_info['output_path']
            }
            
            self.undo_manager.push(
                action_type=undo_info['action_type'],
                description=undo_info['description'],
                before_state=before_state,
                after_state=after_state,
                undo_callback=self._restore_from_backup,
                redo_callback=self._redo_from_output
            )
            logger.info(f"Registered undo for: {undo_info['action_type']}")
        
        # Toast 알림 표시
        toast = ToastWidget("작업이 완료되었습니다!", toast_type='success', duration=4000)
        toast.show_toast(self)
        
        QMessageBox.information(self, "완료", msg)
        QTimer.singleShot(3000, lambda: self.progress_bar.setValue(0))
    
    def on_fail(self, msg):
        self.set_ui_busy(False)
        self.progress_overlay.hide_progress()  # 오버레이 숨기기
        self.status_label.setText("❌ 오류 발생")
        self.progress_bar.setValue(0)
        self.btn_open_folder.setVisible(False)
        
        # Toast 알림 표시
        toast = ToastWidget("작업 중 오류가 발생했습니다", toast_type='error', duration=5000)
        toast.show_toast(self)
        
        QMessageBox.critical(self, "오류", f"작업 중 문제가 발생했습니다.\n{msg}")
    
    def set_ui_busy(self, busy):
        self.tabs.setEnabled(not busy)
        self.btn_open_folder.setEnabled(not busy)

    # ===================== Undo/Redo 헬퍼 =====================
    def _create_backup_for_undo(self, source_path: str) -> str:
        """작업 전 원본 파일 백업 생성"""
        if not source_path or not os.path.exists(source_path):
            return ""
        try:
            import uuid
            backup_name = f"undo_{uuid.uuid4().hex[:8]}_{os.path.basename(source_path)}"
            backup_path = os.path.join(self._undo_backup_dir, backup_name)
            shutil.copy2(source_path, backup_path)
            logger.debug(f"Created undo backup: {backup_path}")
            return backup_path
        except Exception as e:
            logger.warning(f"Failed to create backup: {e}")
            return ""
    
    def _restore_from_backup(self, state: dict):
        """백업에서 파일 복원 (undo 콜백)"""
        backup_path = state.get("backup_path", "")
        target_path = state.get("target_path", "")
        if not backup_path or not target_path:
            logger.warning("Undo: Missing paths")
            return
        if not os.path.exists(backup_path):
            logger.warning(f"Undo: Backup not found: {backup_path}")
            QMessageBox.warning(self, tm.get("undo_failed_title"), tm.get("undo_backup_not_found"))
            return
        try:
            shutil.copy2(backup_path, target_path)
            logger.info(f"Restored from backup: {target_path}")
            # 미리보기 갱신
            self._update_preview(target_path)
            toast = ToastWidget(tm.get("restore_success"), toast_type='success', duration=2000)
            toast.show_toast(self)
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            QMessageBox.warning(self, tm.get("restore_failed_title"), tm.get("restore_failed_msg", str(e)))
    
    def _redo_from_output(self, state: dict):
        """출력 파일로 다시 적용 (redo 콜백)"""
        output_path = state.get("output_path", "")
        target_path = state.get("target_path", "")
        if output_path and target_path and os.path.exists(output_path):
            try:
                shutil.copy2(output_path, target_path)
                logger.info(f"Redo applied: {target_path}")
                self._update_preview(target_path)
            except Exception as e:
                logger.error(f"Redo failed: {e}")
    
    def _register_undo_action(self, action_type: str, description: str, 
                              source_path: str, output_path: str):
        """작업을 undo 히스토리에 등록"""
        backup_path = self._create_backup_for_undo(source_path)
        if not backup_path:
            logger.warning(f"Skipping undo registration for {action_type}: no backup")
            return
        
        before_state = {
            "backup_path": backup_path,
            "target_path": output_path
        }
        after_state = {
            "output_path": output_path,
            "target_path": output_path
        }
        
        self.undo_manager.push(
            action_type=action_type,
            description=description,
            before_state=before_state,
            after_state=after_state,
            undo_callback=self._restore_from_backup,
            redo_callback=self._redo_from_output
        )
    
    def _cleanup_old_undo_backups(self, max_age_hours: int = 24):
        """오래된 undo 백업 파일 정리
        
        Args:
            max_age_hours: 이 시간(시간 단위) 이상 된 파일 삭제
        """
        if not os.path.exists(self._undo_backup_dir):
            return
        
        import time
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        cleaned_count = 0
        
        try:
            for filename in os.listdir(self._undo_backup_dir):
                if not filename.startswith("undo_"):
                    continue
                filepath = os.path.join(self._undo_backup_dir, filename)
                try:
                    file_age = current_time - os.path.getmtime(filepath)
                    if file_age > max_age_seconds:
                        os.remove(filepath)
                        cleaned_count += 1
                except Exception as e:
                    logger.debug(f"Failed to remove old backup {filename}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old undo backup files")
        except Exception as e:
            logger.warning(f"Error during backup cleanup: {e}")
    
    def _cleanup_unused_undo_backups(self):
        """현재 undo 스택에 없는 백업 파일 정리"""
        if not os.path.exists(self._undo_backup_dir):
            return
        
        # 현재 undo/redo 스택에서 사용 중인 백업 경로 수집
        active_backups = set()
        for record in self.undo_manager._undo_stack:
            backup = record.before_state.get("backup_path", "")
            if backup:
                active_backups.add(os.path.basename(backup))
        for record in self.undo_manager._redo_stack:
            backup = record.before_state.get("backup_path", "")
            if backup:
                active_backups.add(os.path.basename(backup))
        
        cleaned_count = 0
        try:
            for filename in os.listdir(self._undo_backup_dir):
                if not filename.startswith("undo_"):
                    continue
                if filename not in active_backups:
                    filepath = os.path.join(self._undo_backup_dir, filename)
                    try:
                        os.remove(filepath)
                        cleaned_count += 1
                    except Exception as e:
                        logger.debug(f"Failed to remove unused backup {filename}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} unused undo backup files")
        except Exception as e:
            logger.warning(f"Error during unused backup cleanup: {e}")

    # ===================== Tab 1: 병합 =====================
    def setup_merge_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Guide
        guide = QLabel(tm.get("guide_merge"))
        guide.setObjectName("desc")
        layout.addWidget(guide)
        
        step1 = QLabel(tm.get("step_merge_1"))
        step1.setObjectName("stepLabel")
        layout.addWidget(step1)
        
        self.merge_list = FileListWidget()
        self.merge_list.itemClicked.connect(self._on_list_item_clicked)
        layout.addWidget(self.merge_list)
        
        # v2.7: 파일 개수 표시
        merge_info_layout = QHBoxLayout()
        self.merge_count_label = QLabel(tm.get("lbl_merge_count").format(0))
        self.merge_count_label.setStyleSheet("color: #888; font-size: 12px;")
        merge_info_layout.addWidget(self.merge_count_label)
        merge_info_layout.addStretch()
        layout.addLayout(merge_info_layout)
        
        # 파일 추가/삭제 시 카운트 업데이트
        self.merge_list.model().rowsInserted.connect(self._update_merge_count)
        self.merge_list.model().rowsRemoved.connect(self._update_merge_count)
        
        btn_box = QHBoxLayout()
        b_add = QPushButton(tm.get("btn_add_files_merge"))
        b_add.setObjectName("secondaryBtn")
        b_add.clicked.connect(self._merge_add_files)
        
        b_del = QPushButton(tm.get("btn_remove_sel"))
        b_del.setObjectName("secondaryBtn")
        b_del.clicked.connect(lambda: [self.merge_list.takeItem(self.merge_list.row(i)) for i in self.merge_list.selectedItems()])
        
        b_clr = QPushButton(tm.get("btn_clear_merge"))
        b_clr.setObjectName("secondaryBtn")
        b_clr.clicked.connect(self._confirm_clear_merge)  # v2.7: 확인 다이얼로그
        
        btn_box.addWidget(b_add)
        btn_box.addWidget(b_del)
        btn_box.addWidget(b_clr)
        btn_box.addStretch()
        layout.addLayout(btn_box)
        
        step2 = QLabel(tm.get("step_merge_2"))
        step2.setObjectName("stepLabel")
        layout.addWidget(step2)
        
        b_run = QPushButton(tm.get("btn_run_merge"))
        b_run.setObjectName("actionBtn")
        b_run.clicked.connect(self.action_merge)
        layout.addWidget(b_run)
        
        self.tabs.addTab(tab, f"📎 {tm.get('tab_merge')}")
    
    def _merge_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, tm.get("dlg_title_pdf"), "", "PDF (*.pdf)")
        for f in files:
            item = QListWidgetItem(f"📄 {os.path.basename(f)}")
            item.setData(Qt.ItemDataRole.UserRole, f)
            item.setToolTip(f)
            self.merge_list.addItem(item)
    
    def _update_merge_count(self):
        """병합 탭 파일 개수 업데이트"""
        count = self.merge_list.count()
        self.merge_count_label.setText(tm.get("lbl_merge_count").format(count))
    
    def _confirm_clear_merge(self):
        """전체 삭제 확인 다이얼로그"""
        if self.merge_list.count() == 0:
            return
        reply = QMessageBox.question(self, tm.get("confirm"), 
                                    tm.get("msg_confirm_clear").format(self.merge_list.count()),
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.merge_list.clear()
    
    def action_merge(self):
        files = self.merge_list.get_all_paths()
        if len(files) < 2:
            return QMessageBox.warning(self, tm.get("info"), tm.get("msg_merge_count_error"))
        save, _ = QFileDialog.getSaveFileName(self, tm.get("save"), "merged.pdf", "PDF (*.pdf)")
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
        grp_img = QGroupBox(tm.get("grp_pdf_to_img"))
        l_img = QVBoxLayout(grp_img)
        step = QLabel(tm.get("step_pdf_to_img"))
        step.setObjectName("stepLabel")
        l_img.addWidget(step)
        self.img_conv_list = FileListWidget()
        self.img_conv_list.setMaximumHeight(100)
        l_img.addWidget(self.img_conv_list)
        self.img_conv_list.itemClicked.connect(self._on_list_item_clicked)
        self.img_conv_list.fileAdded.connect(self._update_preview)
        
        # 버튼 레이아웃
        btn_layout_img = QHBoxLayout()
        btn_add_pdf = QPushButton(tm.get("btn_add_pdf"))
        btn_add_pdf.clicked.connect(self._add_pdf_for_img)
        
        btn_clear_img = QPushButton(tm.get("btn_clear_all"))
        btn_clear_img.setToolTip(tm.get("tooltip_clear_list"))
        btn_clear_img.setStyleSheet("""
            QPushButton { background-color: #3e272b; color: #ff6b6b; border: 1px solid #5c3a3a; padding: 10px; }
            QPushButton:hover { background-color: #5c3a3a; color: #ff8787; }
        """)
        btn_clear_img.clicked.connect(self.img_conv_list.clear)
        
        btn_layout_img.addWidget(btn_add_pdf)
        btn_layout_img.addWidget(btn_clear_img)
        l_img.addLayout(btn_layout_img)
        
        opt = QHBoxLayout()
        opt.addWidget(QLabel(tm.get("lbl_format")))
        self.cmb_fmt = QComboBox()
        self.cmb_fmt.addItems(["png", "jpg"])
        opt.addWidget(self.cmb_fmt)
        opt.addWidget(QLabel(tm.get("lbl_dpi")))
        self.spn_dpi = QSpinBox()
        self.spn_dpi.setRange(72, 600)
        self.spn_dpi.setValue(150)
        opt.addWidget(self.spn_dpi)
        
        # 프리셋 버튼
        btn_save_preset = QPushButton("💾")
        btn_save_preset.setToolTip("현재 설정을 프리셋으로 저장")
        btn_save_preset.setFixedWidth(36)
        btn_save_preset.clicked.connect(self._save_convert_preset)
        opt.addWidget(btn_save_preset)
        
        btn_load_preset = QPushButton("📂")
        btn_load_preset.setToolTip("저장된 프리셋 불러오기")
        btn_load_preset.setFixedWidth(36)
        btn_load_preset.clicked.connect(self._load_convert_preset)
        opt.addWidget(btn_load_preset)
        
        opt.addStretch()
        l_img.addLayout(opt)
        
        b_img = QPushButton(tm.get("btn_convert_to_img"))
        b_img.clicked.connect(self.action_img)
        l_img.addWidget(b_img)
        content_layout.addWidget(grp_img)
        
        # 이미지 → PDF
        grp_img2pdf = QGroupBox(tm.get("grp_img_to_pdf"))
        l_i2p = QVBoxLayout(grp_img2pdf)
        step2 = QLabel(tm.get("step_img_to_pdf"))
        step2.setObjectName("stepLabel")
        l_i2p.addWidget(step2)
        self.img_list = ImageListWidget()
        l_i2p.addWidget(self.img_list)
        
        btn_i2p = QHBoxLayout()
        b_add_img = QPushButton(tm.get("btn_add_img"))
        b_add_img.setObjectName("secondaryBtn")
        b_add_img.clicked.connect(self._add_images)
        b_clr_img = QPushButton(tm.get("btn_clear_img"))
        b_clr_img.setObjectName("secondaryBtn")
        b_clr_img.clicked.connect(self.img_list.clear)
        btn_i2p.addWidget(b_add_img)
        btn_i2p.addWidget(b_clr_img)
        btn_i2p.addStretch()
        l_i2p.addLayout(btn_i2p)
        
        b_i2p = QPushButton(tm.get("btn_convert_to_pdf"))
        b_i2p.clicked.connect(self.action_img_to_pdf)
        l_i2p.addWidget(b_i2p)
        content_layout.addWidget(grp_img2pdf)
        
        # 텍스트 추출
        grp_txt = QGroupBox(tm.get("grp_extract_text"))
        l_txt = QVBoxLayout(grp_txt)
        step_txt = QLabel(tm.get("lbl_extract_drag"))
        step_txt.setObjectName("stepLabel")
        l_txt.addWidget(step_txt)
        self.txt_conv_list = FileListWidget()
        self.txt_conv_list.setMaximumHeight(100)
        l_txt.addWidget(self.txt_conv_list)
        self.txt_conv_list.itemClicked.connect(self._on_list_item_clicked)
        self.txt_conv_list.fileAdded.connect(self._update_preview)
        
        # 버튼 레이아웃
        btn_layout_txt = QHBoxLayout()
        btn_add_txt = QPushButton(tm.get("btn_add_pdf"))
        btn_add_txt.clicked.connect(self._add_pdf_for_txt)
        
        btn_clear_txt = QPushButton(tm.get("btn_clear_all"))
        btn_clear_txt.setToolTip(tm.get("tooltip_clear_list"))
        btn_clear_txt.setStyleSheet("""
            QPushButton { background-color: #3e272b; color: #ff6b6b; border: 1px solid #5c3a3a; padding: 10px; }
            QPushButton:hover { background-color: #5c3a3a; color: #ff8787; }
        """)
        btn_clear_txt.clicked.connect(self.txt_conv_list.clear)
        
        btn_layout_txt.addWidget(btn_add_txt)
        btn_layout_txt.addWidget(btn_clear_txt)
        l_txt.addLayout(btn_layout_txt)
        b_txt = QPushButton(tm.get("btn_save_text"))
        b_txt.clicked.connect(self.action_txt)
        l_txt.addWidget(b_txt)
        content_layout.addWidget(grp_txt)
        
        
        # PDF → Word 변환 기능 제거됨 (v4.2)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.tabs.addTab(tab, f"🔄 {tm.get('tab_convert')}")
    
    def _add_images(self):
        files, _ = QFileDialog.getOpenFileNames(self, tm.get("dlg_title_img"), "", "이미지 (*.png *.jpg *.jpeg *.bmp *.gif *.webp)")
        for f in files:
            item = QListWidgetItem(f"🖼️ {os.path.basename(f)}")
            item.setData(Qt.ItemDataRole.UserRole, f)
            item.setToolTip(f)
            self.img_list.addItem(item)
    
    def _add_pdf_for_img(self):
        """이미지 변환용 PDF 추가"""
        files, _ = QFileDialog.getOpenFileNames(self, "PDF 선택", "", "PDF (*.pdf)")
        for f in files:
            self.img_conv_list.add_file(f)
    
    def _add_pdf_for_txt(self):
        """텍스트 추출용 PDF 추가"""
        files, _ = QFileDialog.getOpenFileNames(self, "PDF 선택", "", "PDF (*.pdf)")
        for f in files:
            self.txt_conv_list.add_file(f)
    
    def _save_convert_preset(self):
        """변환 설정 프리셋 저장"""
        name, ok = QInputDialog.getText(self, "프리셋 저장", "프리셋 이름:")
        if ok and name:
            presets = self.settings.get("convert_presets", {})
            presets[name] = {
                "format": self.cmb_fmt.currentText(),
                "dpi": self.spn_dpi.value()
            }
            self.settings["convert_presets"] = presets
            save_settings(self.settings)
            toast = ToastWidget(f"프리셋 '{name}' 저장됨", toast_type='success', duration=2000)
            toast.show_toast(self)
    
    def _load_convert_preset(self):
        """변환 설정 프리셋 불러오기"""
        presets = self.settings.get("convert_presets", {})
        if not presets:
            QMessageBox.information(self, "프리셋", "저장된 프리셋이 없습니다.")
            return
        
        # 프리셋 선택 다이얼로그
        name, ok = QInputDialog.getItem(self, "프리셋 불러오기", "프리셋 선택:", 
                                        list(presets.keys()), 0, False)
        if ok and name:
            preset = presets[name]
            idx = self.cmb_fmt.findText(preset.get("format", "png"))
            if idx >= 0:
                self.cmb_fmt.setCurrentIndex(idx)
            self.spn_dpi.setValue(preset.get("dpi", 150))
            toast = ToastWidget(f"프리셋 '{name}' 적용됨", toast_type='info', duration=2000)
            toast.show_toast(self)
    
    def _print_pdf(self, path):
        """PDF 직접 인쇄"""
        from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
        
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, tm.get("print_title"), tm.get("print_no_file"))
            return
        
        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            dialog = QPrintDialog(printer, self)
            
            if dialog.exec() == QPrintDialog.DialogCode.Accepted:
                # 시스템 기본 PDF 뷰어로 인쇄 명령 전송
                if sys.platform == 'win32':
                    os.startfile(path, 'print')
                else:
                    subprocess.run(['lpr', path])
                toast = ToastWidget(tm.get("print_sent"), toast_type='success', duration=2000)
                toast.show_toast(self)
        except Exception as e:
            QMessageBox.warning(self, tm.get("print_error_title"), tm.get("print_error_msg", str(e)))
    
    def action_img(self):
        paths = self.img_conv_list.get_all_paths()
        if not paths:
            return QMessageBox.warning(self, "알림", "PDF 파일을 추가하세요.")
        d = QFileDialog.getExistingDirectory(self, "저장 폴더 선택")
        if d:
            self.run_worker("convert_to_img", file_paths=paths, output_dir=d, 
                          fmt=self.cmb_fmt.currentText(), dpi=self.spn_dpi.value())
    
    def action_img_to_pdf(self):
        files = self.img_list.get_all_paths()
        if not files:
            return QMessageBox.warning(self, "알림", "이미지 파일을 추가하세요.")
        save, _ = QFileDialog.getSaveFileName(self, "저장", "images.pdf", "PDF (*.pdf)")
        if save:
            self.run_worker("images_to_pdf", files=files, output_path=save)
    
    def action_txt(self):
        paths = self.txt_conv_list.get_all_paths()
        if not paths:
            return QMessageBox.warning(self, "알림", "PDF 파일을 추가하세요.")
        d = QFileDialog.getExistingDirectory(self, "저장 폴더 선택")
        if d:
            self.run_worker("extract_text", file_paths=paths, output_dir=d)

    # ===================== Tab 3: 페이지 =====================
    def setup_page_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # 🔢 페이지 번호 삽입 (최상단)
        grp_pn = QGroupBox(tm.get("grp_page_number"))
        l_pn = QVBoxLayout(grp_pn)
        self.sel_pn = FileSelectorWidget()
        self.sel_pn.pathChanged.connect(self._update_preview)
        l_pn.addWidget(self.sel_pn)
        guide_pn = QLabel(tm.get("guide_page_format"))
        guide_pn.setObjectName("desc")
        l_pn.addWidget(guide_pn)
        opt_pn = QHBoxLayout()
        opt_pn.addWidget(QLabel(tm.get("lbl_position")))
        self.cmb_pn_pos = QComboBox()
        self.cmb_pn_pos.addItems(["하단 중앙", "상단 중앙", "하단 좌측", "하단 우측", "상단 좌측", "상단 우측"]) # Note: These specific values might need mapping logic adjustment if translated
        self.cmb_pn_pos.setToolTip("페이지 번호 위치 선택") 
        opt_pn.addWidget(self.cmb_pn_pos)
        opt_pn.addWidget(QLabel(tm.get("lbl_format")))
        self.cmb_pn_format = QComboBox()
        self.cmb_pn_format.addItems(["{n} / {total}", "Page {n} of {total}", "- {n} -", "{n}", "페이지 {n}"])
        self.cmb_pn_format.setEditable(True)
        opt_pn.addWidget(self.cmb_pn_format)
        l_pn.addLayout(opt_pn)
        b_pn = QPushButton(tm.get("btn_insert_page_number"))
        b_pn.clicked.connect(self.action_page_numbers)
        l_pn.addWidget(b_pn)
        content_layout.addWidget(grp_pn)
        
        # 추출
        grp_split = QGroupBox(tm.get("grp_split_page"))
        l_s = QVBoxLayout(grp_split)
        self.sel_split = FileSelectorWidget()
        self.sel_split.pathChanged.connect(self._update_preview)
        l_s.addWidget(self.sel_split)
        h = QHBoxLayout()
        h.addWidget(QLabel(tm.get("lbl_split_range")))
        self.inp_range = QLineEdit()
        self.inp_range.setPlaceholderText("1, 3-5, 8")
        h.addWidget(self.inp_range)
        l_s.addLayout(h)
        b_s = QPushButton(tm.get("btn_split_run"))
        b_s.clicked.connect(self.action_split)
        l_s.addWidget(b_s)
        content_layout.addWidget(grp_split)
        
        # 삭제
        grp_del = QGroupBox(tm.get("grp_delete_page"))
        l_d = QVBoxLayout(grp_del)
        self.sel_del = FileSelectorWidget()
        self.sel_del.pathChanged.connect(self._update_preview)
        l_d.addWidget(self.sel_del)
        h2 = QHBoxLayout()
        h2.addWidget(QLabel(tm.get("lbl_delete_range")))
        self.inp_del_range = QLineEdit()
        self.inp_del_range.setPlaceholderText("2, 4-6")
        h2.addWidget(self.inp_del_range)
        l_d.addLayout(h2)
        b_d = QPushButton(tm.get("btn_delete_run"))
        b_d.clicked.connect(self.action_delete_pages)
        l_d.addWidget(b_d)
        content_layout.addWidget(grp_del)
        
        # 회전
        grp_rot = QGroupBox(tm.get("grp_rotate_page"))
        l_r = QVBoxLayout(grp_rot)
        self.sel_rot = FileSelectorWidget()
        l_r.addWidget(self.sel_rot)
        h3 = QHBoxLayout()
        h3.addWidget(QLabel(tm.get("lbl_rotate_angle")))
        self.cmb_rot = QComboBox()
        self.cmb_rot.addItems([tm.get("combo_rotate_90"), tm.get("combo_rotate_180"), tm.get("combo_rotate_270")])
        h3.addWidget(self.cmb_rot)
        h3.addStretch()
        l_r.addLayout(h3)
        b_r = QPushButton(tm.get("btn_rotate_run"))
        b_r.clicked.connect(self.action_rotate)
        l_r.addWidget(b_r)
        content_layout.addWidget(grp_rot)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.tabs.addTab(tab, f"✂️ {tm.get('tab_page')}")
    
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
    
    def action_page_numbers(self):
        """페이지 번호 삽입 실행"""
        path = self.sel_pn.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        
        # 위치 매핑
        pos_map = {
            "하단 중앙": "bottom", "상단 중앙": "top",
            "하단 좌측": "bottom-left", "하단 우측": "bottom-right",
            "상단 좌측": "top-left", "상단 우측": "top-right"
        }
        position = pos_map.get(self.cmb_pn_pos.currentText(), "bottom")
        format_str = self.cmb_pn_format.currentText()
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "numbered.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("add_page_numbers", file_path=path, output_path=s,
                          position=position, format=format_str)

    # ===================== Tab 4: 편집/보안 =====================
    def setup_edit_sec_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # 메타데이터
        # 메타데이터
        grp_meta = QGroupBox(tm.get("grp_metadata"))
        l_m = QVBoxLayout(grp_meta)
        self.sel_meta = FileSelectorWidget()
        self.sel_meta.pathChanged.connect(self._load_metadata)
        l_m.addWidget(self.sel_meta)
        self.sel_meta.pathChanged.connect(self._update_preview)
        form = QFormLayout()
        self.inp_title = QLineEdit()
        self.inp_author = QLineEdit()
        self.inp_subj = QLineEdit()
        form.addRow(tm.get("lbl_title"), self.inp_title)
        form.addRow(tm.get("lbl_author"), self.inp_author)
        form.addRow(tm.get("lbl_subject"), self.inp_subj)
        l_m.addLayout(form)
        b_m = QPushButton(tm.get("btn_save_metadata"))
        b_m.clicked.connect(self.action_metadata)
        l_m.addWidget(b_m)
        content_layout.addWidget(grp_meta)
        
        # 워터마크
        grp_wm = QGroupBox(tm.get("grp_watermark"))
        l_w = QVBoxLayout(grp_wm)
        self.sel_wm = FileSelectorWidget()
        l_w.addWidget(self.sel_wm)
        self.sel_wm.pathChanged.connect(self._update_preview)
        h_w = QHBoxLayout()
        self.inp_wm = QLineEdit()
        self.inp_wm.setPlaceholderText(tm.get("ph_watermark_text"))
        h_w.addWidget(self.inp_wm)
        self.cmb_wm_color = QComboBox()
        self.cmb_wm_color.addItems([tm.get("color_gray"), tm.get("color_black"), tm.get("color_red"), tm.get("color_blue")])
        h_w.addWidget(self.cmb_wm_color)
        l_w.addLayout(h_w)
        b_w = QPushButton(tm.get("btn_apply_watermark"))
        b_w.clicked.connect(self.action_watermark)
        l_w.addWidget(b_w)
        content_layout.addWidget(grp_wm)
        
        # 보안
        grp_sec = QGroupBox(tm.get("grp_security"))
        l_sec = QVBoxLayout(grp_sec)
        self.sel_sec = FileSelectorWidget()
        l_sec.addWidget(self.sel_sec)
        self.sel_sec.pathChanged.connect(self._update_preview)
        h_sec = QHBoxLayout()
        self.inp_pw = QLineEdit()
        self.inp_pw.setPlaceholderText(tm.get("ph_password"))
        self.inp_pw.setEchoMode(QLineEdit.EchoMode.Password)
        h_sec.addWidget(self.inp_pw)
        b_enc = QPushButton(tm.get("btn_encrypt"))
        b_enc.clicked.connect(self.action_protect)
        h_sec.addWidget(b_enc)
        b_comp = QPushButton(tm.get("btn_compress"))
        b_comp.clicked.connect(self.action_compress)
        h_sec.addWidget(b_comp)
        l_sec.addLayout(h_sec)
        content_layout.addWidget(grp_sec)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.tabs.addTab(tab, f"🔒 {tm.get('tab_edit')}")
    
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
        except Exception:
            pass
    
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
        
        guide = QLabel(tm.get("guide_reorder"))
        guide.setObjectName("desc")
        layout.addWidget(guide)
        
        step1 = QLabel(tm.get("step_reorder_1"))
        step1.setObjectName("stepLabel")
        layout.addWidget(step1)
        
        self.sel_reorder = FileSelectorWidget()
        self.sel_reorder.pathChanged.connect(self._load_pages_for_reorder)
        layout.addWidget(self.sel_reorder)
        self.sel_reorder.pathChanged.connect(self._update_preview)
        
        step2 = QLabel(tm.get("step_reorder_2"))
        step2.setObjectName("stepLabel")
        layout.addWidget(step2)
        
        self.reorder_list = QListWidget()
        self.reorder_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.reorder_list.setMinimumHeight(150)
        self.reorder_list.setToolTip(tm.get("tooltip_reorder_list"))
        layout.addWidget(self.reorder_list)
        
        btn_box = QHBoxLayout()
        b_reverse = QPushButton(tm.get("btn_reverse_order"))
        b_reverse.setObjectName("secondaryBtn")
        b_reverse.clicked.connect(self._reverse_pages)
        btn_box.addWidget(b_reverse)
        btn_box.addStretch()
        layout.addLayout(btn_box)
        
        b_run = QPushButton(tm.get("btn_save_order"))
        b_run.setObjectName("actionBtn")
        b_run.clicked.connect(self.action_reorder)
        layout.addWidget(b_run)
        
        self.tabs.addTab(tab, f"🔀 {tm.get('tab_reorder')}")
    
    def _load_pages_for_reorder(self, path):
        """페이지 목록 로드"""
        self.reorder_list.clear()
        if not path or not os.path.exists(path):
            return
        try:
            doc = fitz.open(path)
            for i in range(len(doc)):
                item = QListWidgetItem(tm.get("msg_page_num", i+1))
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
        
        guide = QLabel(tm.get("guide_batch"))
        guide.setObjectName("desc")
        content_layout.addWidget(guide)
        
        step1 = QLabel(tm.get("step_batch_1"))
        step1.setObjectName("stepLabel")
        content_layout.addWidget(step1)
        
        self.batch_list = FileListWidget()
        self.batch_list.itemClicked.connect(self._on_list_item_clicked)
        content_layout.addWidget(self.batch_list)
        
        btn_box = QHBoxLayout()
        b_add = QPushButton(tm.get("btn_add_files"))
        b_add.setObjectName("secondaryBtn")
        b_add.clicked.connect(self._batch_add_files)
        b_folder = QPushButton(tm.get("btn_add_folder"))
        b_folder.setObjectName("secondaryBtn")
        b_folder.clicked.connect(self._batch_add_folder)
        b_clr = QPushButton(tm.get("btn_clear_list"))
        b_clr.setObjectName("secondaryBtn")
        b_clr.clicked.connect(self.batch_list.clear)
        btn_box.addWidget(b_add)
        btn_box.addWidget(b_folder)
        btn_box.addWidget(b_clr)
        btn_box.addStretch()
        content_layout.addLayout(btn_box)
        
        step2 = QLabel(tm.get("step_batch_2"))
        step2.setObjectName("stepLabel")
        content_layout.addWidget(step2)
        
        # 작업 선택
        opt_layout = QHBoxLayout()
        opt_layout.addWidget(QLabel(tm.get("lbl_operation")))
        self.cmb_batch_op = QComboBox()
        self.cmb_batch_op.addItems([tm.get("op_compress"), tm.get("op_watermark"), tm.get("op_encrypt"), tm.get("op_rotate")])
        opt_layout.addWidget(self.cmb_batch_op)
        opt_layout.addStretch()
        content_layout.addLayout(opt_layout)
        
        # 워터마크/암호 옵션
        opt_layout2 = QHBoxLayout()
        opt_layout2.addWidget(QLabel(tm.get("lbl_batch_option")))
        self.inp_batch_opt = QLineEdit()
        self.inp_batch_opt.setPlaceholderText(tm.get("ph_batch_option"))
        opt_layout2.addWidget(self.inp_batch_opt)
        content_layout.addLayout(opt_layout2)
        
        step3 = QLabel(tm.get("step_batch_3"))
        step3.setObjectName("stepLabel")
        content_layout.addWidget(step3)
        
        b_run = QPushButton(tm.get("btn_run_batch"))
        b_run.setObjectName("actionBtn")
        b_run.clicked.connect(self.action_batch)
        content_layout.addWidget(b_run)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.tabs.addTab(tab, f"📦 {tm.get('tab_batch')}")
    
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

    # ===================== Tab 7: 고급 기능 =====================
    def setup_advanced_tab(self):
        """고급 기능 탭 - 4개 서브탭으로 구성"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 서브 탭 위젯
        sub_tabs = QTabWidget()
        sub_tabs.setDocumentMode(True)
        
        # 1. 편집 서브탭
        sub_tabs.addTab(self._create_edit_subtab(), f"✏️ {tm.get('subtab_edit')}")
        # 2. 추출 서브탭
        sub_tabs.addTab(self._create_extract_subtab(), f"📊 {tm.get('subtab_extract')}")
        # 3. 마크업 서브탭
        sub_tabs.addTab(self._create_markup_subtab(), f"📝 {tm.get('subtab_markup')}")
        # 4. 기타 서브탭
        sub_tabs.addTab(self._create_misc_subtab(), f"📎 {tm.get('subtab_misc')}")
        
        layout.addWidget(sub_tabs)
        self.tabs.addTab(tab, f"🔧 {tm.get('tab_advanced')}")
    
    def _create_edit_subtab(self):
        """편집 서브탭: 분할, 페이지 번호, 스탬프, 크롭, 빈 페이지, 크기 변경, 복제, 역순"""
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        
        # PDF 분할
        grp_split = QGroupBox(tm.get("grp_split_pdf"))
        l_split = QVBoxLayout(grp_split)
        self.sel_split_adv = FileSelectorWidget()
        self.sel_split_adv.pathChanged.connect(self._update_preview)
        l_split.addWidget(self.sel_split_adv)
        opt_split = QHBoxLayout()
        opt_split.addWidget(QLabel(tm.get("lbl_split_mode")))
        self.cmb_split_mode = QComboBox()
        self.cmb_split_mode.addItems([tm.get("mode_split_page"), tm.get("mode_split_range")])
        opt_split.addWidget(self.cmb_split_mode)
        self.inp_split_range = QLineEdit()
        self.inp_split_range.setPlaceholderText(tm.get("ph_split_range"))
        opt_split.addWidget(self.inp_split_range)
        l_split.addLayout(opt_split)
        b_split = QPushButton(tm.get("btn_split_pdf"))
        b_split.setToolTip("PDF를 여러 파일로 분할합니다")
        b_split.clicked.connect(self.action_split_adv)
        l_split.addWidget(b_split)
        layout.addWidget(grp_split)
        
        # 스탬프
        grp_stamp = QGroupBox(tm.get("grp_stamp"))
        l_stamp = QVBoxLayout(grp_stamp)
        self.sel_stamp = FileSelectorWidget()
        self.sel_stamp.pathChanged.connect(self._update_preview)
        l_stamp.addWidget(self.sel_stamp)
        opt_stamp = QHBoxLayout()
        opt_stamp.addWidget(QLabel(tm.get("lbl_stamp_text")))
        self.cmb_stamp = QComboBox()
        self.cmb_stamp.addItems([tm.get("stamp_confidential"), tm.get("stamp_approved"), tm.get("stamp_draft"), tm.get("stamp_final"), tm.get("stamp_no_copy")])
        self.cmb_stamp.setEditable(True)
        opt_stamp.addWidget(self.cmb_stamp)
        opt_stamp.addWidget(QLabel(tm.get("lbl_stamp_pos")))
        self.cmb_stamp_pos = QComboBox()
        self.cmb_stamp_pos.addItems([tm.get("pos_top_right"), tm.get("pos_top_left"), tm.get("pos_bottom_right"), tm.get("pos_bottom_left")])
        opt_stamp.addWidget(self.cmb_stamp_pos)
        l_stamp.addLayout(opt_stamp)
        b_stamp = QPushButton(tm.get("btn_add_stamp"))
        b_stamp.clicked.connect(self.action_stamp)
        l_stamp.addWidget(b_stamp)
        layout.addWidget(grp_stamp)
        
        # 여백 자르기
        grp_crop = QGroupBox(tm.get("grp_crop"))
        l_crop = QVBoxLayout(grp_crop)
        self.sel_crop = FileSelectorWidget()
        self.sel_crop.pathChanged.connect(self._update_preview)
        l_crop.addWidget(self.sel_crop)
        opt_crop = QHBoxLayout()
        sides = ["left", "top", "right", "bottom"]
        labels = [tm.get("lbl_left"), tm.get("lbl_top"), tm.get("lbl_right"), tm.get("lbl_bottom")]
        py_sides = ["좌", "상", "우", "하"] # Keep py names as is for attribute access unless refactored
        for i, side_name in enumerate(py_sides):
            opt_crop.addWidget(QLabel(labels[i]))
            spn = QSpinBox()
            spn.setRange(0, 200)
            spn.setValue(20)
            spn.setToolTip(tm.get("tooltip_crop"))
            setattr(self, f"spn_crop_{side_name}", spn)
            opt_crop.addWidget(spn)
        l_crop.addLayout(opt_crop)
        b_crop = QPushButton(tm.get("btn_crop"))
        b_crop.clicked.connect(self.action_crop)
        l_crop.addWidget(b_crop)
        layout.addWidget(grp_crop)
        
        # 빈 페이지 삽입
        grp_blank = QGroupBox(tm.get("grp_blank_page"))
        l_blank = QVBoxLayout(grp_blank)
        self.sel_blank = FileSelectorWidget()
        self.sel_blank.pathChanged.connect(self._update_preview)
        l_blank.addWidget(self.sel_blank)
        opt_blank = QHBoxLayout()
        opt_blank.addWidget(QLabel(tm.get("lbl_blank_pos")))
        self.spn_blank_pos = QSpinBox()
        self.spn_blank_pos.setRange(1, 999)
        self.spn_blank_pos.setValue(1)
        opt_blank.addWidget(self.spn_blank_pos)
        opt_blank.addStretch()
        l_blank.addLayout(opt_blank)
        b_blank = QPushButton(tm.get("btn_insert_blank"))
        b_blank.clicked.connect(self.action_blank_page)
        l_blank.addWidget(b_blank)
        layout.addWidget(grp_blank)
        
        # 페이지 크기 변경
        grp_resize = QGroupBox(tm.get("grp_resize_page"))
        l_resize = QVBoxLayout(grp_resize)
        self.sel_resize = FileSelectorWidget()
        self.sel_resize.pathChanged.connect(self._update_preview)
        l_resize.addWidget(self.sel_resize)
        resize_opts = QHBoxLayout()
        resize_opts.addWidget(QLabel(tm.get("lbl_size")))
        self.cmb_resize = QComboBox()
        self.cmb_resize.addItems(["A4", "A3", "Letter", "Legal"])
        resize_opts.addWidget(self.cmb_resize)
        resize_opts.addStretch()
        l_resize.addLayout(resize_opts)
        b_resize = QPushButton(tm.get("btn_resize"))
        b_resize.clicked.connect(self.action_resize_pages)
        l_resize.addWidget(b_resize)
        layout.addWidget(grp_resize)
        
        # 페이지 복제
        grp_dup = QGroupBox(tm.get("grp_duplicate"))
        l_dup = QVBoxLayout(grp_dup)
        self.sel_dup = FileSelectorWidget()
        self.sel_dup.pathChanged.connect(self._update_preview)
        l_dup.addWidget(self.sel_dup)
        dup_opts = QHBoxLayout()
        dup_opts.addWidget(QLabel(tm.get("tab_page") + ":")) # Reuse tab_page key for "Page"
        self.spn_dup_page = QSpinBox()
        self.spn_dup_page.setRange(1, 9999)
        dup_opts.addWidget(self.spn_dup_page)
        dup_opts.addWidget(QLabel(tm.get("lbl_dup_count")))
        self.spn_dup_count = QSpinBox()
        self.spn_dup_count.setRange(1, 100)
        self.spn_dup_count.setValue(1)
        dup_opts.addWidget(self.spn_dup_count)
        dup_opts.addStretch()
        l_dup.addLayout(dup_opts)
        b_dup = QPushButton(tm.get("btn_duplicate"))
        b_dup.clicked.connect(self.action_duplicate_page)
        l_dup.addWidget(b_dup)
        layout.addWidget(grp_dup)
        
        # 역순 정렬
        grp_rev = QGroupBox(tm.get("grp_reverse_page"))
        l_rev = QVBoxLayout(grp_rev)
        self.sel_rev = FileSelectorWidget()
        self.sel_rev.pathChanged.connect(self._update_preview)
        l_rev.addWidget(self.sel_rev)
        b_rev = QPushButton(tm.get("btn_reverse_page"))
        b_rev.setToolTip("페이지 순서를 뒤집습니다")
        b_rev.clicked.connect(self.action_reverse_pages)
        l_rev.addWidget(b_rev)
        layout.addWidget(grp_rev)
        
        layout.addStretch()
        scroll.setWidget(content)
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        return widget
    
    def _create_extract_subtab(self):
        """추출 서브탭: 링크, 이미지, 테이블, 북마크, 정보, Markdown"""
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        
        # 링크 추출
        grp_links = QGroupBox(tm.get("grp_extract_link"))
        l_links = QVBoxLayout(grp_links)
        self.sel_links = FileSelectorWidget()
        self.sel_links.pathChanged.connect(self._update_preview)
        l_links.addWidget(self.sel_links)
        b_links = QPushButton(tm.get("btn_extract_link"))
        b_links.setToolTip("PDF에 포함된 모든 URL 추출")
        b_links.clicked.connect(self.action_extract_links)
        l_links.addWidget(b_links)
        layout.addWidget(grp_links)
        
        # 이미지 추출
        grp_extract = QGroupBox(tm.get("grp_extract_img"))
        l_extract = QVBoxLayout(grp_extract)
        self.sel_extract = FileSelectorWidget()
        self.sel_extract.pathChanged.connect(self._update_preview)
        l_extract.addWidget(self.sel_extract)
        b_extract = QPushButton(tm.get("btn_extract_img_adv"))
        b_extract.setToolTip("PDF에 포함된 모든 이미지 추출")
        b_extract.clicked.connect(self.action_extract_images)
        l_extract.addWidget(b_extract)
        layout.addWidget(grp_extract)
        
        # 테이블 추출
        grp_table = QGroupBox(tm.get("grp_extract_table"))
        l_table = QVBoxLayout(grp_table)
        self.sel_table = FileSelectorWidget()
        self.sel_table.pathChanged.connect(self._update_preview)
        l_table.addWidget(self.sel_table)
        b_table = QPushButton(tm.get("btn_extract_table"))
        b_table.setToolTip("PDF의 표 데이터를 CSV로 추출")
        b_table.clicked.connect(self.action_extract_tables)
        l_table.addWidget(b_table)
        layout.addWidget(grp_table)
        
        # 북마크 추출
        grp_bm = QGroupBox(tm.get("grp_extract_bookmark"))
        l_bm = QVBoxLayout(grp_bm)
        self.sel_bm = FileSelectorWidget()
        self.sel_bm.pathChanged.connect(self._update_preview)
        l_bm.addWidget(self.sel_bm)
        b_bm = QPushButton(tm.get("btn_extract_bookmark"))
        b_bm.setToolTip("PDF의 목차/북마크 구조 추출")
        b_bm.clicked.connect(self.action_get_bookmarks)
        l_bm.addWidget(b_bm)
        layout.addWidget(grp_bm)
        
        # PDF 정보
        grp_info = QGroupBox(tm.get("grp_pdf_info"))
        l_info = QVBoxLayout(grp_info)
        self.sel_info = FileSelectorWidget()
        self.sel_info.pathChanged.connect(self._update_preview)
        l_info.addWidget(self.sel_info)
        b_info = QPushButton(tm.get("btn_extract_info"))
        b_info.setToolTip("페이지 수, 글자 수, 폰트 등 상세 정보")
        b_info.clicked.connect(self.action_pdf_info)
        l_info.addWidget(b_info)
        layout.addWidget(grp_info)
        
        # Markdown 추출
        grp_md = QGroupBox(tm.get("grp_extract_md"))
        l_md = QVBoxLayout(grp_md)
        self.sel_md = FileSelectorWidget()
        self.sel_md.pathChanged.connect(self._update_preview)
        l_md.addWidget(self.sel_md)
        b_md = QPushButton(tm.get("btn_extract_md"))
        b_md.setToolTip("PDF 텍스트를 Markdown 형식으로 저장")
        b_md.clicked.connect(self.action_extract_markdown)
        l_md.addWidget(b_md)
        layout.addWidget(grp_md)
        
        layout.addStretch()
        scroll.setWidget(content)
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        return widget
    
    def _create_markup_subtab(self):
        """마크업 서브탭: 검색, 하이라이트, 주석, 텍스트 마크업, 배경색, 교정"""
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        
        # 텍스트 검색 & 하이라이트
        grp_search = QGroupBox(tm.get("grp_search_hi"))
        l_search = QVBoxLayout(grp_search)
        self.sel_search = FileSelectorWidget()
        self.sel_search.pathChanged.connect(self._update_preview)
        l_search.addWidget(self.sel_search)
        search_opts = QHBoxLayout()
        search_opts.addWidget(QLabel(tm.get("lbl_keyword")))
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText(tm.get("ph_search"))
        search_opts.addWidget(self.inp_search)
        l_search.addLayout(search_opts)
        search_btns = QHBoxLayout()
        b_search = QPushButton(tm.get("btn_search_text"))
        b_search.setToolTip(tm.get("tooltip_search_text"))
        b_search.clicked.connect(self.action_search_text)
        search_btns.addWidget(b_search)
        b_highlight = QPushButton(tm.get("btn_highlight"))
        b_highlight.setToolTip(tm.get("tooltip_highlight"))
        b_highlight.clicked.connect(self.action_highlight_text)
        search_btns.addWidget(b_highlight)
        l_search.addLayout(search_btns)
        layout.addWidget(grp_search)
        
        # 주석 관리
        grp_annot = QGroupBox(tm.get("grp_annot"))
        l_annot = QVBoxLayout(grp_annot)
        self.sel_annot = FileSelectorWidget()
        self.sel_annot.pathChanged.connect(self._update_preview)
        l_annot.addWidget(self.sel_annot)
        annot_btns = QHBoxLayout()
        b_list_annot = QPushButton(tm.get("btn_list_annot"))
        b_list_annot.setToolTip(tm.get("tooltip_list_annot"))
        b_list_annot.clicked.connect(self.action_list_annotations)
        annot_btns.addWidget(b_list_annot)
        b_remove_annot = QPushButton(tm.get("btn_remove_annot"))
        b_remove_annot.setObjectName("dangerBtn")
        b_remove_annot.setToolTip(tm.get("tooltip_remove_annot"))
        b_remove_annot.clicked.connect(self.action_remove_annotations)
        annot_btns.addWidget(b_remove_annot)
        l_annot.addLayout(annot_btns)
        layout.addWidget(grp_annot)
        
        # 텍스트 마크업
        grp_markup = QGroupBox(tm.get("grp_markup"))
        l_markup = QVBoxLayout(grp_markup)
        self.sel_markup = FileSelectorWidget()
        self.sel_markup.pathChanged.connect(self._update_preview)
        l_markup.addWidget(self.sel_markup)
        markup_opts = QHBoxLayout()
        markup_opts.addWidget(QLabel(tm.get("lbl_keyword"))) # Reuse keyword label
        self.inp_markup = QLineEdit()
        self.inp_markup.setPlaceholderText(tm.get("ph_markup"))
        markup_opts.addWidget(self.inp_markup)
        markup_opts.addWidget(QLabel(tm.get("lbl_markup_type")))
        self.cmb_markup = QComboBox()
        self.cmb_markup.addItems([tm.get("type_underline"), tm.get("type_strikeout"), tm.get("type_squiggly")])
        markup_opts.addWidget(self.cmb_markup)
        l_markup.addLayout(markup_opts)
        b_markup = QPushButton(tm.get("btn_add_markup"))
        b_markup.clicked.connect(self.action_add_text_markup)
        l_markup.addWidget(b_markup)
        layout.addWidget(grp_markup)
        
        # 배경색 추가
        grp_bg = QGroupBox(tm.get("grp_bg_color"))
        l_bg = QVBoxLayout(grp_bg)
        self.sel_bg = FileSelectorWidget()
        self.sel_bg.pathChanged.connect(self._update_preview)
        l_bg.addWidget(self.sel_bg)
        bg_opts = QHBoxLayout()
        bg_opts.addWidget(QLabel(tm.get("lbl_color")))
        self.cmb_bg_color = QComboBox()
        self.cmb_bg_color.addItems([tm.get("color_cream"), tm.get("color_light_yellow"), tm.get("color_light_blue"), tm.get("color_light_gray"), tm.get("color_white")])
        bg_opts.addWidget(self.cmb_bg_color)
        bg_opts.addStretch()
        l_bg.addLayout(bg_opts)
        b_bg = QPushButton(tm.get("btn_add_bg"))
        b_bg.clicked.connect(self.action_add_background)
        l_bg.addWidget(b_bg)
        layout.addWidget(grp_bg)
        
        # 텍스트 교정 (Redact)
        grp_redact = QGroupBox(tm.get("grp_redact"))
        l_redact = QVBoxLayout(grp_redact)
        self.sel_redact = FileSelectorWidget()
        self.sel_redact.pathChanged.connect(self._update_preview)
        l_redact.addWidget(self.sel_redact)
        redact_opts = QHBoxLayout()
        redact_opts.addWidget(QLabel(tm.get("lbl_redact_text")))
        self.inp_redact = QLineEdit()
        self.inp_redact.setPlaceholderText(tm.get("ph_redact"))
        redact_opts.addWidget(self.inp_redact)
        l_redact.addLayout(redact_opts)
        b_redact = QPushButton(tm.get("btn_redact"))
        b_redact.setObjectName("dangerBtn")
        b_redact.setToolTip(tm.get("tooltip_redact"))
        b_redact.clicked.connect(self.action_redact_text)
        l_redact.addWidget(b_redact)
        layout.addWidget(grp_redact)
        
        # v3.2: 스티키 노트 주석
        grp_sticky = QGroupBox(tm.get("grp_sticky"))
        l_sticky = QVBoxLayout(grp_sticky)
        self.sel_sticky = FileSelectorWidget()
        self.sel_sticky.pathChanged.connect(self._update_preview)
        l_sticky.addWidget(self.sel_sticky)
        sticky_opts1 = QHBoxLayout()
        sticky_opts1.addWidget(QLabel(tm.get("lbl_pos_x")))
        self.spn_sticky_x = QSpinBox()
        self.spn_sticky_x.setRange(0, 999)
        self.spn_sticky_x.setValue(100)
        sticky_opts1.addWidget(self.spn_sticky_x)
        sticky_opts1.addWidget(QLabel(tm.get("lbl_pos_y")))
        self.spn_sticky_y = QSpinBox()
        self.spn_sticky_y.setRange(0, 999)
        self.spn_sticky_y.setValue(100)
        sticky_opts1.addWidget(self.spn_sticky_y)
        sticky_opts1.addWidget(QLabel(tm.get("tab_page") + ":"))
        self.spn_sticky_page = QSpinBox()
        self.spn_sticky_page.setRange(1, 9999)
        self.spn_sticky_page.setValue(1)
        sticky_opts1.addWidget(self.spn_sticky_page)
        sticky_opts1.addStretch()
        l_sticky.addLayout(sticky_opts1)
        sticky_opts2 = QHBoxLayout()
        sticky_opts2.addWidget(QLabel(tm.get("lbl_icon")))
        self.cmb_sticky_icon = QComboBox()
        self.cmb_sticky_icon.addItems(["Note", "Comment", "Key", "Help", "Insert", "Paragraph"])
        sticky_opts2.addWidget(self.cmb_sticky_icon)
        sticky_opts2.addStretch()
        l_sticky.addLayout(sticky_opts2)
        l_sticky.addWidget(QLabel(tm.get("lbl_content")))
        self.txt_sticky_content = QLineEdit()
        self.txt_sticky_content.setPlaceholderText(tm.get("ph_sticky"))
        l_sticky.addWidget(self.txt_sticky_content)
        b_sticky = QPushButton(tm.get("btn_add_sticky"))
        b_sticky.clicked.connect(self.action_add_sticky_note)
        l_sticky.addWidget(b_sticky)
        layout.addWidget(grp_sticky)
        
        # v3.2: 프리핸드 드로잉
        grp_ink = QGroupBox(tm.get("grp_ink"))
        l_ink = QVBoxLayout(grp_ink)
        self.sel_ink = FileSelectorWidget()
        self.sel_ink.pathChanged.connect(self._update_preview)
        l_ink.addWidget(self.sel_ink)
        ink_opts1 = QHBoxLayout()
        ink_opts1.addWidget(QLabel(tm.get("tab_page") + ":"))
        self.spn_ink_page = QSpinBox()
        self.spn_ink_page.setRange(1, 9999)
        self.spn_ink_page.setValue(1)
        ink_opts1.addWidget(self.spn_ink_page)
        ink_opts1.addWidget(QLabel(tm.get("lbl_line_width")))
        self.spn_ink_width = QSpinBox()
        self.spn_ink_width.setRange(1, 10)
        self.spn_ink_width.setValue(2)
        ink_opts1.addWidget(self.spn_ink_width)
        ink_opts1.addWidget(QLabel(tm.get("lbl_color")))
        self.cmb_ink_color = QComboBox()
        self.cmb_ink_color.addItems([tm.get("color_blue_ink"), tm.get("color_red_ink"), tm.get("color_black_ink"), tm.get("color_green_ink")])
        ink_opts1.addWidget(self.cmb_ink_color)
        ink_opts1.addStretch()
        l_ink.addLayout(ink_opts1)
        ink_guide = QLabel(tm.get("lbl_ink_guide"))
        ink_guide.setObjectName("desc")
        l_ink.addWidget(ink_guide)
        self.txt_ink_points = QLineEdit()
        self.txt_ink_points.setPlaceholderText(tm.get("ph_ink"))
        l_ink.addWidget(self.txt_ink_points)
        b_ink = QPushButton(tm.get("btn_add_ink"))
        b_ink.clicked.connect(self.action_add_ink_annotation)
        l_ink.addWidget(b_ink)
        layout.addWidget(grp_ink)
        
        layout.addStretch()
        scroll.setWidget(content)
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        return widget
    
    def _create_misc_subtab(self):
        """기타 서브탭: 양식, 비교, 서명, 복호화, 첨부파일"""
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        
        # 양식 작성
        grp_form = QGroupBox(tm.get("grp_form"))
        l_form = QVBoxLayout(grp_form)
        self.sel_form = FileSelectorWidget()
        self.sel_form.pathChanged.connect(self._update_preview)
        l_form.addWidget(self.sel_form)
        self.form_fields_list = QListWidget()
        self.form_fields_list.setMaximumHeight(80)
        self.form_fields_list.setToolTip(tm.get("tooltip_form_list"))
        self.form_fields_list.itemDoubleClicked.connect(self._edit_form_field)
        l_form.addWidget(self.form_fields_list)
        btn_form_layout = QHBoxLayout()
        b_detect = QPushButton(tm.get("btn_detect_fields"))
        b_detect.clicked.connect(self.action_detect_fields)
        btn_form_layout.addWidget(b_detect)
        b_fill = QPushButton(tm.get("btn_save_form"))
        b_fill.setObjectName("actionBtn")
        b_fill.clicked.connect(self.action_fill_form)
        btn_form_layout.addWidget(b_fill)
        l_form.addLayout(btn_form_layout)
        layout.addWidget(grp_form)
        
        # PDF 비교
        grp_compare = QGroupBox(tm.get("grp_compare"))
        l_compare = QVBoxLayout(grp_compare)
        l_compare.addWidget(QLabel(tm.get("lbl_file_1")))
        self.sel_compare1 = FileSelectorWidget()
        l_compare.addWidget(self.sel_compare1)
        l_compare.addWidget(QLabel(tm.get("lbl_file_2")))
        self.sel_compare2 = FileSelectorWidget()
        l_compare.addWidget(self.sel_compare2)
        b_compare = QPushButton(tm.get("btn_compare_pdf"))
        b_compare.setToolTip(tm.get("tooltip_compare"))
        b_compare.clicked.connect(self.action_compare_pdfs)
        l_compare.addWidget(b_compare)
        layout.addWidget(grp_compare)
        
        # 전자 서명
        grp_sig = QGroupBox(tm.get("grp_sig"))
        l_sig = QVBoxLayout(grp_sig)
        l_sig.addWidget(QLabel(tm.get("lbl_target_pdf")))
        self.sel_sig_pdf = FileSelectorWidget()
        self.sel_sig_pdf.pathChanged.connect(self._update_preview)
        l_sig.addWidget(self.sel_sig_pdf)
        l_sig.addWidget(QLabel(tm.get("lbl_sig_img")))
        self.sel_sig_img = FileSelectorWidget()
        self.sel_sig_img.drop_zone.accept_extensions = ['.png', '.jpg', '.jpeg']
        l_sig.addWidget(self.sel_sig_img)
        sig_opts = QHBoxLayout()
        sig_opts.addWidget(QLabel(tm.get("lbl_position")))
        self.cmb_sig_pos = QComboBox()
        self.cmb_sig_pos.addItems([tm.get("pos_bottom_right"), tm.get("pos_bottom_left"), tm.get("pos_top_right"), tm.get("pos_top_left")])
        sig_opts.addWidget(self.cmb_sig_pos)
        sig_opts.addWidget(QLabel(tm.get("tab_page") + ":"))
        self.spn_sig_page = QSpinBox()
        self.spn_sig_page.setRange(-1, 9999)
        self.spn_sig_page.setValue(-1)
        self.spn_sig_page.setToolTip(tm.get("tooltip_sig_pos"))
        sig_opts.addWidget(self.spn_sig_page)
        sig_opts.addStretch()
        l_sig.addLayout(sig_opts)
        b_sig = QPushButton(tm.get("btn_insert_sig"))
        b_sig.clicked.connect(self.action_insert_signature)
        l_sig.addWidget(b_sig)
        layout.addWidget(grp_sig)
        
        # PDF 복호화
        grp_decrypt = QGroupBox(tm.get("grp_decrypt"))
        l_decrypt = QVBoxLayout(grp_decrypt)
        self.sel_decrypt = FileSelectorWidget()
        self.sel_decrypt.pathChanged.connect(self._update_preview)
        l_decrypt.addWidget(self.sel_decrypt)
        decrypt_opts = QHBoxLayout()
        decrypt_opts.addWidget(QLabel(tm.get("lbl_pw")))
        self.inp_decrypt_pw = QLineEdit()
        self.inp_decrypt_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_decrypt_pw.setPlaceholderText(tm.get("ph_decrypt_pw"))
        decrypt_opts.addWidget(self.inp_decrypt_pw)
        l_decrypt.addLayout(decrypt_opts)
        b_decrypt = QPushButton(tm.get("btn_decrypt"))
        b_decrypt.setToolTip(tm.get("tooltip_decrypt"))
        b_decrypt.clicked.connect(self.action_decrypt_pdf)
        l_decrypt.addWidget(b_decrypt)
        layout.addWidget(grp_decrypt)
        
        # 첨부 파일 관리
        grp_attach = QGroupBox(tm.get("grp_attach"))
        l_attach = QVBoxLayout(grp_attach)
        self.sel_attach = FileSelectorWidget()
        self.sel_attach.pathChanged.connect(self._update_preview)
        l_attach.addWidget(self.sel_attach)
        attach_btns = QHBoxLayout()
        b_list_attach = QPushButton(tm.get("btn_list_attach"))
        b_list_attach.clicked.connect(self.action_list_attachments)
        attach_btns.addWidget(b_list_attach)
        b_add_attach = QPushButton(tm.get("btn_add_attach"))
        b_add_attach.clicked.connect(self.action_add_attachment)
        attach_btns.addWidget(b_add_attach)
        b_extract_attach = QPushButton(tm.get("btn_extract_attach"))
        b_extract_attach.clicked.connect(self.action_extract_attachments)
        attach_btns.addWidget(b_extract_attach)
        l_attach.addLayout(attach_btns)
        layout.addWidget(grp_attach)
        
        layout.addStretch()
        scroll.setWidget(content)
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        return widget
    
    def action_split_adv(self):
        path = self.sel_split_adv.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        out_dir = QFileDialog.getExistingDirectory(self, "저장 폴더 선택")
        if out_dir:
            mode = 'each' if self.cmb_split_mode.currentIndex() == 0 else 'range'
            self.run_worker("split_by_pages", file_path=path, output_dir=out_dir, 
                          split_mode=mode, ranges=self.inp_split_range.text())
    
    def action_page_numbers(self):
        path = self.sel_pn.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "numbered.pdf", "PDF (*.pdf)")
        if s:
            pos = 'bottom' if self.cmb_pn_pos.currentIndex() == 0 else 'top'
            self.run_worker("add_page_numbers", file_path=path, output_path=s,
                          position=pos, format=self.cmb_pn_format.currentText())
    
    def action_stamp(self):
        path = self.sel_stamp.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "stamped.pdf", "PDF (*.pdf)")
        if s:
            pos_map = {"우상단": "top-right", "좌상단": "top-left", 
                      "우하단": "bottom-right", "좌하단": "bottom-left"}
            pos = pos_map.get(self.cmb_stamp_pos.currentText(), "top-right")
            self.run_worker("add_stamp", file_path=path, output_path=s,
                          stamp_text=self.cmb_stamp.currentText(), position=pos)
    
    def action_crop(self):
        path = self.sel_crop.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "cropped.pdf", "PDF (*.pdf)")
        if s:
            margins = {
                'left': self.spn_crop_좌.value(),
                'top': self.spn_crop_상.value(),
                'right': self.spn_crop_우.value(),
                'bottom': self.spn_crop_하.value()
            }
            self.run_worker("crop_pdf", file_path=path, output_path=s, margins=margins)
    
    def action_blank_page(self):
        path = self.sel_blank.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "with_blank.pdf", "PDF (*.pdf)")
        if s:
            pos = self.spn_blank_pos.value() - 1  # 0-indexed
            self.run_worker("insert_blank_page", file_path=path, output_path=s, position=pos)

    # ===================== 신규 기능 액션 =====================
    
    def action_extract_links(self):
        """PDF 링크 추출"""
        path = self.sel_links.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "links.txt", "텍스트 (*.txt)")
        if s:
            self.run_worker("extract_links", file_path=path, output_path=s)
    
    def action_detect_fields(self):
        """PDF 양식 필드 감지"""
        path = self.sel_form.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        
        try:
            import fitz
            doc = fitz.open(path)
            self.form_fields_list.clear()
            self._form_field_data = {}  # 필드 데이터 저장
            
            for page_num, page in enumerate(doc):
                widgets = page.widgets()
                if widgets:
                    for widget in widgets:
                        name = widget.field_name or f"field_{self.form_fields_list.count()}"
                        value = widget.field_value or ""
                        item = QListWidgetItem(f"📋 {name}: {value}")
                        item.setData(Qt.ItemDataRole.UserRole, name)
                        item.setToolTip(f"타입: {widget.field_type_string}, 페이지: {page_num + 1}")
                        self.form_fields_list.addItem(item)
                        self._form_field_data[name] = value
            
            doc.close()
            
            count = self.form_fields_list.count()
            if count == 0:
                QMessageBox.information(self, "양식", "양식 필드가 없습니다.")
            else:
                toast = ToastWidget(f"{count}개 필드 감지됨", toast_type='success', duration=2000)
                toast.show_toast(self)
        except Exception as e:
            QMessageBox.warning(self, "오류", f"필드 감지 실패: {e}")
    
    def _edit_form_field(self, item):
        """양식 필드 값 수정"""
        name = item.data(Qt.ItemDataRole.UserRole)
        current_value = self._form_field_data.get(name, "")
        
        new_value, ok = QInputDialog.getText(self, "필드 수정", f"'{name}' 값:", 
                                             QLineEdit.EchoMode.Normal, current_value)
        if ok:
            self._form_field_data[name] = new_value
            item.setText(f"📋 {name}: {new_value}")
    
    def action_fill_form(self):
        """양식 작성 저장"""
        path = self.sel_form.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        if not hasattr(self, '_form_field_data') or not self._form_field_data:
            return QMessageBox.warning(self, "알림", "먼저 필드를 감지하세요.")
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "filled_form.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("fill_form", file_path=path, output_path=s, 
                          field_values=self._form_field_data)
    
    def action_compare_pdfs(self):
        """PDF 비교"""
        path1 = self.sel_compare1.get_path()
        path2 = self.sel_compare2.get_path()
        
        if not path1 or not path2:
            return QMessageBox.warning(self, "알림", "두 개의 PDF 파일을 모두 선택하세요.")
        
        s, _ = QFileDialog.getSaveFileName(self, "비교 결과 저장", "comparison.txt", "텍스트 (*.txt)")
        if s:
            self.run_worker("compare_pdfs", file_path1=path1, file_path2=path2, output_path=s)

    # ===================== v2.8 신규 기능 액션 =====================
    
    def action_pdf_info(self):
        """PDF 정보 추출"""
        path = self.sel_info.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "pdf_info.txt", "텍스트 (*.txt)")
        if s:
            self.run_worker("get_pdf_info", file_path=path, output_path=s)
    
    def action_duplicate_page(self):
        """페이지 복제"""
        path = self.sel_dup.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "duplicated.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("duplicate_page", file_path=path, output_path=s,
                          page_num=self.spn_dup_page.value() - 1,  # 0-indexed
                          count=self.spn_dup_count.value())
    
    def action_reverse_pages(self):
        """페이지 역순 정렬"""
        path = self.sel_rev.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "reversed.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("reverse_pages", file_path=path, output_path=s)
    
    def action_resize_pages(self):
        """페이지 크기 변경"""
        path = self.sel_resize.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "resized.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("resize_pages", file_path=path, output_path=s,
                          target_size=self.cmb_resize.currentText())
    
    def action_extract_images(self):
        """이미지 추출"""
        path = self.sel_extract.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        out_dir = QFileDialog.getExistingDirectory(self, "저장 폴더 선택")
        if out_dir:
            self.run_worker("extract_images", file_path=path, output_dir=out_dir)
    
    def action_insert_signature(self):
        """전자 서명 삽입"""
        pdf_path = self.sel_sig_pdf.get_path()
        sig_path = self.sel_sig_img.get_path()
        
        if not pdf_path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        if not sig_path:
            return QMessageBox.warning(self, "알림", "서명 이미지를 선택하세요.")
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "signed.pdf", "PDF (*.pdf)")
        if s:
            pos_map = {"우하단": "bottom_right", "좌하단": "bottom_left", 
                       "우상단": "top_right", "좌상단": "top_left"}
            self.run_worker("insert_signature", file_path=pdf_path, output_path=s,
                          signature_path=sig_path,
                          page_num=self.spn_sig_page.value(),
                          position=pos_map.get(self.cmb_sig_pos.currentText(), "bottom_right"))

    # ===================== v2.9 신규 기능 액션 =====================
    
    def action_get_bookmarks(self):
        """북마크 추출"""
        path = self.sel_bm.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "bookmarks.txt", "텍스트 (*.txt)")
        if s:
            self.run_worker("get_bookmarks", file_path=path, output_path=s)
    
    def action_search_text(self):
        """텍스트 검색"""
        path = self.sel_search.get_path()
        term = self.inp_search.text().strip()
        
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        if not term:
            return QMessageBox.warning(self, "알림", "검색어를 입력하세요.")
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "search_results.txt", "텍스트 (*.txt)")
        if s:
            self.run_worker("search_text", file_path=path, output_path=s, search_term=term)
    
    def action_highlight_text(self):
        """텍스트 하이라이트"""
        path = self.sel_search.get_path()
        term = self.inp_search.text().strip()
        
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        if not term:
            return QMessageBox.warning(self, "알림", "검색어를 입력하세요.")
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "highlighted.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("highlight_text", file_path=path, output_path=s, search_term=term)

    # ===================== v3.0 신규 기능 액션 =====================
    
    def action_extract_tables(self):
        """테이블 추출"""
        path = self.sel_table.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "tables.csv", "CSV (*.csv)")
        if s:
            self.run_worker("extract_tables", file_path=path, output_path=s)
    
    def action_decrypt_pdf(self):
        """PDF 복호화"""
        path = self.sel_decrypt.get_path()
        password = self.inp_decrypt_pw.text()
        
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        if not password:
            return QMessageBox.warning(self, "알림", "비밀번호를 입력하세요.")
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "decrypted.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("decrypt_pdf", file_path=path, output_path=s, password=password)
    
    def action_list_annotations(self):
        """주석 목록 추출"""
        path = self.sel_annot.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "annotations.txt", "텍스트 (*.txt)")
        if s:
            self.run_worker("list_annotations", file_path=path, output_path=s)
    
    def action_remove_annotations(self):
        """모든 주석 삭제"""
        path = self.sel_annot.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        
        reply = QMessageBox.question(self, "확인", 
                                    "모든 주석을 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "no_annotations.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("remove_annotations", file_path=path, output_path=s)
    
    def action_list_attachments(self):
        """첨부 파일 목록"""
        path = self.sel_attach.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        
        try:
            import fitz
            doc = fitz.open(path)
            count = doc.embfile_count()
            
            if count == 0:
                QMessageBox.information(self, "첨부 파일", "첨부 파일이 없습니다.")
            else:
                attachments = []
                for i in range(count):
                    info = doc.embfile_info(i)
                    attachments.append(f"• {info.get('name', 'Unknown')} ({info.get('size', 0)} bytes)")
                
                QMessageBox.information(self, "첨부 파일 목록", 
                                       f"{count}개 첨부 파일:\n\n" + "\n".join(attachments))
            doc.close()
        except Exception as e:
            QMessageBox.warning(self, "오류", f"첨부 파일 목록 오류: {e}")
    
    def action_add_attachment(self):
        """파일 첨부"""
        pdf_path = self.sel_attach.get_path()
        if not pdf_path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        
        attach_path, _ = QFileDialog.getOpenFileName(self, "첨부할 파일 선택", "", "모든 파일 (*.*)")
        if not attach_path:
            return
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "with_attachment.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("add_attachment", file_path=pdf_path, output_path=s, attach_path=attach_path)
    
    def action_extract_attachments(self):
        """첨부 파일 추출"""
        path = self.sel_attach.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        
        out_dir = QFileDialog.getExistingDirectory(self, "첨부 파일 저장 폴더 선택")
        if out_dir:
            self.run_worker("extract_attachments", file_path=path, output_dir=out_dir)
    
    def action_redact_text(self):
        """텍스트 교정 (영구 삭제)"""
        path = self.sel_redact.get_path()
        term = self.inp_redact.text().strip()
        
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        if not term:
            return QMessageBox.warning(self, "알림", "삭제할 텍스트를 입력하세요.")
        
        reply = QMessageBox.warning(self, "경고", 
                                   f"'{term}' 텍스트가 영구적으로 삭제됩니다.\n이 작업은 되돌릴 수 없습니다.\n\n계속하시겠습니까?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "redacted.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("redact_text", file_path=path, output_path=s, search_term=term)
    
    def action_extract_markdown(self):
        """Markdown 추출"""
        path = self.sel_md.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "output.md", "Markdown (*.md)")
        if s:
            self.run_worker("extract_markdown", file_path=path, output_path=s)
    
    def action_add_text_markup(self):
        """텍스트 마크업 추가"""
        path = self.sel_markup.get_path()
        term = self.inp_markup.text().strip()
        
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        if not term:
            return QMessageBox.warning(self, "알림", "마크업할 텍스트를 입력하세요.")
        
        markup_map = {"밑줄": "underline", "취소선": "strikeout", "물결선": "squiggly"}
        markup_type = markup_map.get(self.cmb_markup.currentText(), "underline")
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "marked_up.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("add_text_markup", file_path=path, output_path=s, 
                          search_term=term, markup_type=markup_type)
    
    def action_add_background(self):
        """배경색 추가"""
        path = self.sel_bg.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        
        color_map = {
            "크림색": [1, 1, 0.9],
            "연노랑": [1, 1, 0.8],
            "연파랑": [0.9, 0.95, 1],
            "연회색": [0.95, 0.95, 0.95],
            "흰색": [1, 1, 1]
        }
        color = color_map.get(self.cmb_bg_color.currentText(), [1, 1, 0.9])
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "with_background.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("add_background", file_path=path, output_path=s, color=color)

    # ===================== v3.2 신규 기능 액션 =====================
    
    def action_add_sticky_note(self):
        """스티키 노트 추가"""
        path = self.sel_sticky.get_path()
        content = self.txt_sticky_content.text().strip()
        
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        if not content:
            return QMessageBox.warning(self, "알림", "메모 내용을 입력하세요.")
        
        x = self.spn_sticky_x.value()
        y = self.spn_sticky_y.value()
        page_num = self.spn_sticky_page.value() - 1
        icon = self.cmb_sticky_icon.currentText()
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "with_note.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("add_sticky_note", file_path=path, output_path=s,
                          page_num=page_num, x=x, y=y, content=content, icon=icon)
    
    def action_add_ink_annotation(self):
        """프리핸드 드로잉 추가"""
        path = self.sel_ink.get_path()
        points_text = self.txt_ink_points.text().strip()
        
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        if not points_text:
            return QMessageBox.warning(self, "알림", "좌표를 입력하세요. 형식: x1,y1;x2,y2;x3,y3")
        
        # 좌표 파싱
        try:
            points = []
            for pt in points_text.split(";"):
                coords = pt.strip().split(",")
                if len(coords) >= 2:
                    points.append([float(coords[0]), float(coords[1])])
            
            if len(points) < 2:
                return QMessageBox.warning(self, "알림", "최소 2개 이상의 좌표가 필요합니다.")
        except Exception as e:
            return QMessageBox.warning(self, "오류", f"좌표 형식 오류: {e}")
        
        page_num = self.spn_ink_page.value() - 1
        width = self.spn_ink_width.value()
        
        color_map = {"파랑": (0, 0, 1), "빨강": (1, 0, 0), "검정": (0, 0, 0), "녹색": (0, 0.5, 0)}
        color = color_map.get(self.cmb_ink_color.currentText(), (0, 0, 1))
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "with_drawing.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("add_ink_annotation", file_path=path, output_path=s,
                          page_num=page_num, points=points, color=color, width=width)
    
    # ===================== Tab 8: AI 요약 (v4.0) =====================
    def setup_ai_tab(self):
        """AI 요약 탭 설정"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # AI 요약 섹션
        grp_summary = QGroupBox(tm.get("grp_ai_summary"))
        l_summary = QVBoxLayout(grp_summary)
        
        # ⚠️ AI 패키지 미설치 경고 배너
        if not AI_AVAILABLE:
            ai_warning = QLabel(tm.get("msg_ai_unavailable"))
            ai_warning.setStyleSheet("""
                QLabel {
                    background-color: #3a1a1a;
                    color: #ff6b6b;
                    padding: 15px;
                    border: 2px solid #ff6b6b;
                    border-radius: 8px;
                    font-size: 12px;
                }
            """)
            ai_warning.setWordWrap(True)
            ai_warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l_summary.addWidget(ai_warning)
            l_summary.addWidget(QLabel(""))  # 간격
        
        # API 키 설정
        api_layout = QHBoxLayout()
        api_layout.addWidget(QLabel(tm.get("lbl_api_key")))
        self.txt_api_key = QLineEdit()
        self.txt_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_api_key.setPlaceholderText(tm.get("ph_api_key"))
        self.txt_api_key.setEnabled(AI_AVAILABLE)  # 오프라인 시 비활성화
        saved_key = self.settings.get("gemini_api_key", "")
        if saved_key:
            self.txt_api_key.setText(saved_key)
        api_layout.addWidget(self.txt_api_key)
        
        btn_save_key = QPushButton(tm.get("btn_save_key"))
        btn_save_key.setFixedWidth(70)
        btn_save_key.setEnabled(AI_AVAILABLE)
        btn_save_key.clicked.connect(self._save_api_key)
        api_layout.addWidget(btn_save_key)
        
        l_summary.addLayout(api_layout)
        
        # API 키 안내
        api_hint = QLabel(tm.get("msg_api_hint"))
        api_hint.setOpenExternalLinks(True)
        api_hint.setStyleSheet("color: #888; font-size: 11px;")
        l_summary.addWidget(api_hint)
        
        l_summary.addWidget(QLabel(""))  # 간격
        
        # PDF 파일 선택
        step1 = QLabel(tm.get("step_ai_1"))
        step1.setObjectName("stepLabel")
        l_summary.addWidget(step1)
        
        self.sel_ai_pdf = FileSelectorWidget(tm.get("lbl_ai_file"), ['.pdf'])
        self.sel_ai_pdf.pathChanged.connect(self._update_preview)
        l_summary.addWidget(self.sel_ai_pdf)
        
        # 요약 옵션
        step2 = QLabel(tm.get("step_ai_2"))
        step2.setObjectName("stepLabel")
        l_summary.addWidget(step2)
        
        opt_layout = QHBoxLayout()
        opt_layout.addWidget(QLabel(tm.get("lbl_ai_style")))
        self.cmb_summary_style = QComboBox()
        self.cmb_summary_style.addItems([tm.get("style_concise"), tm.get("style_detailed"), tm.get("style_bullet")])
        self.cmb_summary_style.setEnabled(AI_AVAILABLE)
        opt_layout.addWidget(self.cmb_summary_style)
        
        opt_layout.addWidget(QLabel(tm.get("lbl_ai_lang")))
        self.cmb_summary_lang = QComboBox()
        self.cmb_summary_lang.addItems([tm.get("lang_ko"), tm.get("lang_en")])
        self.cmb_summary_lang.setEnabled(AI_AVAILABLE)
        opt_layout.addWidget(self.cmb_summary_lang)
        
        opt_layout.addWidget(QLabel(tm.get("lbl_max_pages")))
        self.spn_max_pages = QSpinBox()
        self.spn_max_pages.setRange(0, 100)
        self.spn_max_pages.setValue(0)
        self.spn_max_pages.setToolTip(tm.get("tooltip_max_pages"))
        self.spn_max_pages.setEnabled(AI_AVAILABLE)
        opt_layout.addWidget(self.spn_max_pages)
        
        opt_layout.addStretch()
        l_summary.addLayout(opt_layout)
        
        # 요약 실행 버튼
        self.btn_ai_summarize = QPushButton(tm.get("btn_ai_run"))
        self.btn_ai_summarize.setObjectName("actionBtn")
        self.btn_ai_summarize.setEnabled(AI_AVAILABLE)
        self.btn_ai_summarize.clicked.connect(self.action_ai_summarize)
        if not AI_AVAILABLE:
            self.btn_ai_summarize.setToolTip(tm.get("tooltip_ai_unavailable"))
        l_summary.addWidget(self.btn_ai_summarize)
        
        # 요약 결과 표시
        step3 = QLabel(tm.get("step_ai_3"))
        step3.setObjectName("stepLabel")
        l_summary.addWidget(step3)
        
        self.txt_summary_result = QTextEdit()
        self.txt_summary_result.setPlaceholderText(tm.get("ph_ai_result") if AI_AVAILABLE else tm.get("msg_ai_disabled"))
        self.txt_summary_result.setMinimumHeight(200)
        self.txt_summary_result.setReadOnly(True)
        l_summary.addWidget(self.txt_summary_result)
        
        # 저장 버튼
        btn_save_summary = QPushButton(tm.get("btn_save_summary"))
        btn_save_summary.setObjectName("secondaryBtn")
        btn_save_summary.clicked.connect(self._save_summary_result)
        l_summary.addWidget(btn_save_summary)
        
        content_layout.addWidget(grp_summary)
        
        # 페이지 썸네일 그리드 섹션
        grp_thumb = QGroupBox(tm.get("grp_thumb"))
        l_thumb = QVBoxLayout(grp_thumb)
        
        thumb_desc = QLabel(tm.get("desc_thumb"))
        thumb_desc.setObjectName("desc")
        l_thumb.addWidget(thumb_desc)
        
        self.sel_thumb_pdf = FileSelectorWidget(tm.get("lbl_thumb_file"), ['.pdf'])
        l_thumb.addWidget(self.sel_thumb_pdf)
        
        btn_show_grid = QPushButton(tm.get("btn_show_grid"))
        btn_show_grid.setObjectName("actionBtn")
        btn_show_grid.clicked.connect(self._show_thumbnail_grid)
        l_thumb.addWidget(btn_show_grid)
        
        content_layout.addWidget(grp_thumb)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.tabs.addTab(tab, f"🤖 {tm.get('tab_ai')}")
    
    def _save_api_key(self):
        """API 키 저장"""
        key = self.txt_api_key.text().strip()
        self.settings["gemini_api_key"] = key
        save_settings(self.settings)
        toast = ToastWidget(tm.get("msg_key_saved"), toast_type='success', duration=2000)
        toast.show_toast(self)
    
    def _save_summary_result(self):
        """요약 결과 저장"""
        text = self.txt_summary_result.toPlainText()
        if not text:
            return QMessageBox.warning(self, tm.get("info"), tm.get("msg_no_summary"))
        
        s, _ = QFileDialog.getSaveFileName(self, tm.get("dlg_save_summary"), "summary.txt", "텍스트 (*.txt)")
        if s:
            with open(s, 'w', encoding='utf-8') as f:
                f.write(text)
            toast = ToastWidget(tm.get("msg_summary_saved"), toast_type='success', duration=2000)
            toast.show_toast(self)
    
    def action_ai_summarize(self):
        """AI 요약 실행"""
        # 오프라인 안전 체크
        if not AI_AVAILABLE:
            return QMessageBox.critical(self, tm.get("error"), 
                tm.get("msg_ai_unavailable"))
        
        path = self.sel_ai_pdf.get_path()
        api_key = self.txt_api_key.text().strip()
        
        if not path:
            return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
        if not api_key:
            return QMessageBox.warning(self, tm.get("info"), tm.get("msg_enter_key"))
        
        style_map = {"간결하게": "concise", "상세하게": "detailed", "불릿 포인트": "bullet"}
        style = style_map.get(self.cmb_summary_style.currentText(), "concise")
        
        lang = "ko" if self.cmb_summary_lang.currentText() == "한국어" else "en"
        
        max_pages = self.spn_max_pages.value()
        if max_pages == 0:
            max_pages = None
        
        
        self.txt_summary_result.clear()
        self.txt_summary_result.setPlaceholderText(tm.get("msg_ai_working"))
        
        # Worker 실행 (결과는 finished 시그널에서 처리)
        self._ai_worker_mode = True
        self.run_worker("ai_summarize", 
                       file_path=path, 
                       api_key=api_key,
                       language=lang,
                       style=style,
                       max_pages=max_pages)
    
    
    # action_convert_to_word 함수 제거됨 (v4.2)
    
    def _show_thumbnail_grid(self):
        """썸네일 그리드 다이얼로그 표시"""
        path = self.sel_thumb_pdf.get_path()
        if not path:
            return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
        
        # 다이얼로그 생성
        dialog = QDialog(self)
        dialog.setWindowTitle(tm.get("title_thumb_grid").format(os.path.basename(path)))
        dialog.resize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        # 썸네일 그리드 위젯
        thumbnail_grid = ThumbnailGridWidget()
        thumbnail_grid.pageSelected.connect(lambda pg: self._on_grid_page_selected(pg, dialog))
        layout.addWidget(thumbnail_grid)
        
        # 닫기 버튼
        btn_close = QPushButton(tm.get("close"))
        btn_close.clicked.connect(dialog.accept)
        layout.addWidget(btn_close)
        
        # PDF 로드
        thumbnail_grid.load_pdf(path)
        
        dialog.exec()
    
    def _on_grid_page_selected(self, page_index: int, dialog: QDialog):
        """그리드에서 페이지 선택 시"""
        self._current_preview_page = page_index
        self._render_preview_page()
        self.status_label.setText(tm.get("status_page_sel").format(page_index + 1))

    # ===================== 설정 저장 및 리소스 정리 =====================
    
    def _save_settings_on_exit(self):
        """종료 시 설정 저장"""
        try:
            # 창 위치/크기 저장
            self.settings['window_geometry'] = self.saveGeometry().data().hex()
            
            # 현재 테마 저장
            # (이미 settings에 저장되어 있음)
            
            save_settings(self.settings)
            logger.info("Settings saved on exit")
        except Exception as e:
            logger.error(f"Failed to save settings on exit: {e}")
    
    def _add_to_recent_files(self, file_path: str):
        """최근 파일 목록에 추가"""
        if not file_path or not os.path.exists(file_path):
            return
        
        recent = self.settings.get('recent_files', [])
        
        # 이미 있으면 제거 후 맨 앞에 추가 (최신으로 이동)
        if file_path in recent:
            recent.remove(file_path)
        recent.insert(0, file_path)
        
        # 최대 10개 유지
        self.settings['recent_files'] = recent[:10]
    
    def closeEvent(self, event):
        """앱 종료 시 리소스 정리 및 설정 저장"""
        logger.info("Application closing...")
        
        # 1. 실행 중인 Worker 정리
        if self.worker and self.worker.isRunning():
            logger.info("Stopping running worker...")
            self.worker.cancel()
            if not self.worker.wait(3000):  # 3초 대기
                logger.warning("Worker did not stop in time, forcing termination")
                self.worker.terminate()
                self.worker.wait(1000)
        
        # 2. 미리보기 문서 리소스 정리
        if hasattr(self, '_current_preview_doc') and self._current_preview_doc:
            try:
                self._current_preview_doc.close()
                logger.debug("Preview document closed")
            except Exception as e:
                logger.warning(f"Error closing preview doc: {e}")
        
        # 3. Undo 백업 폴더 정리 (선택적)
        # 임시 폴더이므로 시스템이 자동 정리
        
        # 4. 설정 저장
        self._save_settings_on_exit()
        
        logger.info("Application cleanup complete")
        super().closeEvent(event)
