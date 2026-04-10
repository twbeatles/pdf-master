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


def _get_output_dialog_dir(self) -> str:
    """출력 관련 다이얼로그의 시작 경로를 결정한다."""
    last_output_dir = self.settings.get("last_output_dir", "")
    if isinstance(last_output_dir, str) and last_output_dir:
        if os.path.isdir(last_output_dir):
            return last_output_dir
        parent = os.path.dirname(last_output_dir)
        if parent and os.path.isdir(parent):
            return parent
    return ""


def _remember_output_location(self, selected_path: str) -> None:
    """출력 파일/폴더 선택 결과를 최근 출력 폴더로 저장한다."""
    if not selected_path:
        return

    output_dir = selected_path if os.path.isdir(selected_path) else os.path.dirname(selected_path)
    if not output_dir:
        return

    self.settings["last_output_dir"] = output_dir
    if hasattr(self, "_schedule_settings_save"):
        self._schedule_settings_save()
    else:
        save_settings(self.settings)


def _choose_save_file(self, title: str, default_name: str, file_filter: str):
    start_dir = self._get_output_dialog_dir()
    initial_path = os.path.join(start_dir, default_name) if start_dir else default_name
    selected, selected_filter = QFileDialog.getSaveFileName(self, title, initial_path, file_filter)
    if selected:
        self._remember_output_location(selected)
    return selected, selected_filter


def _choose_output_directory(self, title: str) -> str:
    start_dir = self._get_output_dialog_dir()
    selected = QFileDialog.getExistingDirectory(self, title, start_dir)
    if selected:
        self._remember_output_location(selected)
    return selected

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
