import sys
import os
import json
import fitz
import subprocess
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
    QPushButton, QLabel, QFileDialog, QMessageBox, QComboBox, 
    QSpinBox, QSplitter, QGroupBox, QScrollArea, QApplication, 
    QInputDialog, QLineEdit, QProgressBar, QListWidget, QListWidgetItem,
    QAbstractItemView, QFrame, QFormLayout, QMenuBar, QMenu
)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QIcon, QAction, QPixmap, QImage, QKeySequence, QShortcut

from ..core.settings import load_settings, save_settings
from ..core.worker import WorkerThread
from .widgets import FileSelectorWidget, FileListWidget, ImageListWidget, DropZoneWidget, WheelEventFilter, ToastWidget
from .styles import DARK_STYLESHEET, LIGHT_STYLESHEET, ThemeColors

APP_NAME = "PDF Master"
VERSION = "3.0"

class PDFMasterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.worker = None
        self._last_output_path = None  # 마지막 저장 경로 추적
        self._current_preview_page = 0
        self._current_preview_doc = None
        
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
        self.setup_reorder_tab()  # NEW: 페이지 순서 변경
        self.setup_edit_sec_tab()
        self.setup_batch_tab()    # NEW: 일괄 처리
        self.setup_advanced_tab()  # NEW: 고급 기능
        
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
        
        # 모든 QSpinBox, QComboBox에 휠 필터 설치
        self._install_wheel_filters()
        
        # v2.7: 윈도우 위치 복원
        self._restore_window_geometry()
    
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
        QShortcut(QKeySequence("Ctrl+T"), self, self._toggle_theme)  # v2.7: 테마 토글
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
    
    def _restore_window_geometry(self):
        """윈도우 위치/크기 복원"""
        geo = self.settings.get("window_geometry")
        if geo:
            self.setGeometry(geo.get("x", 100), geo.get("y", 100), 
                           geo.get("width", 1200), geo.get("height", 850))
    
    def closeEvent(self, event):
        """앱 종료 시 윈도우 위치 저장"""
        self.settings["window_geometry"] = {
            "x": self.x(), "y": self.y(),
            "width": self.width(), "height": self.height()
        }
        save_settings(self.settings)
        event.accept()
    
    def _create_menu_bar(self):
        """메뉴 바 생성"""
        menubar = self.menuBar()
        
        # 파일 메뉴
        file_menu = menubar.addMenu("📁 파일")
        
        open_action = QAction("📂 열기 (Ctrl+O)", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._shortcut_open_file)
        file_menu.addAction(open_action)
        
        # 최근 파일 서브메뉴
        self.recent_menu_bar = file_menu.addMenu("📋 최근 파일")
        self._update_recent_menu_bar()
        
        file_menu.addSeparator()
        
        exit_action = QAction("🚪 종료 (Ctrl+Q)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 도움말 메뉴
        help_menu = menubar.addMenu("❓ 도움말")
        
        shortcuts_action = QAction("⌨️ 단축키 안내", self)
        shortcuts_action.triggered.connect(self._show_shortcuts)
        help_menu.addAction(shortcuts_action)
        
        help_menu.addSeparator()
        
        about_action = QAction("ℹ️ 정보", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _update_recent_menu_bar(self):
        """최근 파일 메뉴 업데이트"""
        self.recent_menu_bar.clear()
        recent = self.settings.get("recent_files", [])
        if not recent:
            action = self.recent_menu_bar.addAction("(최근 파일 없음)")
            action.setEnabled(False)
        else:
            for path in recent[:10]:
                if os.path.exists(path):
                    action = self.recent_menu_bar.addAction(f"📄 {os.path.basename(path)}")
                    action.triggered.connect(lambda checked, p=path: self._update_preview(p))
    
    def _show_shortcuts(self):
        """단축키 안내 대화상자"""
        shortcuts_text = f"""📑 {APP_NAME} v{VERSION} - 키보드 단축키

🔹 Ctrl + O  :  파일 열기
🔹 Ctrl + Q  :  프로그램 종료
🔹 Ctrl + 1~4  :  탭 전환 (1:병합, 2:변환, 3:페이지, 4:순서)
🔹 F1  :  도움말 표시"""
        QMessageBox.information(self, "키보드 단축키", shortcuts_text)
    
    def _show_about(self):
        """정보 대화상자"""
        about_text = f"""📑 {APP_NAME} v{VERSION}

모든 PDF 작업을 한 곳에서 처리하는 올인원 PDF 도구입니다.
강력한 기능과 직관적인 UI를 제공합니다.

🛠️ 기술 스택:
  • Python 3.9+
  • PyQt6 (UI Framework)
  • PyMuPDF (PDF Processing)

📧 Made with ❤️
© 2025-2026"""
        QMessageBox.about(self, f"{APP_NAME} 정보", about_text)
        
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
        theme_text = "DARK" if self.settings.get("theme") == "dark" else "LIGHT"
        self.btn_theme = QPushButton(theme_text)
        self.btn_theme.setMinimumSize(70, 32)
        self.btn_theme.setStyleSheet("QPushButton { background-color: #e94560; color: white; border: none; border-radius: 4px; font-weight: bold; font-size: 11px; padding: 5px 10px; } QPushButton:hover { background-color: #ff5a7a; }")
        self.btn_theme.clicked.connect(self._toggle_theme)
        header.addWidget(self.btn_theme)
        
        # Help button
        btn_help = QPushButton("HELP")
        btn_help.setMinimumSize(60, 32)
        btn_help.setStyleSheet("QPushButton { background-color: #e94560; color: white; border: none; border-radius: 4px; font-weight: bold; font-size: 11px; padding: 5px 10px; } QPushButton:hover { background-color: #ff5a7a; }")
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
        layout.addWidget(self.preview_image, 1)
        
        # 페이지 네비게이션 버튼
        nav_layout = QHBoxLayout()
        self.btn_prev_page = QPushButton("PREV")
        self.btn_prev_page.setMinimumSize(70, 30)
        self.btn_prev_page.setStyleSheet("QPushButton { background-color: #e94560; color: white; border: none; border-radius: 4px; font-weight: bold; font-size: 11px; } QPushButton:hover { background-color: #ff5a7a; }")
        self.btn_prev_page.clicked.connect(self._prev_preview_page)
        nav_layout.addWidget(self.btn_prev_page)
        
        self.page_counter = QLabel("1 / 1")
        self.page_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_counter.setStyleSheet("font-weight: bold; min-width: 60px; color: #eaeaea;")
        nav_layout.addWidget(self.page_counter)
        
        self.btn_next_page = QPushButton("NEXT")
        self.btn_next_page.setMinimumSize(70, 30)
        self.btn_next_page.setStyleSheet("QPushButton { background-color: #e94560; color: white; border: none; border-radius: 4px; font-weight: bold; font-size: 11px; } QPushButton:hover { background-color: #ff5a7a; }")
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
            doc.close()
        except Exception as e:
            print(f"Preview render error: {e}")
    
    def _on_list_item_clicked(self, item):
        """리스트 아이템 클릭 시 미리보기 업데이트"""
        path = item.data(Qt.ItemDataRole.UserRole)
        self._update_preview(path)
    
    
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
        
        # 미리보기 패널 테마 동기화
        if hasattr(self, 'preview_image'):
            if is_dark:
                self.preview_image.setStyleSheet("background: #0f0f23; border-radius: 8px; border: 1px solid #333;")
                self.preview_label.setStyleSheet("color: #888; padding: 10px; font-size: 12px;")
                self.page_counter.setStyleSheet("font-weight: bold; min-width: 60px; color: #eaeaea;")
            else:
                self.preview_image.setStyleSheet("background: #f0f0f0; border-radius: 8px; border: 1px solid #ddd;")
                self.preview_label.setStyleSheet("color: #666; padding: 10px; font-size: 12px; background: transparent;")
                self.page_counter.setStyleSheet("font-weight: bold; min-width: 60px; color: #333;")
    
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
        
        # Toast 알림 표시
        toast = ToastWidget("작업이 완료되었습니다!", toast_type='success', duration=4000)
        toast.show_toast(self)
        
        QMessageBox.information(self, "완료", msg)
        QTimer.singleShot(3000, lambda: self.progress_bar.setValue(0))
    
    def on_fail(self, msg):
        self.set_ui_busy(False)
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
        self.merge_list.itemClicked.connect(self._on_list_item_clicked)
        layout.addWidget(self.merge_list)
        
        # v2.7: 파일 개수 표시
        merge_info_layout = QHBoxLayout()
        self.merge_count_label = QLabel("📁 0개 파일")
        self.merge_count_label.setStyleSheet("color: #888; font-size: 12px;")
        merge_info_layout.addWidget(self.merge_count_label)
        merge_info_layout.addStretch()
        layout.addLayout(merge_info_layout)
        
        # 파일 추가/삭제 시 카운트 업데이트
        self.merge_list.model().rowsInserted.connect(self._update_merge_count)
        self.merge_list.model().rowsRemoved.connect(self._update_merge_count)
        
        btn_box = QHBoxLayout()
        b_add = QPushButton("➕ 파일 추가")
        b_add.setObjectName("secondaryBtn")
        b_add.clicked.connect(self._merge_add_files)
        
        b_del = QPushButton("➖ 선택 삭제")
        b_del.setObjectName("secondaryBtn")
        b_del.clicked.connect(lambda: [self.merge_list.takeItem(self.merge_list.row(i)) for i in self.merge_list.selectedItems()])
        
        b_clr = QPushButton("🧹 전체 삭제")
        b_clr.setObjectName("secondaryBtn")
        b_clr.clicked.connect(self._confirm_clear_merge)  # v2.7: 확인 다이얼로그
        
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
    
    def _update_merge_count(self):
        """병합 탭 파일 개수 업데이트"""
        count = self.merge_list.count()
        self.merge_count_label.setText(f"📁 {count}개 파일")
    
    def _confirm_clear_merge(self):
        """전체 삭제 확인 다이얼로그"""
        if self.merge_list.count() == 0:
            return
        reply = QMessageBox.question(self, "확인", 
                                    f"{self.merge_list.count()}개 파일을 모두 삭제하시겠습니까?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.merge_list.clear()
    
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
        grp_img = QGroupBox("🖼️ PDF → 이미지 변환 (다중 파일)")
        l_img = QVBoxLayout(grp_img)
        step = QLabel("1️⃣ PDF 파일들을 드래그하거나 추가하세요")
        step.setObjectName("stepLabel")
        l_img.addWidget(step)
        self.img_conv_list = FileListWidget()
        self.img_conv_list.setMaximumHeight(100)
        l_img.addWidget(self.img_conv_list)
        self.img_conv_list.itemClicked.connect(self._on_list_item_clicked)
        self.img_conv_list.fileAdded.connect(self._update_preview)
        
        # 버튼 레이아웃
        btn_layout_img = QHBoxLayout()
        btn_add_pdf = QPushButton("➕ PDF 추가")
        btn_add_pdf.clicked.connect(self._add_pdf_for_img)
        
        btn_clear_img = QPushButton("🗑️ 전체 삭제")
        btn_clear_img.setToolTip("목록 비우기")
        btn_clear_img.setStyleSheet("""
            QPushButton { background-color: #3e272b; color: #ff6b6b; border: 1px solid #5c3a3a; padding: 10px; }
            QPushButton:hover { background-color: #5c3a3a; color: #ff8787; }
        """)
        btn_clear_img.clicked.connect(self.img_conv_list.clear)
        
        btn_layout_img.addWidget(btn_add_pdf)
        btn_layout_img.addWidget(btn_clear_img)
        l_img.addLayout(btn_layout_img)
        
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
        grp_txt = QGroupBox("📝 텍스트 추출 (다중 파일)")
        l_txt = QVBoxLayout(grp_txt)
        step_txt = QLabel("PDF 파일들을 드래그하거나 추가하세요")
        step_txt.setObjectName("stepLabel")
        l_txt.addWidget(step_txt)
        self.txt_conv_list = FileListWidget()
        self.txt_conv_list.setMaximumHeight(100)
        l_txt.addWidget(self.txt_conv_list)
        self.txt_conv_list.itemClicked.connect(self._on_list_item_clicked)
        self.txt_conv_list.fileAdded.connect(self._update_preview)
        
        # 버튼 레이아웃
        btn_layout_txt = QHBoxLayout()
        btn_add_txt = QPushButton("➕ PDF 추가")
        btn_add_txt.clicked.connect(self._add_pdf_for_txt)
        
        btn_clear_txt = QPushButton("🗑️ 전체 삭제")
        btn_clear_txt.setToolTip("목록 비우기")
        btn_clear_txt.setStyleSheet("""
            QPushButton { background-color: #3e272b; color: #ff6b6b; border: 1px solid #5c3a3a; padding: 10px; }
            QPushButton:hover { background-color: #5c3a3a; color: #ff8787; }
        """)
        btn_clear_txt.clicked.connect(self.txt_conv_list.clear)
        
        btn_layout_txt.addWidget(btn_add_txt)
        btn_layout_txt.addWidget(btn_clear_txt)
        l_txt.addLayout(btn_layout_txt)
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
            QMessageBox.warning(self, "인쇄", "인쇄할 파일이 없습니다.")
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
                toast = ToastWidget("인쇄 명령이 전송되었습니다", toast_type='success', duration=2000)
                toast.show_toast(self)
        except Exception as e:
            QMessageBox.warning(self, "인쇄 오류", f"인쇄 중 오류: {e}")
    
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
        self.sel_del.pathChanged.connect(self._update_preview)
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
        self.sel_meta.pathChanged.connect(self._update_preview)
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
        self.sel_wm.pathChanged.connect(self._update_preview)
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
        self.sel_sec.pathChanged.connect(self._update_preview)
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
        
        guide = QLabel("🔀 PDF 페이지 순서를 변경합니다")
        guide.setObjectName("desc")
        layout.addWidget(guide)
        
        step1 = QLabel("1️⃣ PDF 파일 선택")
        step1.setObjectName("stepLabel")
        layout.addWidget(step1)
        
        self.sel_reorder = FileSelectorWidget()
        self.sel_reorder.pathChanged.connect(self._load_pages_for_reorder)
        layout.addWidget(self.sel_reorder)
        self.sel_reorder.pathChanged.connect(self._update_preview)
        
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
        self.batch_list.itemClicked.connect(self._on_list_item_clicked)
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
        sub_tabs.addTab(self._create_edit_subtab(), "✏️ 편집")
        # 2. 추출 서브탭
        sub_tabs.addTab(self._create_extract_subtab(), "📊 추출")
        # 3. 마크업 서브탭
        sub_tabs.addTab(self._create_markup_subtab(), "📝 마크업")
        # 4. 기타 서브탭
        sub_tabs.addTab(self._create_misc_subtab(), "📎 기타")
        
        layout.addWidget(sub_tabs)
        self.tabs.addTab(tab, "🔧 고급")
    
    def _create_edit_subtab(self):
        """편집 서브탭: 분할, 페이지 번호, 스탬프, 크롭, 빈 페이지, 크기 변경, 복제, 역순"""
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        
        # PDF 분할
        grp_split = QGroupBox("✂️ PDF 분할")
        l_split = QVBoxLayout(grp_split)
        self.sel_split_adv = FileSelectorWidget()
        self.sel_split_adv.pathChanged.connect(self._update_preview)
        l_split.addWidget(self.sel_split_adv)
        opt_split = QHBoxLayout()
        opt_split.addWidget(QLabel("분할 모드:"))
        self.cmb_split_mode = QComboBox()
        self.cmb_split_mode.addItems(["각 페이지별", "범위 지정"])
        opt_split.addWidget(self.cmb_split_mode)
        self.inp_split_range = QLineEdit()
        self.inp_split_range.setPlaceholderText("예: 1-3, 5-7, 10-12")
        opt_split.addWidget(self.inp_split_range)
        l_split.addLayout(opt_split)
        b_split = QPushButton("✂️ PDF 분할 실행")
        b_split.setToolTip("PDF를 여러 파일로 분할합니다")
        b_split.clicked.connect(self.action_split_adv)
        l_split.addWidget(b_split)
        layout.addWidget(grp_split)
        
        # 페이지 번호
        grp_pn = QGroupBox("🔢 페이지 번호 삽입")
        l_pn = QVBoxLayout(grp_pn)
        self.sel_pn = FileSelectorWidget()
        self.sel_pn.pathChanged.connect(self._update_preview)
        l_pn.addWidget(self.sel_pn)
        guide_pn = QLabel("📌 형식: {n}=현재페이지, {total}=전체페이지")
        guide_pn.setObjectName("desc")
        l_pn.addWidget(guide_pn)
        opt_pn = QHBoxLayout()
        opt_pn.addWidget(QLabel("위치:"))
        self.cmb_pn_pos = QComboBox()
        self.cmb_pn_pos.addItems(["하단 중앙", "상단 중앙", "하단 좌측", "하단 우측", "상단 좌측", "상단 우측"])
        self.cmb_pn_pos.setToolTip("페이지 번호 위치 선택")
        opt_pn.addWidget(self.cmb_pn_pos)
        opt_pn.addWidget(QLabel("형식:"))
        self.cmb_pn_format = QComboBox()
        self.cmb_pn_format.addItems(["{n} / {total}", "Page {n} of {total}", "- {n} -", "{n}", "페이지 {n}"])
        self.cmb_pn_format.setEditable(True)
        opt_pn.addWidget(self.cmb_pn_format)
        l_pn.addLayout(opt_pn)
        b_pn = QPushButton("🔢 페이지 번호 삽입")
        b_pn.clicked.connect(self.action_page_numbers)
        l_pn.addWidget(b_pn)
        layout.addWidget(grp_pn)
        
        # 스탬프
        grp_stamp = QGroupBox("📌 스탬프 추가")
        l_stamp = QVBoxLayout(grp_stamp)
        self.sel_stamp = FileSelectorWidget()
        self.sel_stamp.pathChanged.connect(self._update_preview)
        l_stamp.addWidget(self.sel_stamp)
        opt_stamp = QHBoxLayout()
        opt_stamp.addWidget(QLabel("스탬프:"))
        self.cmb_stamp = QComboBox()
        self.cmb_stamp.addItems(["기밀", "승인됨", "초안", "최종본", "복사본 금지"])
        self.cmb_stamp.setEditable(True)
        opt_stamp.addWidget(self.cmb_stamp)
        opt_stamp.addWidget(QLabel("위치:"))
        self.cmb_stamp_pos = QComboBox()
        self.cmb_stamp_pos.addItems(["우상단", "좌상단", "우하단", "좌하단"])
        opt_stamp.addWidget(self.cmb_stamp_pos)
        l_stamp.addLayout(opt_stamp)
        b_stamp = QPushButton("📌 스탬프 추가")
        b_stamp.clicked.connect(self.action_stamp)
        l_stamp.addWidget(b_stamp)
        layout.addWidget(grp_stamp)
        
        # 여백 자르기
        grp_crop = QGroupBox("📐 여백 자르기 (Crop)")
        l_crop = QVBoxLayout(grp_crop)
        self.sel_crop = FileSelectorWidget()
        self.sel_crop.pathChanged.connect(self._update_preview)
        l_crop.addWidget(self.sel_crop)
        opt_crop = QHBoxLayout()
        for side in ["좌", "상", "우", "하"]:
            opt_crop.addWidget(QLabel(f"{side}:"))
            spn = QSpinBox()
            spn.setRange(0, 200)
            spn.setValue(20)
            spn.setToolTip(f"{side}측 자르기 (pt)")
            setattr(self, f"spn_crop_{side}", spn)
            opt_crop.addWidget(spn)
        l_crop.addLayout(opt_crop)
        b_crop = QPushButton("📐 여백 자르기")
        b_crop.clicked.connect(self.action_crop)
        l_crop.addWidget(b_crop)
        layout.addWidget(grp_crop)
        
        # 빈 페이지 삽입
        grp_blank = QGroupBox("📄 빈 페이지 삽입")
        l_blank = QVBoxLayout(grp_blank)
        self.sel_blank = FileSelectorWidget()
        self.sel_blank.pathChanged.connect(self._update_preview)
        l_blank.addWidget(self.sel_blank)
        opt_blank = QHBoxLayout()
        opt_blank.addWidget(QLabel("삽입 위치 (페이지):"))
        self.spn_blank_pos = QSpinBox()
        self.spn_blank_pos.setRange(1, 999)
        self.spn_blank_pos.setValue(1)
        opt_blank.addWidget(self.spn_blank_pos)
        opt_blank.addStretch()
        l_blank.addLayout(opt_blank)
        b_blank = QPushButton("📄 빈 페이지 삽입")
        b_blank.clicked.connect(self.action_blank_page)
        l_blank.addWidget(b_blank)
        layout.addWidget(grp_blank)
        
        # 페이지 크기 변경
        grp_resize = QGroupBox("📐 페이지 크기 변경")
        l_resize = QVBoxLayout(grp_resize)
        self.sel_resize = FileSelectorWidget()
        self.sel_resize.pathChanged.connect(self._update_preview)
        l_resize.addWidget(self.sel_resize)
        resize_opts = QHBoxLayout()
        resize_opts.addWidget(QLabel("크기:"))
        self.cmb_resize = QComboBox()
        self.cmb_resize.addItems(["A4", "A3", "Letter", "Legal"])
        resize_opts.addWidget(self.cmb_resize)
        resize_opts.addStretch()
        l_resize.addLayout(resize_opts)
        b_resize = QPushButton("📐 크기 변경")
        b_resize.clicked.connect(self.action_resize_pages)
        l_resize.addWidget(b_resize)
        layout.addWidget(grp_resize)
        
        # 페이지 복제
        grp_dup = QGroupBox("📋 페이지 복제")
        l_dup = QVBoxLayout(grp_dup)
        self.sel_dup = FileSelectorWidget()
        self.sel_dup.pathChanged.connect(self._update_preview)
        l_dup.addWidget(self.sel_dup)
        dup_opts = QHBoxLayout()
        dup_opts.addWidget(QLabel("페이지:"))
        self.spn_dup_page = QSpinBox()
        self.spn_dup_page.setRange(1, 9999)
        dup_opts.addWidget(self.spn_dup_page)
        dup_opts.addWidget(QLabel("복제 횟수:"))
        self.spn_dup_count = QSpinBox()
        self.spn_dup_count.setRange(1, 100)
        self.spn_dup_count.setValue(1)
        dup_opts.addWidget(self.spn_dup_count)
        dup_opts.addStretch()
        l_dup.addLayout(dup_opts)
        b_dup = QPushButton("📋 페이지 복제")
        b_dup.clicked.connect(self.action_duplicate_page)
        l_dup.addWidget(b_dup)
        layout.addWidget(grp_dup)
        
        # 역순 정렬
        grp_rev = QGroupBox("🔄 페이지 역순 정렬")
        l_rev = QVBoxLayout(grp_rev)
        self.sel_rev = FileSelectorWidget()
        self.sel_rev.pathChanged.connect(self._update_preview)
        l_rev.addWidget(self.sel_rev)
        b_rev = QPushButton("🔄 역순 정렬")
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
        grp_links = QGroupBox("🔗 PDF 링크 추출")
        l_links = QVBoxLayout(grp_links)
        self.sel_links = FileSelectorWidget()
        self.sel_links.pathChanged.connect(self._update_preview)
        l_links.addWidget(self.sel_links)
        b_links = QPushButton("🔗 링크 추출")
        b_links.setToolTip("PDF에 포함된 모든 URL 추출")
        b_links.clicked.connect(self.action_extract_links)
        l_links.addWidget(b_links)
        layout.addWidget(grp_links)
        
        # 이미지 추출
        grp_extract = QGroupBox("🖼️ 이미지 추출")
        l_extract = QVBoxLayout(grp_extract)
        self.sel_extract = FileSelectorWidget()
        self.sel_extract.pathChanged.connect(self._update_preview)
        l_extract.addWidget(self.sel_extract)
        b_extract = QPushButton("🖼️ 이미지 추출")
        b_extract.setToolTip("PDF에 포함된 모든 이미지 추출")
        b_extract.clicked.connect(self.action_extract_images)
        l_extract.addWidget(b_extract)
        layout.addWidget(grp_extract)
        
        # 테이블 추출
        grp_table = QGroupBox("📊 테이블 추출")
        l_table = QVBoxLayout(grp_table)
        self.sel_table = FileSelectorWidget()
        self.sel_table.pathChanged.connect(self._update_preview)
        l_table.addWidget(self.sel_table)
        b_table = QPushButton("📊 테이블 추출 (CSV)")
        b_table.setToolTip("PDF의 표 데이터를 CSV로 추출")
        b_table.clicked.connect(self.action_extract_tables)
        l_table.addWidget(b_table)
        layout.addWidget(grp_table)
        
        # 북마크 추출
        grp_bm = QGroupBox("📑 북마크/목차 추출")
        l_bm = QVBoxLayout(grp_bm)
        self.sel_bm = FileSelectorWidget()
        self.sel_bm.pathChanged.connect(self._update_preview)
        l_bm.addWidget(self.sel_bm)
        b_bm = QPushButton("📑 북마크 추출")
        b_bm.setToolTip("PDF의 목차/북마크 구조 추출")
        b_bm.clicked.connect(self.action_get_bookmarks)
        l_bm.addWidget(b_bm)
        layout.addWidget(grp_bm)
        
        # PDF 정보
        grp_info = QGroupBox("📊 PDF 정보/통계")
        l_info = QVBoxLayout(grp_info)
        self.sel_info = FileSelectorWidget()
        self.sel_info.pathChanged.connect(self._update_preview)
        l_info.addWidget(self.sel_info)
        b_info = QPushButton("📊 정보 추출")
        b_info.setToolTip("페이지 수, 글자 수, 폰트 등 상세 정보")
        b_info.clicked.connect(self.action_pdf_info)
        l_info.addWidget(b_info)
        layout.addWidget(grp_info)
        
        # Markdown 추출
        grp_md = QGroupBox("📝 Markdown 추출")
        l_md = QVBoxLayout(grp_md)
        self.sel_md = FileSelectorWidget()
        self.sel_md.pathChanged.connect(self._update_preview)
        l_md.addWidget(self.sel_md)
        b_md = QPushButton("📝 Markdown으로 추출")
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
        grp_search = QGroupBox("🔍 텍스트 검색 & 하이라이트")
        l_search = QVBoxLayout(grp_search)
        self.sel_search = FileSelectorWidget()
        self.sel_search.pathChanged.connect(self._update_preview)
        l_search.addWidget(self.sel_search)
        search_opts = QHBoxLayout()
        search_opts.addWidget(QLabel("검색어:"))
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("검색할 텍스트 입력...")
        search_opts.addWidget(self.inp_search)
        l_search.addLayout(search_opts)
        search_btns = QHBoxLayout()
        b_search = QPushButton("🔍 검색")
        b_search.setToolTip("텍스트 위치 검색")
        b_search.clicked.connect(self.action_search_text)
        search_btns.addWidget(b_search)
        b_highlight = QPushButton("🖍️ 하이라이트")
        b_highlight.setToolTip("검색어에 노란색 하이라이트 표시")
        b_highlight.clicked.connect(self.action_highlight_text)
        search_btns.addWidget(b_highlight)
        l_search.addLayout(search_btns)
        layout.addWidget(grp_search)
        
        # 주석 관리
        grp_annot = QGroupBox("📝 주석 관리")
        l_annot = QVBoxLayout(grp_annot)
        self.sel_annot = FileSelectorWidget()
        self.sel_annot.pathChanged.connect(self._update_preview)
        l_annot.addWidget(self.sel_annot)
        annot_btns = QHBoxLayout()
        b_list_annot = QPushButton("📋 주석 목록")
        b_list_annot.setToolTip("PDF에 있는 모든 주석 목록 추출")
        b_list_annot.clicked.connect(self.action_list_annotations)
        annot_btns.addWidget(b_list_annot)
        b_remove_annot = QPushButton("🗑️ 주석 삭제")
        b_remove_annot.setObjectName("dangerBtn")
        b_remove_annot.setToolTip("PDF에서 모든 주석 제거")
        b_remove_annot.clicked.connect(self.action_remove_annotations)
        annot_btns.addWidget(b_remove_annot)
        l_annot.addLayout(annot_btns)
        layout.addWidget(grp_annot)
        
        # 텍스트 마크업
        grp_markup = QGroupBox("✒️ 텍스트 마크업")
        l_markup = QVBoxLayout(grp_markup)
        self.sel_markup = FileSelectorWidget()
        self.sel_markup.pathChanged.connect(self._update_preview)
        l_markup.addWidget(self.sel_markup)
        markup_opts = QHBoxLayout()
        markup_opts.addWidget(QLabel("검색어:"))
        self.inp_markup = QLineEdit()
        self.inp_markup.setPlaceholderText("마크업할 텍스트...")
        markup_opts.addWidget(self.inp_markup)
        markup_opts.addWidget(QLabel("유형:"))
        self.cmb_markup = QComboBox()
        self.cmb_markup.addItems(["밑줄", "취소선", "물결선"])
        markup_opts.addWidget(self.cmb_markup)
        l_markup.addLayout(markup_opts)
        b_markup = QPushButton("✒️ 마크업 추가")
        b_markup.clicked.connect(self.action_add_text_markup)
        l_markup.addWidget(b_markup)
        layout.addWidget(grp_markup)
        
        # 배경색 추가
        grp_bg = QGroupBox("🎨 배경색 추가")
        l_bg = QVBoxLayout(grp_bg)
        self.sel_bg = FileSelectorWidget()
        self.sel_bg.pathChanged.connect(self._update_preview)
        l_bg.addWidget(self.sel_bg)
        bg_opts = QHBoxLayout()
        bg_opts.addWidget(QLabel("색상:"))
        self.cmb_bg_color = QComboBox()
        self.cmb_bg_color.addItems(["크림색", "연노랑", "연파랑", "연회색", "흰색"])
        bg_opts.addWidget(self.cmb_bg_color)
        bg_opts.addStretch()
        l_bg.addLayout(bg_opts)
        b_bg = QPushButton("🎨 배경색 추가")
        b_bg.clicked.connect(self.action_add_background)
        l_bg.addWidget(b_bg)
        layout.addWidget(grp_bg)
        
        # 텍스트 교정 (Redact)
        grp_redact = QGroupBox("🖤 텍스트 교정 (영구 삭제)")
        l_redact = QVBoxLayout(grp_redact)
        self.sel_redact = FileSelectorWidget()
        self.sel_redact.pathChanged.connect(self._update_preview)
        l_redact.addWidget(self.sel_redact)
        redact_opts = QHBoxLayout()
        redact_opts.addWidget(QLabel("삭제할 텍스트:"))
        self.inp_redact = QLineEdit()
        self.inp_redact.setPlaceholderText("영구 삭제할 텍스트 입력...")
        redact_opts.addWidget(self.inp_redact)
        l_redact.addLayout(redact_opts)
        b_redact = QPushButton("🖤 텍스트 교정")
        b_redact.setObjectName("dangerBtn")
        b_redact.setToolTip("⚠️ 텍스트를 영구적으로 삭제합니다")
        b_redact.clicked.connect(self.action_redact_text)
        l_redact.addWidget(b_redact)
        layout.addWidget(grp_redact)
        
        # v3.2: 스티키 노트 주석
        grp_sticky = QGroupBox("📌 스티키 노트 (메모 주석)")
        l_sticky = QVBoxLayout(grp_sticky)
        self.sel_sticky = FileSelectorWidget()
        self.sel_sticky.pathChanged.connect(self._update_preview)
        l_sticky.addWidget(self.sel_sticky)
        sticky_opts1 = QHBoxLayout()
        sticky_opts1.addWidget(QLabel("위치 X:"))
        self.spn_sticky_x = QSpinBox()
        self.spn_sticky_x.setRange(0, 999)
        self.spn_sticky_x.setValue(100)
        sticky_opts1.addWidget(self.spn_sticky_x)
        sticky_opts1.addWidget(QLabel("Y:"))
        self.spn_sticky_y = QSpinBox()
        self.spn_sticky_y.setRange(0, 999)
        self.spn_sticky_y.setValue(100)
        sticky_opts1.addWidget(self.spn_sticky_y)
        sticky_opts1.addWidget(QLabel("페이지:"))
        self.spn_sticky_page = QSpinBox()
        self.spn_sticky_page.setRange(1, 9999)
        self.spn_sticky_page.setValue(1)
        sticky_opts1.addWidget(self.spn_sticky_page)
        sticky_opts1.addStretch()
        l_sticky.addLayout(sticky_opts1)
        sticky_opts2 = QHBoxLayout()
        sticky_opts2.addWidget(QLabel("아이콘:"))
        self.cmb_sticky_icon = QComboBox()
        self.cmb_sticky_icon.addItems(["Note", "Comment", "Key", "Help", "Insert", "Paragraph"])
        sticky_opts2.addWidget(self.cmb_sticky_icon)
        sticky_opts2.addStretch()
        l_sticky.addLayout(sticky_opts2)
        l_sticky.addWidget(QLabel("메모 내용:"))
        self.txt_sticky_content = QLineEdit()
        self.txt_sticky_content.setPlaceholderText("스티키 노트에 표시할 메모 내용...")
        l_sticky.addWidget(self.txt_sticky_content)
        b_sticky = QPushButton("📌 스티키 노트 추가")
        b_sticky.clicked.connect(self.action_add_sticky_note)
        l_sticky.addWidget(b_sticky)
        layout.addWidget(grp_sticky)
        
        # v3.2: 프리핸드 드로잉
        grp_ink = QGroupBox("✏️ 프리핸드 드로잉")
        l_ink = QVBoxLayout(grp_ink)
        self.sel_ink = FileSelectorWidget()
        self.sel_ink.pathChanged.connect(self._update_preview)
        l_ink.addWidget(self.sel_ink)
        ink_opts1 = QHBoxLayout()
        ink_opts1.addWidget(QLabel("페이지:"))
        self.spn_ink_page = QSpinBox()
        self.spn_ink_page.setRange(1, 9999)
        self.spn_ink_page.setValue(1)
        ink_opts1.addWidget(self.spn_ink_page)
        ink_opts1.addWidget(QLabel("선 두께:"))
        self.spn_ink_width = QSpinBox()
        self.spn_ink_width.setRange(1, 10)
        self.spn_ink_width.setValue(2)
        ink_opts1.addWidget(self.spn_ink_width)
        ink_opts1.addWidget(QLabel("색상:"))
        self.cmb_ink_color = QComboBox()
        self.cmb_ink_color.addItems(["파랑", "빨강", "검정", "녹색"])
        ink_opts1.addWidget(self.cmb_ink_color)
        ink_opts1.addStretch()
        l_ink.addLayout(ink_opts1)
        ink_guide = QLabel("📝 좌표 형식: x1,y1;x2,y2;x3,y3 (예: 100,100;150,120;200,100)")
        ink_guide.setObjectName("desc")
        l_ink.addWidget(ink_guide)
        self.txt_ink_points = QLineEdit()
        self.txt_ink_points.setPlaceholderText("좌표 입력: 100,100;150,120;200,100")
        l_ink.addWidget(self.txt_ink_points)
        b_ink = QPushButton("✏️ 프리핸드 드로잉 추가")
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
        grp_form = QGroupBox("📝 PDF 양식 작성")
        l_form = QVBoxLayout(grp_form)
        self.sel_form = FileSelectorWidget()
        self.sel_form.pathChanged.connect(self._update_preview)
        l_form.addWidget(self.sel_form)
        self.form_fields_list = QListWidget()
        self.form_fields_list.setMaximumHeight(80)
        self.form_fields_list.setToolTip("양식 필드 목록 (수정하려면 더블클릭)")
        self.form_fields_list.itemDoubleClicked.connect(self._edit_form_field)
        l_form.addWidget(self.form_fields_list)
        btn_form_layout = QHBoxLayout()
        b_detect = QPushButton("🔍 필드 감지")
        b_detect.clicked.connect(self.action_detect_fields)
        btn_form_layout.addWidget(b_detect)
        b_fill = QPushButton("💾 양식 저장")
        b_fill.setObjectName("actionBtn")
        b_fill.clicked.connect(self.action_fill_form)
        btn_form_layout.addWidget(b_fill)
        l_form.addLayout(btn_form_layout)
        layout.addWidget(grp_form)
        
        # PDF 비교
        grp_compare = QGroupBox("🔍 PDF 비교")
        l_compare = QVBoxLayout(grp_compare)
        l_compare.addWidget(QLabel("📄 파일 1:"))
        self.sel_compare1 = FileSelectorWidget()
        l_compare.addWidget(self.sel_compare1)
        l_compare.addWidget(QLabel("📄 파일 2:"))
        self.sel_compare2 = FileSelectorWidget()
        l_compare.addWidget(self.sel_compare2)
        b_compare = QPushButton("🔍 PDF 비교")
        b_compare.setToolTip("두 PDF의 텍스트 차이 분석")
        b_compare.clicked.connect(self.action_compare_pdfs)
        l_compare.addWidget(b_compare)
        layout.addWidget(grp_compare)
        
        # 전자 서명
        grp_sig = QGroupBox("✍️ 전자 서명 삽입")
        l_sig = QVBoxLayout(grp_sig)
        l_sig.addWidget(QLabel("PDF 파일:"))
        self.sel_sig_pdf = FileSelectorWidget()
        self.sel_sig_pdf.pathChanged.connect(self._update_preview)
        l_sig.addWidget(self.sel_sig_pdf)
        l_sig.addWidget(QLabel("서명 이미지 (PNG/JPG):"))
        self.sel_sig_img = FileSelectorWidget()
        self.sel_sig_img.drop_zone.accept_extensions = ['.png', '.jpg', '.jpeg']
        l_sig.addWidget(self.sel_sig_img)
        sig_opts = QHBoxLayout()
        sig_opts.addWidget(QLabel("위치:"))
        self.cmb_sig_pos = QComboBox()
        self.cmb_sig_pos.addItems(["우하단", "좌하단", "우상단", "좌상단"])
        sig_opts.addWidget(self.cmb_sig_pos)
        sig_opts.addWidget(QLabel("페이지:"))
        self.spn_sig_page = QSpinBox()
        self.spn_sig_page.setRange(-1, 9999)
        self.spn_sig_page.setValue(-1)
        self.spn_sig_page.setToolTip("-1 = 마지막 페이지")
        sig_opts.addWidget(self.spn_sig_page)
        sig_opts.addStretch()
        l_sig.addLayout(sig_opts)
        b_sig = QPushButton("✍️ 서명 삽입")
        b_sig.clicked.connect(self.action_insert_signature)
        l_sig.addWidget(b_sig)
        layout.addWidget(grp_sig)
        
        # PDF 복호화
        grp_decrypt = QGroupBox("🔓 PDF 복호화")
        l_decrypt = QVBoxLayout(grp_decrypt)
        self.sel_decrypt = FileSelectorWidget()
        self.sel_decrypt.pathChanged.connect(self._update_preview)
        l_decrypt.addWidget(self.sel_decrypt)
        decrypt_opts = QHBoxLayout()
        decrypt_opts.addWidget(QLabel("비밀번호:"))
        self.inp_decrypt_pw = QLineEdit()
        self.inp_decrypt_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_decrypt_pw.setPlaceholderText("암호화된 PDF의 비밀번호")
        decrypt_opts.addWidget(self.inp_decrypt_pw)
        l_decrypt.addLayout(decrypt_opts)
        b_decrypt = QPushButton("🔓 복호화")
        b_decrypt.setToolTip("암호 해제된 PDF로 저장")
        b_decrypt.clicked.connect(self.action_decrypt_pdf)
        l_decrypt.addWidget(b_decrypt)
        layout.addWidget(grp_decrypt)
        
        # 첨부 파일 관리
        grp_attach = QGroupBox("📎 첨부 파일 관리")
        l_attach = QVBoxLayout(grp_attach)
        self.sel_attach = FileSelectorWidget()
        self.sel_attach.pathChanged.connect(self._update_preview)
        l_attach.addWidget(self.sel_attach)
        attach_btns = QHBoxLayout()
        b_list_attach = QPushButton("📋 첨부 목록")
        b_list_attach.clicked.connect(self.action_list_attachments)
        attach_btns.addWidget(b_list_attach)
        b_add_attach = QPushButton("➕ 파일 첨부")
        b_add_attach.clicked.connect(self.action_add_attachment)
        attach_btns.addWidget(b_add_attach)
        b_extract_attach = QPushButton("📤 첨부 추출")
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
