"""Compatibility shim for basic tabs mixin.

Keeps the original import path stable while delegating most
implementation to the folder-based tabs_basic package.
"""

import logging
import os
from typing import cast

import fitz
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..core.constants import SUPPORTED_IMAGE_FORMATS
from ..core.i18n import tm
from ..core.settings import save_settings
from .tabs_basic import MainWindowTabsBasicMixin as _MainWindowTabsBasicMixin
from .widgets import FileListWidget, FileSelectorWidget, ImageListWidget, ToastWidget

logger = logging.getLogger(__name__)


class MainWindowTabsBasicMixin(_MainWindowTabsBasicMixin):
    def _save_convert_preset(self):
        """변환 설정 프리셋 저장"""
        parent = cast(QWidget, self)
        name, ok = QInputDialog.getText(parent, tm.get("dlg_save_preset"), tm.get("lbl_preset_name"))
        if ok and name:
            presets = self.settings.get("convert_presets", {})
            presets[name] = {
                "format": self.cmb_fmt.currentText(),
                "dpi": self.spn_dpi.value()
            }
            self.settings["convert_presets"] = presets
            save_settings(self.settings)
            toast = ToastWidget(tm.get("msg_preset_saved", name), toast_type='success', duration=2000)
            toast.show_toast(self)

    def _load_convert_preset(self):
        """변환 설정 프리셋 불러오기"""
        parent = cast(QWidget, self)
        presets = self.settings.get("convert_presets", {})
        if not presets:
            QMessageBox.information(parent, tm.get("dlg_preset"), tm.get("msg_no_presets"))
            return

        # 프리셋 선택 다이얼로그
        name, ok = QInputDialog.getItem(parent, tm.get("dlg_load_preset"), tm.get("lbl_select_preset"), 
                                        list(presets.keys()), 0, False)
        if ok and name:
            preset = presets[name]
            preset_fmt = (preset.get("format", "png") or "png").lower()
            idx = self.cmb_fmt.findText(preset_fmt)
            if idx >= 0:
                self.cmb_fmt.setCurrentIndex(idx)
            else:
                fallback_idx = self.cmb_fmt.findText("png")
                self.cmb_fmt.setCurrentIndex(max(0, fallback_idx))
            self.spn_dpi.setValue(preset.get("dpi", 150))
            toast = ToastWidget(tm.get("msg_preset_applied", name), toast_type='info', duration=2000)
            toast.show_toast(self)
