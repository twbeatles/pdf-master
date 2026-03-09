import logging
import os

import fitz
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
from ...core.constants import RECENT_FILES_MAX
from ...core.settings import save_settings
from ..widgets import FileSelectorWidget
from ..zoomable_preview import ZoomablePreviewWidget

logger = logging.getLogger(__name__)

def _update_preview(self, path):
    if not path or not os.path.exists(path):
        self.preview_label.setText(tm.get("preview_default"))
        self._reset_preview_state()
        return

    self._add_to_recent_files(path)

    try:
        self._current_preview_password = None
        doc, locked_state = self._ensure_preview_document(path)
        if not doc:
            if locked_state == "error":
                raise RuntimeError(tm.get("err_pdf_corrupted"))
            if locked_state == "wrong":
                self.preview_label.setText(tm.get("preview_password_wrong"))
            else:
                self.preview_label.setText(tm.get("preview_encrypted"))
            self._reset_preview_state(close_doc=False)
            return

        size_kb = os.path.getsize(path) / 1024
        meta = doc.metadata
        title = meta.get("title", "-") if meta else "-"
        author = meta.get("author", "-") if meta else "-"
        info = tm.get(
            "preview_info",
            os.path.basename(path),
            len(doc),
            size_kb,
            title or "-",
            author or "-",
        )
        self.preview_label.setText(info)

        self._current_preview_path = path
        self._preview_total_pages = len(doc)
        self._current_preview_page = 0
        self.page_counter.setText(f"1 / {len(doc)}")
        self._set_preview_navigation_enabled(True)
        if len(doc) > 0:
            self._render_preview_page()
    except Exception as e:
        self.preview_label.setText(tm.get("preview_error", str(e)))
        self._reset_preview_state()

def _add_to_recent_files(self, path):
    recent = self.settings.get("recent_files", [])
    if path in recent:
        recent.remove(path)
    recent.insert(0, path)
    self.settings["recent_files"] = recent[:RECENT_FILES_MAX]
    if hasattr(self, "_schedule_settings_save"):
        self._schedule_settings_save()
    else:
        save_settings(self.settings)
