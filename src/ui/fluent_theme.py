"""PyQt6-Fluent-Widgets optional bridge (srtgo ktrain/gui/theme.py 계승).

- 하드 의존성 없음: qfluentwidgets/darkdetect 미설치면 전 함수 no-op.
- PyQt6 바인딩 유지(§1.1). PySide6 변형과 혼합 금지 — import명은 qfluentwidgets.
- Mica 강제 off, 라이트는 플랫폼 기본, 다크만 최소 보정.
"""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)

_THEME_WATCHER_STARTED = False


def _installed_dist_names() -> set:
    try:
        from importlib import metadata as _md

        return {str(d.metadata["Name"]) for d in _md.distributions()}
    except Exception:
        return set()


def is_fluent_available() -> bool:
    """qfluentwidgets import 가능 + PyQt6 백엔드 확인 (§1.1 혼합 금지)."""
    try:
        # PyInstaller onefile does not expose all distribution metadata to
        # importlib.metadata. The build spec validates the installed variant;
        # at runtime the actual QWidget binding is the decisive check.
        if not getattr(sys, "frozen", False):
            dists = _installed_dist_names()
            if "PySide6-Fluent-Widgets" in dists:
                return False  # PySide6 변형과 혼합 금지
            if "PyQt6-Fluent-Widgets" not in dists:
                return False
        # 혼합 설치 잔재 방어: 실제 위젯 베이스가 PyQt6인지 확인
        from PyQt6.QtWidgets import QWidget as _QtWidget
        from qfluentwidgets import NavigationInterface as _Nav
        from qfluentwidgets import Pivot as _Pivot
        from qfluentwidgets import PushButton as _Btn

        return all(issubclass(c, _QtWidget) for c in (_Nav, _Pivot, _Btn))
    except Exception:
        logger.warning("Fluent binding validation failed", exc_info=True)
        return False


def setup_app_theme(app: object) -> bool:
    """QApplication 생성 직후 호출. Fluent 없으면 False."""
    if not is_fluent_available():
        return False
    try:
        from qfluentwidgets import Theme, setTheme, setThemeColor

        setTheme(Theme.AUTO)
        try:
            setThemeColor("#4f8cff")
        except Exception:
            logger.debug("Fluent setThemeColor skipped", exc_info=True)
        sync_system_theme()
        _install_theme_watcher(app)
        return True
    except Exception:
        logger.debug("Fluent setup_app_theme skipped", exc_info=True)
        return False


def sync_system_theme() -> None:
    try:
        from qfluentwidgets import Theme, setTheme
    except Exception:
        return
    try:
        import darkdetect

        system = darkdetect.theme()
    except Exception:
        return
    try:
        if system == "Dark":
            setTheme(Theme.DARK)
        elif system == "Light":
            setTheme(Theme.LIGHT)
    except Exception:
        logger.debug("Fluent sync_system_theme failed", exc_info=True)


def sync_fluent_theme(mode: str) -> bool:
    """settings theme('dark'/'light'/'auto') → Fluent 반영. 수동 전환 브리지."""
    if not is_fluent_available():
        return False
    try:
        from qfluentwidgets import Theme, setTheme

        mapping = {"dark": Theme.DARK, "light": Theme.LIGHT, "auto": Theme.AUTO}
        setTheme(mapping.get(mode, Theme.AUTO))
        return True
    except Exception:
        logger.debug("Fluent sync_fluent_theme failed", exc_info=True)
        return False


def configure_fluent_window(window: object) -> None:
    if not is_fluent_available():
        return
    set_mica = getattr(window, "setMicaEffectEnabled", None)
    if callable(set_mica):
        try:
            set_mica(False)
        except Exception:
            logger.debug("Fluent Mica disable skipped", exc_info=True)


def apply_native_widget_style(root: object) -> None:
    """다크에서 네이티브 Qt 위젯 최소 보정. Fluent 없으면 no-op."""
    if not is_fluent_available():
        return
    try:
        from qfluentwidgets import isDarkTheme

        if not isDarkTheme():
            return
        set_ss = getattr(root, "setStyleSheet", None)
        cur = getattr(root, "styleSheet", lambda: "")()
        if callable(set_ss):
            set_ss(
                cur
                + """
                QCheckBox, QLabel, QSpinBox, QDoubleSpinBox, QListWidget, QListWidget::item {
                    color: #E8E8E8;
                    background-color: transparent;
                }
                QSpinBox, QDoubleSpinBox, QListWidget {
                    background-color: #2B2B2B;
                    border: 1px solid #3E3E3E;
                    border-radius: 4px;
                    padding: 2px 4px;
                }
                QListWidget::item:selected { background-color: #3A3A3A; }
                QTableWidget { color: #E8E8E8; background-color: #2B2B2B; gridline-color: #3E3E3E; }
                QHeaderView::section { color: #E8E8E8; background-color: #333333; }
                """
            )
    except Exception:
        logger.debug("Fluent apply_native_widget_style failed", exc_info=True)


def _install_theme_watcher(app: object) -> None:
    global _THEME_WATCHER_STARTED
    if _THEME_WATCHER_STARTED:
        return
    try:
        from PyQt6.QtCore import QTimer
        from PyQt6.QtGui import QGuiApplication

        hints = QGuiApplication.styleHints()
        if hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(lambda _s: QTimer.singleShot(0, sync_system_theme))
        timer = QTimer(app)  # type: ignore[arg-type]
        timer.timeout.connect(sync_system_theme)
        timer.start(3000)
        _THEME_WATCHER_STARTED = True
    except Exception:
        logger.debug("Fluent theme watcher install failed", exc_info=True)


def resolve_is_dark(theme: str) -> bool:
    """settings theme 값 → 실제 다크 여부. 'auto'는 OS 설정을 따른다."""
    if theme == "light":
        return False
    if theme == "dark":
        return True
    try:
        import darkdetect

        return darkdetect.theme() == "Dark"
    except Exception:
        logger.debug("darkdetect unavailable; defaulting to dark", exc_info=True)
        return True
