import logging
import os
import subprocess

from PyQt6.QtCore import QByteArray, Qt, QUrl
from PyQt6.QtGui import QAction, QDesktopServices, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
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

def _install_wheel_filters(self):
    """모든 입력 위젯에 휠 이벤트 필터 설치"""
    for widget in self.findChildren(QSpinBox):
        widget.installEventFilter(self._wheel_filter)
    for widget in self.findChildren(QComboBox):
        widget.installEventFilter(self._wheel_filter)

def _setup_shortcuts(self):
    """Keyboard shortcuts"""
    self._app_shortcuts = [
        QShortcut(QKeySequence("Ctrl+O"), self, self._shortcut_open_file),
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close),
        QShortcut(QKeySequence("Ctrl+T"), self, self._toggle_theme),
        QShortcut(QKeySequence("Ctrl+Z"), self, self._undo_action),
        QShortcut(QKeySequence("Ctrl+Y"), self, self._redo_action),
        QShortcut(QKeySequence("Ctrl+F"), self, self._focus_preview_search),
        QShortcut(QKeySequence("F1"), self, self._show_help),
        QShortcut(QKeySequence("F11"), self, self._toggle_preview_focus_mode),
        QShortcut(QKeySequence("Ctrl+F11"), self, self._enter_preview_fullscreen),
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self._on_preview_focus_escape),
        # Ctrl+1~9: 탭 순서대로 이동
        *(
            QShortcut(QKeySequence(f"Ctrl+{number}"), self, lambda index=number - 1: self.tabs.setCurrentIndex(index))
            for number in range(1, 10)
        ),
    ]

def _relax_spinbox_min_widths(self):
    """Fluent 숫자 입력칸의 기본 최소 폭이 넓어 한 줄 배치가 패널을 넘친다. 줄어들 수 있게 한다."""
    for widget in self.findChildren(QDoubleSpinBox):
        widget.setMinimumWidth(124)
    for widget in self.findChildren(QSpinBox):
        widget.setMinimumWidth(110)


def _shortcut_open_file(self):
    """Open file via shortcut"""
    f, _ = QFileDialog.getOpenFileName(self, tm.get("open"), "", "PDF (*.pdf)")
    if f:
        self._update_preview(f)
        self.status_label.setText(tm.get("status_file_opened", os.path.basename(f)))
