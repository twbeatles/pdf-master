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
from ..fluent_widgets import PushButton

from ...core.i18n import tm
from ...core.settings import save_settings
from ..main_window_config import APP_NAME, VERSION
from ..styles import DARK_STYLESHEET, LIGHT_STYLESHEET, NATIVE_DARK_STYLESHEET, NATIVE_LIGHT_STYLESHEET
from ..thumbnail_grid import ThumbnailGridWidget
from ..widgets import DropZoneWidget, EmptyStateWidget, FileSelectorWidget
from ..zoomable_preview import ZoomablePreviewWidget

logger = logging.getLogger(__name__)

def _create_header(self):
    header = QHBoxLayout()
    header.setSpacing(15)

    # 컴팩트한 타이틀 - 테마 통일 (파란색)
    title = QLabel(APP_NAME)
    title.setObjectName("header")
    header.addWidget(title)

    ver_label = QLabel(f"v{VERSION}")
    ver_label.setStyleSheet("color: #666; font-size: 11px;")
    header.addWidget(ver_label)

    header.addStretch()

    # Theme toggle - objectName으로 스타일 적용
    current_theme = self.settings.get("theme")
    theme_text = {"dark": tm.get("theme_dark"), "light": tm.get("theme_light")}.get(current_theme, tm.get("theme_auto"))
    # But wait, existing logic: theme_text = "DARK" if self.settings.get("theme") == "dark" else "LIGHT"
    # The button usually shows the CURRENT theme or the TARGET theme?
    # Usually a toggle button shows the current state or what will happen.
    # Original code: "DARK" if dark else "LIGHT". This suggests it shows the current state.

    self.btn_theme = PushButton(theme_text)
    # (Fluent button: legacy accent objectName removed)
    self.btn_theme.setMinimumSize(70, 32)
    self.btn_theme.clicked.connect(self._toggle_theme)
    header.addWidget(self.btn_theme)

    # Help button - objectName으로 스타일 적용
    btn_help = PushButton(tm.get("help")) # "도움말" or "Help"
    # (Fluent button: legacy accent objectName removed)
    btn_help.setMinimumSize(60, 32)
    btn_help.clicked.connect(self._show_help)
    header.addWidget(btn_help)

    return header

def _toggle_theme(self):
    current = self.settings.get("theme", "dark")
    new_theme = {"dark": "light", "light": "auto"}.get(current, "dark")
    self.settings["theme"] = new_theme
    save_settings(self.settings)
    self._apply_theme()
    self.btn_theme.setText({"dark": tm.get("theme_dark"), "light": tm.get("theme_light")}.get(new_theme, tm.get("theme_auto")))

def _apply_theme(self):
    theme = self.settings.get("theme", "dark")
    from ..fluent_theme import resolve_is_dark

    is_dark = resolve_is_dark(theme)
    app = QApplication.instance()
    if isinstance(app, QApplication):
        from ..fluent_widgets import is_fluent_widgets_available

        if is_fluent_widgets_available():
            app.setStyleSheet(NATIVE_DARK_STYLESHEET if is_dark else NATIVE_LIGHT_STYLESHEET)
        else:
            app.setStyleSheet(DARK_STYLESHEET if is_dark else LIGHT_STYLESHEET)
    try:  # Fluent 브리지: settings 테마를 qfluentwidgets에 반영 (미설치면 no-op)
        from ..fluent_theme import sync_fluent_theme

        sync_fluent_theme("dark" if is_dark else "light")
    except Exception:
        logger.debug("Fluent sync skipped", exc_info=True)

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
        self.preview_image.set_theme(is_dark)
        if is_dark:
            self.preview_label.setStyleSheet("color: #94a3b8; padding: 12px; font-size: 13px; background: transparent;")
        else:
            self.preview_label.setStyleSheet("color: #64748b; padding: 12px; font-size: 13px; background: transparent;")
