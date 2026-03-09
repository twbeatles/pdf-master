"""Compatibility shim for AI tabs mixin.

Keeps the original import path stable while delegating most
implementation to the folder-based tabs_ai package.
"""

import logging
import os
from typing import cast

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.i18n import tm
from ..core.settings import KEYRING_AVAILABLE, get_api_key, save_settings, set_api_key
from .main_window_config import AI_AVAILABLE, MAX_CHAT_HISTORY_ENTRIES, MAX_CHAT_HISTORY_PDFS
from .tabs_ai import MainWindowTabsAiMixin as _MainWindowTabsAiMixin
from .thumbnail_grid import ThumbnailGridWidget
from .widgets import FileSelectorWidget, ToastWidget, is_pdf_encrypted

logger = logging.getLogger(__name__)


class MainWindowTabsAiMixin(_MainWindowTabsAiMixin):
    def _load_api_key_for_ui(self) -> str:
        """keyring 우선 경로로 API 키를 로드하고 레거시 값을 1회 마이그레이션."""
        current = get_api_key() or ""
        legacy = self.settings.get("gemini_api_key", "")
        if legacy:
            if not current:
                if set_api_key(legacy):
                    current = legacy
            # keyring 사용 시에만 파일 저장 키 제거
            if KEYRING_AVAILABLE and "gemini_api_key" in self.settings:
                self.settings.pop("gemini_api_key", None)
                save_settings(self.settings)
        return current

    def _save_api_key(self):
        """API 키 저장"""
        parent = cast(QWidget, self)
        key = self.txt_api_key.text().strip()
        if set_api_key(key):
            # keyring 사용 시에만 레거시 평문 키 제거
            if KEYRING_AVAILABLE and "gemini_api_key" in self.settings:
                self.settings.pop("gemini_api_key", None)
                save_settings(self.settings)
            toast = ToastWidget(tm.get("msg_key_saved"), toast_type='success', duration=2000)
            toast.show_toast(self)
        else:
            QMessageBox.warning(parent, tm.get("error"), tm.get("msg_key_save_failed"))
