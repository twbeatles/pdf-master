"""Compatibility shim for advanced tabs mixin.

This module keeps the original import path stable while delegating
implementation to the folder-based tabs_advanced package.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
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
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.i18n import tm
from .widgets import FileSelectorWidget, ToastWidget
from .tabs_advanced import MainWindowTabsAdvancedMixin

__all__ = ["MainWindowTabsAdvancedMixin"]
