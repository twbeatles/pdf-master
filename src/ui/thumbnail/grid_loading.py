from __future__ import annotations

from .._typing import ThumbnailGridHost
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
from .loader import ThumbnailLoaderThread
from .tile import ThumbnailLabel


class ThumbnailGridLoadingMixin(ThumbnailGridHost):
    def load_pdf(self, pdf_path: str, password: str | None = None):
        if not pdf_path:
            self.clear()
            return

        self._cleanup_loader_thread()
        self._pdf_path = pdf_path
        self._pdf_password = password
        self._clear_thumbnails()

        doc = None
        try:
            doc, error_message = _open_thumbnail_document(pdf_path, password)
            if not doc:
                self._set_loading_message(error_message or tm.get("preview_default"))
                return
            self._total_pages = len(doc)
            self.info_label.setText(tm.get("thumb_page_count", self._total_pages))
            for i in range(self._total_pages):
                thumb = ThumbnailLabel(i)
                thumb.clickedWithModifiers.connect(self._on_thumbnail_clicked)
                self._thumbnails.append(thumb)
            self._arrange_grid()
            self._request_visible_thumbnails()
        except Exception as e:
            logger.error("Failed to open PDF: %s", e)
            self._set_loading_message(tm.get("thumb_load_failed", str(e)))
            return
        finally:
            if doc:
                doc.close()

    def _disconnect_loader_thread(self, thread: ThumbnailLoaderThread):
        try:
            thread.thumbnail_ready.disconnect(self._on_thumbnail_ready)
        except Exception:
            pass
        try:
            thread.progress.disconnect(self._on_loader_progress)
        except Exception:
            pass
        try:
            thread.loading_complete.disconnect(self._on_loading_complete)
        except Exception:
            pass

    def _cleanup_loader_thread(self):
        thread = self._loader_thread
        if thread:
            self._disconnect_loader_thread(thread)

            if thread.isRunning():
                thread.cancel()
                try:
                    thread.finished.connect(thread.deleteLater)
                except Exception:
                    pass
                if not thread.wait(300):
                    logger.info("ThumbnailLoaderThread is stopping in background")
            else:
                thread.deleteLater()

            self._loader_thread = None

        if self._active_batch_indices:
            self._pending_indices.update(self._active_batch_indices)
            self._requested_indices.difference_update(self._active_batch_indices)
            self._active_batch_indices = []

    def _start_next_loader(self):
        if self._loader_thread and self._loader_thread.isRunning():
            return
        if not self._pending_indices:
            return

        batch = sorted(self._pending_indices)[: self._MAX_BATCH_SIZE]
        for idx in batch:
            self._pending_indices.discard(idx)
        self._requested_indices.update(batch)
        self._active_batch_indices = batch

        self._loader_thread = ThumbnailLoaderThread(
            self._pdf_path,
            batch,
            password=self._pdf_password,
            thumb_w=140,
            thumb_h=160,
        )
        self._loader_thread.thumbnail_ready.connect(self._on_thumbnail_ready)
        self._loader_thread.progress.connect(self._on_loader_progress)
        self._loader_thread.loading_complete.connect(self._on_loading_complete)
        self._loader_thread.start()

    def _is_active_loader_sender(self) -> bool:
        """현재 활성 로더 스레드에서 온 시그널인지 확인 (잔여 스레드 혼선 방지)."""
        sender = self.sender()
        active = getattr(self, "_loader_thread", None)
        if active is None:
            # cleanup 직후 잔여 시그널은 무시
            return False
        if sender is not None and sender is not active:
            return False
        return True

    @pyqtSlot(int, QPixmap)
    def _on_thumbnail_ready(self, index: int, pixmap: QPixmap):
        if not self._is_active_loader_sender():
            return
        if index < len(self._thumbnails):
            self._thumbnails[index].set_pixmap(pixmap)
            self._loaded_indices.add(index)
            self._requested_indices.discard(index)
        self.loadingProgress.emit(int((len(self._loaded_indices) / max(1, self._total_pages)) * 100))

    @pyqtSlot(int)
    def _on_loader_progress(self, _value: int):
        if not self._is_active_loader_sender():
            return
        self.loadingProgress.emit(int((len(self._loaded_indices) / max(1, self._total_pages)) * 100))

    @pyqtSlot()
    def _on_loading_complete(self):
        if not self._is_active_loader_sender():
            return
        logger.debug("Thumbnail batch loading complete")
        unfinished = [
            index for index in self._active_batch_indices if index not in self._loaded_indices
        ]
        self._requested_indices.difference_update(self._active_batch_indices)
        self._pending_indices.update(unfinished)
        self._active_batch_indices = []
        if self._loader_thread:
            self._loader_thread.deleteLater()
        self._loader_thread = None
        self._request_visible_thumbnails()
        self._start_next_loader()

    def _on_columns_changed(self, value: int):
        self._columns = value
        self._arrange_grid()
        self._request_visible_thumbnails()

    def _on_scroll_changed(self, _value: int):
        self._request_visible_thumbnails()
