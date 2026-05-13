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


class EmptyStateWidget(QFrame):
    """
    빈 상태 안내 위젯

    파일이 없거나 시작 상태일 때 표시되는 친근한 안내 UI
    """
    actionClicked = pyqtSignal()

    def __init__(self, icon: str = "📄", title: str | None = None,
                 description: str | None = None,
                 action_text: str | None = None, parent=None):
        super().__init__(parent)
        from ...core.i18n import tm

        if title is None:
            title = tm.get("empty_title")
        if description is None:
            description = tm.get("empty_desc")

        self._is_dark_theme = True


        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)
        layout.setContentsMargins(30, 40, 30, 40)

        # 아이콘
        self.icon_label = QLabel(icon)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 48px; background: transparent;")
        layout.addWidget(self.icon_label)

        # 제목
        self.title_label = QLabel(title or "")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        # 설명
        self.desc_label = QLabel(description or "")
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)

        # 액션 버튼 (선택적)
        if action_text:
            self.action_btn = QPushButton(action_text)
            self.action_btn.setObjectName("secondaryBtn")
            self.action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.action_btn.clicked.connect(self.actionClicked.emit)
            layout.addWidget(self.action_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self._apply_theme_style()

    def _apply_theme_style(self):
        if self._is_dark_theme:
            self.setStyleSheet("""
                EmptyStateWidget {
                    background: transparent;
                    border: 2px dashed #2d3748;
                    border-radius: 16px;
                }
            """)
            self.title_label.setStyleSheet("""
                font-size: 16px;
                font-weight: 600;
                color: #94a3b8;
                background: transparent;
            """)
            self.desc_label.setStyleSheet("""
                font-size: 13px;
                color: #64748b;
                background: transparent;
            """)
        else:
            self.setStyleSheet("""
                EmptyStateWidget {
                    background: transparent;
                    border: 2px dashed #e2e8f0;
                    border-radius: 16px;
                }
            """)
            self.title_label.setStyleSheet("""
                font-size: 16px;
                font-weight: 600;
                color: #475569;
                background: transparent;
            """)
            self.desc_label.setStyleSheet("""
                font-size: 13px;
                color: #94a3b8;
                background: transparent;
            """)

    def set_theme(self, is_dark: bool):
        """테마 설정"""
        self._is_dark_theme = is_dark
        self._apply_theme_style()

    def set_content(self, icon: str | None = None, title: str | None = None, description: str | None = None):
        """내용 업데이트"""
        if icon:
            self.icon_label.setText(icon)
        if title:
            self.title_label.setText(title)
        if description:
            self.desc_label.setText(description)
