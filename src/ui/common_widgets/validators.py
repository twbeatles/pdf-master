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


def _item_user_data(item: QListWidgetItem | None) -> Any | None:
    if item is None:
        return None
    return item.data(Qt.ItemDataRole.UserRole)

def _item_user_path(item: QListWidgetItem | None) -> str | None:
    data = _item_user_data(item)
    return data if isinstance(data, str) else None

def is_valid_pdf(file_path: str) -> bool:
    """
    PDF 파일 유효성 검사 (PDF 헤더 확인)

    Args:
        file_path: 검사할 파일 경로

    Returns:
        유효한 PDF인지 여부
    """
    result = validate_pdf_file(file_path)
    if not result.ok:
        logger.warning("Invalid PDF file (%s): %s", result.reason, file_path)
    return result.ok

def is_pdf_encrypted(file_path: str) -> bool:
    """
    PDF 파일 암호화 여부 확인 (v4.5: 공용 함수)

    Args:
        file_path: 검사할 PDF 파일 경로

    Returns:
        암호화된 PDF인지 여부
    """
    if not file_path or not os.path.exists(file_path):
        return False

    if not FITZ_AVAILABLE:
        logger.debug("PyMuPDF not available; skipping encrypted PDF check for %s", file_path)
        return False

    try:
        doc = fitz.open(file_path)
        try:
            return bool(doc.is_encrypted)
        finally:
            doc.close()
    except Exception as e:
        logger.debug(f"Cannot check PDF encryption: {file_path}: {e}")
        return False

class WheelEventFilter(QObject):
    """QSpinBox, QComboBox 등에서 스크롤 휠로 값이 변경되는 것을 방지"""
    def eventFilter(self, a0: QObject | None, a1: QEvent | None) -> bool:
        if a1 is not None and a1.type() == QEvent.Type.Wheel:
            return True  # 휠 이벤트 차단
        return super().eventFilter(a0, a1)
