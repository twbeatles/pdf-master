from __future__ import annotations

import logging
from typing import Iterable

from PyQt6.QtCore import QThread, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QCloseEvent, QCursor, QImage, QMouseEvent, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...core.i18n import tm
from ...core.optional_deps import fitz
from ...core.perf import PerfTimer

logger = logging.getLogger(__name__)


class ThumbnailLabel(QFrame):
    """Clickable thumbnail item."""

    clicked = pyqtSignal(int)
    clickedWithModifiers = pyqtSignal(int, object)

    def __init__(self, page_index: int, parent=None):
        super().__init__(parent)
        self.page_index = page_index
        self._selected = False
        self._active = False

        self.setFixedSize(160, 200)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(140, 160)
        self.image_label.setStyleSheet("background: #1a1a2e; border-radius: 4px;")
        layout.addWidget(self.image_label)

        self.page_label = QLabel(tm.get("thumb_page_label", page_index + 1))
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.page_label)

        self._update_style()

    def set_pixmap(self, pixmap: QPixmap):
        """Assign pre-sized thumbnail pixmap directly."""
        self.image_label.setPixmap(pixmap)

    def set_selected(self, selected: bool):
        self._selected = selected
        self._update_style()

    def set_active(self, active: bool):
        self._active = active
        self._update_style()

    def _update_style(self):
        if self._active and self._selected:
            self.setStyleSheet(
                """
                ThumbnailLabel {
                    background: rgba(79, 140, 255, 0.22);
                    border: 2px solid #4f8cff;
                    border-radius: 8px;
                }
                """
            )
            self.page_label.setStyleSheet("color: #4f8cff; font-size: 11px; font-weight: bold;")
        elif self._active:
            self.setStyleSheet(
                """
                ThumbnailLabel {
                    background: rgba(79, 140, 255, 0.12);
                    border: 2px solid #4f8cff;
                    border-radius: 8px;
                }
                ThumbnailLabel:hover {
                    background: rgba(79, 140, 255, 0.16);
                }
                """
            )
            self.page_label.setStyleSheet("color: #4f8cff; font-size: 11px; font-weight: bold;")
        elif self._selected:
            self.setStyleSheet(
                """
                ThumbnailLabel {
                    background: rgba(0, 217, 160, 0.12);
                    border: 2px solid #00d9a0;
                    border-radius: 8px;
                }
                ThumbnailLabel:hover {
                    background: rgba(0, 217, 160, 0.16);
                }
                """
            )
            self.page_label.setStyleSheet("color: #00d9a0; font-size: 11px; font-weight: bold;")
        else:
            self.setStyleSheet(
                """
                ThumbnailLabel {
                    background: rgba(30, 30, 50, 0.5);
                    border: 1px solid #333;
                    border-radius: 8px;
                }
                ThumbnailLabel:hover {
                    background: rgba(79, 140, 255, 0.1);
                    border-color: #4f8cff;
                }
                """
            )
            self.page_label.setStyleSheet("color: #888; font-size: 11px;")

    def mousePressEvent(self, a0: QMouseEvent | None):
        if a0 is not None and a0.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.page_index)
            self.clickedWithModifiers.emit(self.page_index, a0.modifiers())
        super().mousePressEvent(a0)
