import logging
import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QPixmap
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QInputDialog,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.optional_deps import fitz
from ...core.i18n import tm
from ...core.settings import save_settings
from ..widgets import FileSelectorWidget
from ..zoomable_preview import ZoomablePreviewWidget

logger = logging.getLogger(__name__)

def _close_preview_document(self):
    doc = getattr(self, "_current_preview_doc", None)
    if doc:
        try:
            doc.close()
        except Exception:
            logger.debug("Failed to close preview document", exc_info=True)
    self._current_preview_doc = None

def _ensure_preview_document(self, path: str):
    abs_path = os.path.abspath(path)
    current_path = os.path.abspath(getattr(self, "_current_preview_path", "")) if getattr(self, "_current_preview_path", "") else ""
    doc = getattr(self, "_current_preview_doc", None)
    if doc and current_path == abs_path:
        try:
            _ = len(doc)
            return doc, None
        except Exception:
            logger.debug("Cached preview doc invalid, reopening", exc_info=True)
            self._close_preview_document()

    self._close_preview_document()
    new_doc, locked_state = self._open_preview_document(path)
    if new_doc:
        self._current_preview_doc = new_doc
        self._current_preview_path = path
    return new_doc, locked_state

def _reset_preview_state(self, close_doc: bool = True):
    self.preview_image.clear_display()
    if close_doc:
        self._close_preview_document()
    self._current_preview_path = ""
    self._preview_total_pages = 0
    self._current_preview_page = 0
    self._current_preview_password = None
    self._set_preview_navigation_enabled(False)

def _prompt_pdf_password(self, path: str):
    password, ok = QInputDialog.getText(
        self,
        tm.get("password_title"),
        tm.get("password_msg").format(os.path.basename(path)),
        QLineEdit.EchoMode.Password,
    )
    if not ok or not password:
        return None
    return password

def _open_preview_document(self, path: str):
    try:
        doc = fitz.open(path)
    except Exception:
        return None, "error"

    if not doc.is_encrypted:
        return doc, None

    doc.close()
    while True:
        password = self._prompt_pdf_password(path)
        if not password:
            self._current_preview_password = None
            return None, "cancelled"
        doc = fitz.open(path)
        if doc.authenticate(password):
            self._current_preview_password = password
            return doc, None
        doc.close()
        retry = QMessageBox.question(
            self,
            tm.get("password_title"),
            tm.get("password_retry"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if retry != QMessageBox.StandardButton.Yes:
            self._current_preview_password = None
            return None, "wrong"
