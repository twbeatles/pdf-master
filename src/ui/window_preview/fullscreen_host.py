"""미리보기 전체화면 호스트 — ZoomablePreviewWidget reparent."""

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget

from ...core.i18n import tm

logger = logging.getLogger(__name__)


class PreviewFullscreenHost(QMainWindow):
    """미리보기 위젯을 담아 OS 전체화면으로 표시하는 호스트 창."""

    hostClosing = pyqtSignal()  # reparent 전에 호출 — 본창이 위젯을 회수 (포커스 유지)
    layoutCycleExitRequested = pyqtSignal()  # F11: 전체화면+포커스 모두 해제 (메인 순환과 동일)
    placeTextboxRequested = pyqtSignal()
    insertTextboxRequested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(tm.get("preview_title_fullscreen"))
        self.setWindowFlag(Qt.WindowType.Window, True)
        self._preview: QWidget | None = None
        self._closing = False

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        toolbar = QHBoxLayout()
        self.btn_close = QPushButton(tm.get("btn_preview_fullscreen_exit"))
        self.btn_close.setObjectName("toolbarSecondaryBtn")
        self.btn_close.clicked.connect(self.close)
        toolbar.addWidget(self.btn_close)

        self.btn_place = QPushButton(tm.get("btn_textbox_drag_select"))
        self.btn_place.setObjectName("toolbarSecondaryBtn")
        self.btn_place.clicked.connect(self.placeTextboxRequested.emit)
        toolbar.addWidget(self.btn_place)

        self.btn_insert = QPushButton(tm.get("btn_insert_textbox"))
        self.btn_insert.setObjectName("toolbarBtn")
        self.btn_insert.clicked.connect(self.insertTextboxRequested.emit)
        toolbar.addWidget(self.btn_insert)

        self.lbl_hint = QLabel(tm.get("hint_preview_fullscreen_bar"))
        self.lbl_hint.setObjectName("desc")
        self.lbl_hint.setWordWrap(True)
        toolbar.addWidget(self.lbl_hint, 1)
        layout.addLayout(toolbar)

        self._body = QVBoxLayout()
        self._body.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self._body, 1)

        # Esc: 전체화면만 종료(포커스 유지). F11: 메인 순환과 동일하게 일반 레이아웃으로.
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.close)
        QShortcut(QKeySequence("F11"), self, self.layoutCycleExitRequested.emit)
        QShortcut(QKeySequence("Ctrl+F11"), self, self.close)

    def set_actions_enabled(self, enabled: bool) -> None:
        """Worker busy 중 배치/삽입 중복 실행 방지."""
        self.btn_place.setEnabled(bool(enabled))
        self.btn_insert.setEnabled(bool(enabled))

    def attach_preview(self, preview: QWidget) -> None:
        """미리보기 위젯을 이 창으로 옮긴다 (기존 부모에서 제거됨)."""
        if self._preview is not None and self._preview is not preview:
            self.detach_preview()
        self._preview = preview
        preview.setParent(self.centralWidget())
        self._body.addWidget(preview, 1)
        preview.show()

    def detach_preview(self) -> QWidget | None:
        """미리보기 위젯을 레이아웃에서 떼고 반환 (parent는 호출측이 설정)."""
        preview = self._preview
        self._preview = None
        if preview is None:
            return None
        self._body.removeWidget(preview)
        preview.setParent(None)
        return preview

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        if not self._closing:
            self._closing = True
            try:
                self.hostClosing.emit()
            except Exception:
                logger.debug("hostClosing handlers failed", exc_info=True)
        super().closeEvent(a0)
        self._closing = False


__all__ = ["PreviewFullscreenHost"]
