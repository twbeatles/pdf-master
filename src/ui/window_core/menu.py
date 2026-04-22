import logging
import os
import subprocess

from PyQt6.QtCore import QByteArray, QUrl
from PyQt6.QtGui import QAction, QDesktopServices, QKeySequence, QShortcut
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

from ...core.i18n import tm
from ...core.settings import save_settings
from ..main_window_config import APP_NAME, VERSION
from ..styles import DARK_STYLESHEET, LIGHT_STYLESHEET
from ..widgets import DropZoneWidget, EmptyStateWidget, FileSelectorWidget
from ..zoomable_preview import ZoomablePreviewWidget

logger = logging.getLogger(__name__)

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
{tm.get('shortcut_preview_search')}
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

def _show_help(self):
    QMessageBox.information(self, tm.get("help_title"), f"""📑 {APP_NAME} v{VERSION}

{tm.get("help_intro")}

{tm.get("help_features")}""")
