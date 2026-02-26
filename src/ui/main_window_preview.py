"""Compatibility shim for preview mixin.

Keeps original import path stable while delegating implementation
to the folder-based window_preview package.
"""

import logging
import os

import fitz
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QPixmap
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core.i18n import tm
from ..core.settings import save_settings
from .widgets import FileSelectorWidget
from .window_preview import MainWindowPreviewMixin
from .zoomable_preview import ZoomablePreviewWidget

logger = logging.getLogger(__name__)
