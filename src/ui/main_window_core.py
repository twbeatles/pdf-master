import logging
import os
import subprocess
import sys

from PyQt6.QtCore import QByteArray
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
)

from ..core.i18n import tm
from ..core.settings import save_settings
from .main_window_config import APP_NAME, VERSION
from .styles import DARK_STYLESHEET, LIGHT_STYLESHEET
from .thumbnail_grid import ThumbnailGridWidget
from .widgets import DropZoneWidget, EmptyStateWidget, FileSelectorWidget
from .zoomable_preview import ZoomablePreviewWidget

logger = logging.getLogger(__name__)


class MainWindowCoreMixin:

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

    def _shortcut_open_file(self):
        """Open file via shortcut"""
        f, _ = QFileDialog.getOpenFileName(self, tm.get("open"), "", "PDF (*.pdf)")
        if f:
            self._update_preview(f)
            self.status_label.setText(f"📄 {os.path.basename(f)} loaded")

    def _open_last_folder(self):
        """Open folder containing last output"""
        if self._last_output_path and os.path.exists(self._last_output_path):
            if os.path.isdir(self._last_output_path):
                folder = self._last_output_path
            else:
                folder = os.path.dirname(self._last_output_path)
            if sys.platform == 'win32':
                if os.path.isdir(self._last_output_path):
                    subprocess.Popen(['explorer', folder])
                else:
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
