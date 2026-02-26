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
from ..thumbnail_grid import ThumbnailGridWidget
from ..widgets import DropZoneWidget, EmptyStateWidget, FileSelectorWidget
from ..zoomable_preview import ZoomablePreviewWidget

logger = logging.getLogger(__name__)

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
