"""Compatibility shim for core window mixin.

Keeps original import path stable while delegating implementation
to the folder-based window_core package.
"""

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

from ..core.i18n import tm
from ..core.settings import save_settings
from .main_window_config import APP_NAME, VERSION
from .styles import DARK_STYLESHEET, LIGHT_STYLESHEET
from .widgets import DropZoneWidget, EmptyStateWidget, FileSelectorWidget
from .window_core import MainWindowCoreMixin
from .zoomable_preview import ZoomablePreviewWidget

logger = logging.getLogger(__name__)
