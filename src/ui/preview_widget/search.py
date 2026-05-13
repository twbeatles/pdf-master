from __future__ import annotations

import logging

from PyQt6.QtCore import QModelIndex, QPointF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtPdf import QPdfBookmarkModel, QPdfDocument, QPdfSearchModel
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from ...core.i18n import tm

logger = logging.getLogger(__name__)


class PreviewSearchLineEdit(QLineEdit):
    submitRequested = pyqtSignal()
    previousRequested = pyqtSignal()
    escapePressed = pyqtSignal()

    def keyPressEvent(self, event):
        if event is None:
            return
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.previousRequested.emit()
            else:
                self.submitRequested.emit()
            event.accept()
            return
        if key == Qt.Key.Key_Escape:
            self.escapePressed.emit()
            event.accept()
            return
        super().keyPressEvent(event)
