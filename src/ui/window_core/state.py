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

def _open_last_folder(self):
    """Open folder containing last output"""
    if self._last_output_path and os.path.exists(self._last_output_path):
        if os.path.isdir(self._last_output_path):
            folder = self._last_output_path
        else:
            folder = os.path.dirname(self._last_output_path)
        if os.name == 'nt':
            if os.path.isdir(self._last_output_path):
                subprocess.Popen(['explorer', folder])
            else:
                subprocess.Popen(['explorer', '/select,', self._last_output_path])
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

def _save_splitter_state(self):
    """Save splitter position"""
    self.settings["splitter_sizes"] = self.content_splitter.sizes()
    if hasattr(self, "_schedule_settings_save"):
        self._schedule_settings_save()
    else:
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
