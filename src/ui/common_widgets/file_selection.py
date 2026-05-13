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
        layout.addWidget(self.drop_zone)

        btn_layout = QHBoxLayout()
        from ...core.i18n import tm
        self.btn_browse = QPushButton(tm.get("btn_browse"))
        self.btn_browse.setObjectName("secondaryBtn")
        self.btn_browse.setToolTip(tm.get("tooltip_browse_file"))
        self.btn_browse.clicked.connect(self.browse_file)

        # 최근 파일 버튼
        self.btn_recent = QToolButton()
        self.btn_recent.setText("📋")
        self.btn_recent.setToolTip(tm.get("recent_files"))
        self.btn_recent.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.btn_recent.setFixedWidth(35)
        self.recent_menu = QMenu(self)
        self.btn_recent.setMenu(self.recent_menu)
        self.recent_menu.aboutToShow.connect(self._update_recent_menu)

        self.btn_clear = QPushButton(tm.get("btn_clear"))
        self.btn_clear.setObjectName("secondaryBtn")
        self.btn_clear.setFixedWidth(100)  # 80 -> 100
        self.btn_clear.setToolTip(tm.get("tooltip_clear_file"))
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #3e272b;
                color: #ff6b6b;
                border: 1px solid #5c3a3a;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #5c3a3a;
                color: #ff8787;
            }
        """)
        self.btn_clear.clicked.connect(self.clear_path)

        btn_layout.addWidget(self.btn_browse)
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
        self.drop_zone.set_path(path)
        self.pathChanged.emit(path)

    def browse_file(self):
        ext_filter = " ".join([f"*{e}" for e in self.extensions])
        from ...core.i18n import tm
        f, _ = QFileDialog.getOpenFileName(self, tm.get("file"), "", f"{tm.get('file')} ({ext_filter})")
        if f:
            self.drop_zone.set_path(f)
            self.pathChanged.emit(f)

    def _on_file_dropped(self, path: str):
        self.pathChanged.emit(path)

    def get_path(self) -> str:
        return self.drop_zone.get_path()

    def set_path(self, path: str):
        self.drop_zone.set_path(path)

    def clear_path(self):
        self.drop_zone.set_path("")
        self.pathChanged.emit("")

    def set_theme(self, is_dark: bool):
        """테마 변경 시 위젯 스타일 동기화"""
        self.drop_zone.set_theme(is_dark)
        if is_dark:
            self.btn_clear.setStyleSheet("""
                QPushButton {
                    background-color: #3e272b;
                    color: #ff6b6b;
                    border: 1px solid #5c3a3a;
                    padding: 10px;
                }
                QPushButton:hover {
                    background-color: #5c3a3a;
                    color: #ff8787;
                }
            """)
        else:
            self.btn_clear.setStyleSheet("""
                QPushButton {
                    background-color: #ffe0e0;
                    color: #d32f2f;
                    border: 1px solid #ffcdd2;
                    padding: 10px;
                }
                QPushButton:hover {
                    background-color: #ffcdd2;
                    color: #c62828;
                }
            """)
