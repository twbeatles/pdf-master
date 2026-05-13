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


def _open_thumbnail_document(pdf_path: str, password: str | None = None):
    doc = fitz.open(pdf_path)
    if not doc.is_encrypted:
        return doc, None

    if not password:
        doc.close()
        return None, tm.get("preview_encrypted")

    if not doc.authenticate(password):
        doc.close()
        return None, tm.get("preview_password_wrong")

    return doc, None
