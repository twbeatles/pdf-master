from __future__ import annotations

import logging
import os
from typing import Any

from PyQt6.QtCore import QEvent, QObject, Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDragMoveEvent, QDropEvent
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ...core.optional_deps import FITZ_AVAILABLE, fitz
from ...core.pdf_validation import validate_pdf_file
from ...core.settings import load_settings

logger = logging.getLogger(__name__)


class DropZoneWidget(QFrame):
    """시각적 드래그 앤 드롭 영역 (테마 대응)"""
    fileDropped = pyqtSignal(str)

    def __init__(self, accept_extensions: list[str] | tuple[str, ...] | None = None, parent=None):
        super().__init__(parent)
        self.accept_extensions = list(accept_extensions or ['.pdf'])
        self.setAcceptDrops(True)
        self.setMinimumHeight(100)
        self._current_path = ""
        self._is_dragging = False
        self._is_dark_theme = True

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(4)

        self.icon_label = QLabel("📄")
        self.icon_label.setStyleSheet("font-size: 32px; background: transparent; border: none;")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        from ...core.i18n import tm
        self.text_label = QLabel(tm.get("drop_title"))
        self.text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.hint_label = QLabel(tm.get("drop_hint"))
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.path_label = QLabel("")
        self.path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.path_label.setWordWrap(True)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        layout.addWidget(self.hint_label)
        layout.addWidget(self.path_label)

        self._apply_theme_style()

    def set_theme(self, is_dark: bool):
        self._is_dark_theme = is_dark
        self._apply_theme_style()

    def _apply_theme_style(self):
        if self._is_dark_theme:
            self.setStyleSheet("""
                DropZoneWidget {
                    border: 2px dashed #4f8cff;
                    border-radius: 12px;
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(22, 27, 34, 0.9), stop:1 rgba(13, 17, 23, 0.95));
                }
                DropZoneWidget:hover {
                    border-color: #6ba0ff;
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(30, 40, 55, 0.95), stop:1 rgba(22, 27, 34, 0.95));
                }
            """)
            self.text_label.setStyleSheet("color: #8b949e; font-size: 13px; background: transparent; border: none;")
            self.hint_label.setStyleSheet("color: #6e7681; font-size: 11px; background: transparent; border: none;")
            self.path_label.setStyleSheet("color: #00d9a0; font-size: 12px; font-weight: bold; background: transparent; border: none;")
        else:
            self.setStyleSheet("""
                DropZoneWidget {
                    border: 2px dashed #4f8cff;
                    border-radius: 12px;
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255, 255, 255, 0.95), stop:1 rgba(246, 248, 250, 0.9));
                }
                DropZoneWidget:hover {
                    border-color: #6ba0ff;
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255, 255, 255, 1), stop:1 rgba(240, 245, 250, 0.95));
                }
            """)
            self.text_label.setStyleSheet("color: #656d76; font-size: 13px; background: transparent; border: none;")
            self.hint_label.setStyleSheet("color: #8c959f; font-size: 11px; background: transparent; border: none;")
            self.path_label.setStyleSheet("color: #00a080; font-size: 12px; font-weight: bold; background: transparent; border: none;")

    def dragEnterEvent(self, a0: QDragEnterEvent | None):
        from ...core.i18n import tm
        mime_data = a0.mimeData() if a0 is not None else None
        if mime_data is not None and mime_data.hasUrls():
            for url in mime_data.urls():
                path = url.toLocalFile().lower()
                if any(path.endswith(ext) for ext in self.accept_extensions):
                    self._is_dragging = True
                    self.setStyleSheet("""
                        DropZoneWidget {
                            border: 3px solid #4f8cff;
                            border-radius: 12px;
                            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(79, 140, 255, 0.15), stop:1 rgba(58, 122, 232, 0.1));
                        }
                    """)
                    self.text_label.setText(tm.get("drop_success"))
                    self.text_label.setStyleSheet("color: #4f8cff; font-size: 15px; font-weight: bold; background: transparent; border: none;")
                    if a0 is not None:
                        a0.acceptProposedAction()
                    return
        if a0 is not None:
            a0.ignore()

    def dragLeaveEvent(self, a0: QDragLeaveEvent | None):
        self._is_dragging = False
        self._apply_theme_style()
        from ...core.i18n import tm
        self.text_label.setText(tm.get("drop_title"))
        if a0 is not None:
            super().dragLeaveEvent(a0)

    def dropEvent(self, a0: QDropEvent | None):
        self._is_dragging = False
        mime_data = a0.mimeData() if a0 is not None else None
        if mime_data is not None and mime_data.hasUrls():
            for url in mime_data.urls():
                path = url.toLocalFile()
                if any(path.lower().endswith(ext) for ext in self.accept_extensions):
                    self._current_path = path
                    self._apply_theme_style()
                    from ...core.i18n import tm
                    self.text_label.setText(tm.get("drop_title"))
                    self.path_label.setText(f"✓ {os.path.basename(path)}")
                    self.icon_label.setText("✅")
                    self.fileDropped.emit(path)
                    if a0 is not None:
                        a0.acceptProposedAction()
                    return
        if a0 is not None:
            a0.ignore()
        self._apply_theme_style()

    def get_path(self) -> str:
        return self._current_path

    def set_path(self, path: str):
        self._current_path = path
        if path:
            self.path_label.setText(f"✓ {os.path.basename(path)}")
            self.icon_label.setText("✅")
        else:
            self.path_label.setText("")
            self.icon_label.setText("📄")

