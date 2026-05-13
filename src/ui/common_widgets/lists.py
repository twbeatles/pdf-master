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


from .validators import _item_user_data, _item_user_path, is_valid_pdf

class FileListWidget(QListWidget):
    """다중 파일 드래그 앤 드롭 리스트 (PDF)"""
    fileAdded = pyqtSignal(str)  # 파일 추가 시그널

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setMinimumHeight(140)
        from ...core.i18n import tm
        self.setToolTip(tm.get("tooltip_pdf_list_drop"))

    def dragEnterEvent(self, e: QDragEnterEvent | None):
        mime_data = e.mimeData() if e is not None else None
        if mime_data is not None and mime_data.hasUrls():
            if e is not None:
                e.acceptProposedAction()
            self.setStyleSheet("QListWidget { border: 2px solid #4f8cff; background: rgba(79, 140, 255, 0.05); }")
        else:
            super().dragEnterEvent(e)

    def dragLeaveEvent(self, e: QDragLeaveEvent | None):
        self.setStyleSheet("")
        super().dragLeaveEvent(e)

    def dragMoveEvent(self, e: QDragMoveEvent | None):
        mime_data = e.mimeData() if e is not None else None
        if mime_data is not None and mime_data.hasUrls():
            if e is not None:
                e.setDropAction(Qt.DropAction.CopyAction)
                e.accept()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, event: QDropEvent | None):
        self.setStyleSheet("")
        mime_data = event.mimeData() if event is not None else None
        if mime_data is not None and mime_data.hasUrls():
            if event is not None:
                event.setDropAction(Qt.DropAction.CopyAction)
                event.accept()
            last_path: str | None = None
            for url in mime_data.urls():
                path = str(url.toLocalFile())

                # 폴더인 경우 내부 PDF 모두 추가
                if os.path.isdir(path):
                    for filename in os.listdir(path):
                        if filename.lower().endswith('.pdf'):
                            file_path = os.path.join(path, filename)
                            if self._add_pdf_item(file_path):
                                last_path = file_path
                # PDF 파일인 경우
                elif path.lower().endswith('.pdf'):
                    if self._add_pdf_item(path):
                        last_path = path

            if last_path is not None:
                self.fileAdded.emit(last_path)
        else:
            super().dropEvent(event)

    def _add_pdf_item(self, path: str) -> bool:
        """PDF 항목 추가 (중복 체크 및 유효성 검사 포함), 성공 시 True 반환"""
        # 유효성 검사
        if not is_valid_pdf(path):
            return False

        # 중복 체크
        exists = any(_item_user_path(self.item(i)) == path for i in range(self.count()))
        if not exists:
            item = QListWidgetItem(f"📄 {os.path.basename(path)}")
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setToolTip(path)
            self.addItem(item)
            return True
        return False

    def get_all_paths(self) -> list[str]:
        return [path for i in range(self.count()) if (path := _item_user_path(self.item(i))) is not None]

    def add_file(self, path: str):
        """파일 추가 (중복 체크 포함)"""
        path = str(path)
        if not path.lower().endswith('.pdf'):
            return
        if self._add_pdf_item(path):
            self.fileAdded.emit(path)

class ImageListWidget(QListWidget):
    """이미지 파일 드래그 앤 드롭 리스트"""
    IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp')

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setMinimumHeight(100)
        from ...core.i18n import tm
        self.setToolTip(tm.get("tooltip_image_list_drop"))

    def dragEnterEvent(self, e: QDragEnterEvent | None):
        mime_data = e.mimeData() if e is not None else None
        if mime_data is not None and mime_data.hasUrls():
            if e is not None:
                e.acceptProposedAction()
            self.setStyleSheet("QListWidget { border: 2px solid #00d9a0; }")
        else:
            super().dragEnterEvent(e)

    def dragLeaveEvent(self, e: QDragLeaveEvent | None):
        self.setStyleSheet("")
        super().dragLeaveEvent(e)

    def dragMoveEvent(self, e: QDragMoveEvent | None):
        mime_data = e.mimeData() if e is not None else None
        if mime_data is not None and mime_data.hasUrls():
            if e is not None:
                e.setDropAction(Qt.DropAction.CopyAction)
                e.accept()
        else:
            super().dragMoveEvent(e)

    def dropEvent(self, event: QDropEvent | None):
        self.setStyleSheet("")
        mime_data = event.mimeData() if event is not None else None
        if mime_data is not None and mime_data.hasUrls():
            if event is not None:
                event.setDropAction(Qt.DropAction.CopyAction)
                event.accept()
            for url in mime_data.urls():
                path = str(url.toLocalFile())
                if path.lower().endswith(self.IMAGE_EXTENSIONS):
                    exists = any(_item_user_path(self.item(i)) == path for i in range(self.count()))
                    if not exists:
                        item = QListWidgetItem(f"🖼️ {os.path.basename(path)}")
                        item.setData(Qt.ItemDataRole.UserRole, path)
                        item.setToolTip(path)
                        self.addItem(item)
        else:
            super().dropEvent(event)

    def get_all_paths(self) -> list[str]:
        return [path for i in range(self.count()) if (path := _item_user_path(self.item(i))) is not None]

class DraggableListWidget(QListWidget):
    """
    드래그 앤 드롭으로 순서 변경이 가능한 리스트 위젯 (v4.4)

    CLAUDE.md에 문서화된 대로 itemsReordered 시그널 지원
    """
    itemsReordered = pyqtSignal(list)  # 재정렬된 항목 리스트

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        model = self.model()
        if model is not None:
            model.rowsMoved.connect(self._on_rows_moved)

    def _on_rows_moved(self, *_args: object):
        """행 이동 시 시그널 발생"""
        items = self.get_all_items()
        self.itemsReordered.emit(items)

    def get_all_items(self) -> list[Any]:
        """모든 항목의 데이터 반환"""
        return [_item_user_data(self.item(i)) for i in range(self.count())]

    def add_item(self, text: str, data: Any = None):
        """항목 추가"""
        item = QListWidgetItem(text)
        if data is not None:
            item.setData(Qt.ItemDataRole.UserRole, data)
        self.addItem(item)
