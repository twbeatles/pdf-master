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
