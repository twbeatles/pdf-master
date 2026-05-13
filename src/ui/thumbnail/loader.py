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


from .document import _open_thumbnail_document

class ThumbnailLoaderThread(QThread):
    """Background thumbnail loader for selected page indices."""

    thumbnail_ready = pyqtSignal(int, QPixmap)
    loading_complete = pyqtSignal()
    progress = pyqtSignal(int)

    def __init__(
        self,
        pdf_path: str,
        page_indices: list[int],
        password: str | None = None,
        thumb_w: int = 140,
        thumb_h: int = 160,
    ):
        super().__init__()
        self.pdf_path = pdf_path
        self.page_indices = page_indices
        self.password = password
        self.thumb_w = thumb_w
        self.thumb_h = thumb_h
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        doc = None
        try:
            with PerfTimer("ui.thumbnail.batch_load", logger=logger, extra={"count": len(self.page_indices)}):
                doc, error_message = _open_thumbnail_document(self.pdf_path, self.password)
                if not doc:
                    logger.warning("Thumbnail loader skipped document %s: %s", self.pdf_path, error_message)
                    return

                total = max(1, len(self.page_indices))
                for i, page_index in enumerate(self.page_indices):
                    if self._is_cancelled:
                        break
                    if page_index < 0 or page_index >= len(doc):
                        continue

                    page = doc[page_index]
                    scale = min(self.thumb_w / max(page.rect.width, 1), self.thumb_h / max(page.rect.height, 1))
                    scale = max(0.05, scale)
                    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))

                    img_data = bytes(pix.samples)
                    fmt = QImage.Format.Format_RGBA8888 if pix.alpha else QImage.Format.Format_RGB888
                    img = QImage(img_data, pix.width, pix.height, pix.stride, fmt)
                    pixmap = QPixmap.fromImage(img.copy())

                    self.thumbnail_ready.emit(page_index, pixmap)
                    self.progress.emit(int((i + 1) / total * 100))
        except Exception as e:
            logger.error("Thumbnail loading failed: %s", e)
        finally:
            if doc:
                doc.close()
            self.loading_complete.emit()
