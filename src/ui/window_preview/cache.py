import logging
import os
from collections import OrderedDict

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QPixmap
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.i18n import tm
from ...core.settings import save_settings
from ..widgets import FileSelectorWidget
from ..zoomable_preview import ZoomablePreviewWidget

logger = logging.getLogger(__name__)

def _ensure_preview_cache(self):
    if not hasattr(self, "_preview_pixmap_cache"):
        self._preview_pixmap_cache = OrderedDict()
        self._preview_pixmap_cache_bytes = 0
    if not hasattr(self, "_PREVIEW_CACHE_MAX_BYTES"):
        # Keep the preview cache bounded even if the host did not preconfigure it.
        self._PREVIEW_CACHE_MAX_BYTES = 64 * 1024 * 1024

def _make_preview_cache_key(self, path: str, page_index: int, target_w: int, target_h: int, zoom_bucket: int) -> tuple:
    abs_path = os.path.abspath(path)
    try:
        mtime_ns = os.stat(abs_path).st_mtime_ns
    except OSError:
        mtime_ns = 0
    return abs_path, mtime_ns, page_index, zoom_bucket, target_w, target_h

def _get_cached_preview_pixmap(self, key: tuple) -> QPixmap | None:
    self._ensure_preview_cache()
    item = self._preview_pixmap_cache.get(key)
    if item is None:
        return None
    pixmap, est_bytes = item
    self._preview_pixmap_cache.move_to_end(key)
    logger.debug("Preview cache hit (%s bytes)", est_bytes)
    return pixmap

def _put_cached_preview_pixmap(self, key: tuple, pixmap: QPixmap):
    self._ensure_preview_cache()
    est_bytes = max(1, pixmap.width()) * max(1, pixmap.height()) * 4
    old = self._preview_pixmap_cache.pop(key, None)
    if old:
        self._preview_pixmap_cache_bytes -= old[1]
    self._preview_pixmap_cache[key] = (pixmap, est_bytes)
    self._preview_pixmap_cache_bytes += est_bytes
    while self._preview_pixmap_cache_bytes > self._PREVIEW_CACHE_MAX_BYTES and self._preview_pixmap_cache:
        _, (_, removed_bytes) = self._preview_pixmap_cache.popitem(last=False)
        self._preview_pixmap_cache_bytes -= removed_bytes
