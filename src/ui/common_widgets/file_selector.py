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
from ..fluent_widgets import DangerButton

from ...core.optional_deps import FITZ_AVAILABLE, fitz
from ...core.pdf_validation import validate_pdf_file
from ...core.settings import load_settings
from .drop_zone import DropZoneWidget

logger = logging.getLogger(__name__)


class FileSelectorWidget(QWidget):
    """파일 선택 위젯 (드롭존 + 버튼)"""
    pathChanged = pyqtSignal(str)

    def __init__(self, placeholder: str | None = None, extensions: list[str] | tuple[str, ...] | None = None, parent=None):
        super().__init__(parent)
        self.extensions = list(extensions or ['.pdf'])
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.drop_zone = DropZoneWidget(extensions, self)
        self.drop_zone.fileDropped.connect(self._on_file_dropped)
        self.drop_zone.clicked.connect(self.browse_file)
        layout.addWidget(self.drop_zone)

        btn_layout = QHBoxLayout()
        from ...core.i18n import tm
        self.btn_browse = QPushButton(tm.get("btn_browse"))
        self.btn_browse.setObjectName("secondaryBtn")
        self.btn_browse.setToolTip(tm.get("tooltip_browse_file"))
        self.btn_browse.clicked.connect(self.browse_file)

        # 최근 파일 버튼
        self.btn_recent = QPushButton(tm.get("btn_recent_short"))
        self.btn_recent.setObjectName("secondaryBtn")
        self.btn_recent.setToolTip(tm.get("recent_files"))
        self.recent_menu = QMenu(self)
        self.btn_recent.setMenu(self.recent_menu)
        self.recent_menu.aboutToShow.connect(self._update_recent_menu)
        # 최근 파일 목록은 PDF만 담으므로 이미지 등 다른 형식 선택칸에서는 숨긴다.
        self.btn_recent.setVisible(".pdf" in self.extensions)

        self.btn_clear = DangerButton(tm.get("btn_clear"))
        self.btn_clear.setObjectName("secondaryBtn")
        self.btn_clear.setMinimumWidth(100)
        self.btn_clear.setToolTip(tm.get("tooltip_clear_file"))
        self._apply_clear_style(True)
        self.btn_clear.setEnabled(False)
        self.btn_clear.clicked.connect(self.clear_path)

        btn_layout.addWidget(self.btn_browse, 1)
        btn_layout.addWidget(self.btn_recent)
        btn_layout.addWidget(self.btn_clear)
        layout.addLayout(btn_layout)

    def _update_recent_menu(self):
        """최근 파일 메뉴 업데이트"""
        self.recent_menu.clear()
        settings = self._get_settings_snapshot()
        recent_value = settings.get("recent_files", [])
        recent = recent_value if isinstance(recent_value, list) else []
        if not recent:
            from ...core.i18n import tm
            action = self.recent_menu.addAction(tm.get("no_recent_files"))
            if action is not None:
                action.setEnabled(False)
        else:
            for path in recent[:10]:
                if isinstance(path, str) and os.path.exists(path):
                    action = self.recent_menu.addAction(f"📄 {os.path.basename(path)}")
                    if action is not None:
                        action.setToolTip(path)
                        action.triggered.connect(lambda checked=False, p=path: self._load_recent(p))

    def _get_settings_snapshot(self) -> dict[str, Any]:
        """Prefer shared in-memory settings to avoid repeated disk reads."""
        current: QObject | None = self.parent()
        while current is not None:
            settings = getattr(current, "settings", None)
            if isinstance(settings, dict):
                return settings
            current = current.parent()
        return load_settings()

    def _load_recent(self, path: str):
        """최근 파일 로드"""
        self.set_path(path)
        self.pathChanged.emit(path)

    def browse_file(self):
        ext_filter = " ".join([f"*{e}" for e in self.extensions])
        from ...core.i18n import tm
        f, _ = QFileDialog.getOpenFileName(self, tm.get("file"), "", f"{tm.get('file')} ({ext_filter})")
        if f:
            self.set_path(f)
            self.pathChanged.emit(f)

    def _on_file_dropped(self, path: str):
        self.btn_clear.setEnabled(bool(path))
        self.pathChanged.emit(path)

    def get_path(self) -> str:
        return self.drop_zone.get_path()

    def set_path(self, path: str):
        self.drop_zone.set_path(path)
        self.btn_clear.setEnabled(bool(path))

    def clear_path(self):
        self.set_path("")
        self.pathChanged.emit("")

    def set_theme(self, is_dark: bool):
        """테마 변경 시 위젯 스타일 동기화"""
        self.drop_zone.set_theme(is_dark)
        self._apply_clear_style(is_dark)

    def _apply_clear_style(self, is_dark: bool):
        if is_dark:
            colors = ("#3e272b", "#ff6b6b", "#5c3a3a", "#5c3a3a", "#ff8787", "#6b7280", "#2d3748")
        else:
            colors = ("#ffe0e0", "#d32f2f", "#ffcdd2", "#ffcdd2", "#c62828", "#94a3b8", "#e2e8f0")
        self.btn_clear.setStyleSheet(
            """
            QPushButton {
                background-color: %s;
                color: %s;
                border: 1px solid %s;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: %s;
                color: %s;
            }
            QPushButton:disabled {
                background-color: transparent;
                color: %s;
                border: 1px solid %s;
            }
            """
            % colors
        )
