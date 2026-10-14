from __future__ import annotations

import logging

from PySide6.QtCore import QModelIndex, QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtPdf import QPdfBookmarkModel, QPdfDocument, QPdfSearchModel
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtWidgets import (
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
    submitRequested = Signal()
    previousRequested = Signal()
    escapePressed = Signal()

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
