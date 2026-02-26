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
from ...core.settings import save_settings
from ..widgets import FileSelectorWidget
from ..zoomable_preview import ZoomablePreviewWidget

logger = logging.getLogger(__name__)

def _print_current_preview(self):
    if hasattr(self, "_current_preview_path") and self._current_preview_path:
        self._print_pdf(self._current_preview_path)
    else:
        QMessageBox.warning(self, tm.get("print_title"), tm.get("print_no_file"))

def _print_pdf(self, path):
    from PyQt6.QtPrintSupport import QPrinter, QPrintDialog

    if not path or not os.path.exists(path):
        QMessageBox.warning(self, tm.get("print_title"), tm.get("print_no_file"))
        return

    try:
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)

        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            if sys.platform == "win32":
                os.startfile(path, "print")
            else:
                subprocess.run(["lpr", path])
            toast = ToastWidget(tm.get("print_sent"), toast_type="success", duration=2000)
            toast.show_toast(self)
    except Exception as e:
        QMessageBox.warning(self, tm.get("print_error_title"), tm.get("print_error_msg", str(e)))

def _prev_preview_page(self):
    if self._current_preview_page > 0:
        self._current_preview_page -= 1
        self._render_preview_page()

def _next_preview_page(self):
    if hasattr(self, "_preview_total_pages") and self._current_preview_page < self._preview_total_pages - 1:
        self._current_preview_page += 1
        self._render_preview_page()

def _render_preview_page(self):
    if not hasattr(self, "_current_preview_path") or not self._current_preview_path:
        return
    with PerfTimer("ui.preview.render", logger=logger, extra={"page": self._current_preview_page}):
        doc, locked_state = self._ensure_preview_document(self._current_preview_path)
        if not doc:
            if locked_state == "wrong":
                self.preview_label.setText(tm.get("preview_password_wrong"))
            elif locked_state == "cancelled":
                self.preview_label.setText(tm.get("preview_encrypted"))
            self._reset_preview_state(close_doc=False)
            return

        if self._current_preview_page < 0 or self._current_preview_page >= len(doc):
            return

        preview_size = self.preview_image.size()
        target_w = max(280, preview_size.width() - 20)
        target_h = max(400, preview_size.height() - 20)
        zoom_bucket = int(self._PREVIEW_RENDER_ZOOM * 100)
        key = self._make_preview_cache_key(
            self._current_preview_path,
            self._current_preview_page,
            target_w,
            target_h,
            zoom_bucket,
        )

        pixmap = self._get_cached_preview_pixmap(key)
        if pixmap is None:
            page = doc[self._current_preview_page]
            pix = page.get_pixmap(matrix=fitz.Matrix(self._PREVIEW_RENDER_ZOOM, self._PREVIEW_RENDER_ZOOM))
            img_data = bytes(pix.samples)
            fmt = QImage.Format.Format_RGBA8888 if pix.alpha else QImage.Format.Format_RGB888
            img = QImage(img_data, pix.width, pix.height, pix.stride, fmt)
            base_pixmap = QPixmap.fromImage(img.copy())
            pixmap = base_pixmap.scaled(
                target_w,
                target_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._put_cached_preview_pixmap(key, pixmap)

        self.preview_image.setPixmap(pixmap)
        self.page_counter.setText(f"{self._current_preview_page + 1} / {self._preview_total_pages}")

def _on_list_item_clicked(self, item):
    path = item.data(Qt.ItemDataRole.UserRole)
    self._update_preview(path)
