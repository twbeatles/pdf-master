import logging
import os
import subprocess

from PyQt6.QtCore import QByteArray, QUrl
from PyQt6.QtGui import QAction, QColor, QDesktopServices, QKeySequence, QPalette, QShortcut
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

# 스타일시트가 닿지 않는 기본 Qt 위젯(스크롤 영역·라벨·체크박스 등)이 OS 색 구성 대신
# 앱 테마를 따르도록 하는 팔레트 값. theme/native.py 의 앱 셸 색과 맞춘다.
_THEME_PALETTES = {
    True: {
        "window": "#0a0e14", "base": "#141922", "alt_base": "#1c2432", "text": "#f0f4f8",
        "button": "#1c2432", "placeholder": "#6b7280", "disabled": "#6b7280",
        "tooltip": "#1c2432", "tooltip_text": "#f0f4f8",
    },
    False: {
        "window": "#f8fafc", "base": "#ffffff", "alt_base": "#f1f5f9", "text": "#1e293b",
        "button": "#ffffff", "placeholder": "#94a3b8", "disabled": "#94a3b8",
        "tooltip": "#ffffff", "tooltip_text": "#1e293b",
    },
}


def build_theme_palette(is_dark: bool) -> QPalette:
    colors = _THEME_PALETTES[bool(is_dark)]
    palette = QPalette()
    role = QPalette.ColorRole
    for color_role, key in (
        (role.Window, "window"),
        (role.Base, "base"),
        (role.AlternateBase, "alt_base"),
        (role.WindowText, "text"),
        (role.Text, "text"),
        (role.Button, "button"),
        (role.ButtonText, "text"),
        (role.PlaceholderText, "placeholder"),
        (role.ToolTipBase, "tooltip"),
        (role.ToolTipText, "tooltip_text"),
        # QPdfView 등 기본 위젯이 빈 영역을 칠할 때 쓰는 음영 계열
        (role.Dark, "alt_base"),
        (role.Mid, "alt_base"),
    ):
        palette.setColor(color_role, QColor(colors[key]))
    palette.setColor(role.Highlight, QColor("#4f8cff"))
    palette.setColor(role.HighlightedText, QColor("#ffffff"))
    palette.setColor(role.Link, QColor("#4f8cff"))
    for color_role in (role.WindowText, role.Text, role.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, color_role, QColor(colors["disabled"]))
    return palette


def _create_header(self):
    header = QHBoxLayout()
    header.setSpacing(15)

    # 컴팩트한 타이틀 - 테마 통일 (파란색)
    title = QLabel(APP_NAME)
    title.setObjectName("header")
    header.addWidget(title)

    ver_label = QLabel(f"v{VERSION}")
    ver_label.setObjectName("desc")
    header.addWidget(ver_label)

    header.addStretch()

    # Theme toggle - objectName으로 스타일 적용
    # 버튼은 현재 적용 중인 테마를 보여 주고, 누르면 다음 테마로 넘어간다.
    self.btn_theme = PushButton(_theme_button_text(self.settings.get("theme")))
    self.btn_theme.setMinimumSize(70, 32)
    self.btn_theme.setToolTip(tm.get("tooltip_theme_toggle"))
    self.btn_theme.clicked.connect(self._toggle_theme)
    header.addWidget(self.btn_theme)

    return header


def _theme_button_text(theme) -> str:
    return {"dark": tm.get("theme_dark"), "light": tm.get("theme_light")}.get(theme, tm.get("theme_auto"))

def _toggle_theme(self):
    current = self.settings.get("theme", "dark")
    new_theme = {"dark": "light", "light": "auto"}.get(current, "dark")
    self.settings["theme"] = new_theme
    save_settings(self.settings)
    self._apply_theme()
    self.btn_theme.setText(_theme_button_text(new_theme))
    from ..tabs_settings.page import sync_settings_combo

    sync_settings_combo(self, "_settings_theme_combo", new_theme)

def _apply_theme(self):
    theme = self.settings.get("theme", "dark")
    from ..fluent_theme import resolve_is_dark

    is_dark = resolve_is_dark(theme)
    app = QApplication.instance()
    if isinstance(app, QApplication):
        from ..fluent_widgets import is_fluent_widgets_available

        app.setPalette(build_theme_palette(is_dark))
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

    _register_system_theme_follow(self)


def _register_system_theme_follow(self):
    """Install the OS-theme watcher once so 'auto' mode follows live changes."""
    if getattr(self, "_system_theme_follow_registered", False):
        return
    try:
        import weakref

        from ..fluent_theme import (
            _install_theme_watcher,
            register_system_theme_callback,
            set_settings_theme_provider,
        )

        app = QApplication.instance()
        if app is not None:
            _install_theme_watcher(app)
        self_ref = weakref.ref(self)

        def _settings_mode():
            inst = self_ref()
            if inst is None:
                return "auto"
            try:
                return inst.settings.get("theme", "dark")
            except Exception:
                return "auto"

        set_settings_theme_provider(_settings_mode)
        register_system_theme_callback(self._on_system_theme_changed)
        setattr(self, "_system_theme_follow_registered", True)
    except Exception:
        logger.debug("System theme follow install failed", exc_info=True)


def _on_system_theme_changed(self):
    """Watcher callback: re-apply only when the user selected 'auto'."""
    try:
        if self.settings.get("theme", "dark") != "auto":
            return
    except Exception:
        return
    try:
        self._apply_theme()
    except RuntimeError:
        logger.debug("System theme apply skipped (window gone)", exc_info=True)
    except Exception:
        logger.debug("System theme apply failed", exc_info=True)
