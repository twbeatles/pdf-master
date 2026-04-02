import logging
import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPainter, QPixmap
from PyQt6.QtPrintSupport import QAbstractPrintDialog, QPrinter, QPrintDialog
from PyQt6.QtWidgets import QMessageBox

from ...core.optional_deps import fitz
from ...core.i18n import tm
from ...core.perf import PerfTimer
from ..widgets import ToastWidget

logger = logging.getLogger(__name__)


def _collect_print_page_indices(printer, total_pages: int, current_page_index: int) -> list[int]:
    if total_pages <= 0:
        return []

    try:
        print_range = printer.printRange()
    except Exception:
        print_range = None

    try:
        if print_range == QPrinter.PrintRange.CurrentPage:
            return [max(0, min(total_pages - 1, current_page_index))]

        if print_range == QPrinter.PrintRange.PageRange:
            indices: list[int] = []
            try:
                page_ranges = printer.pageRanges()
            except Exception:
                page_ranges = None

            if page_ranges is not None and hasattr(page_ranges, "isEmpty") and not page_ranges.isEmpty():
                for page_range in page_ranges.toRangeList():
                    start = max(1, int(page_range.from_()))
                    end = min(total_pages, int(page_range.to()))
                    indices.extend(range(start - 1, end))
                if indices:
                    return indices

            start = max(1, int(getattr(printer, "fromPage", lambda: 1)()))
            end = min(total_pages, int(getattr(printer, "toPage", lambda: total_pages)()))
            return list(range(start - 1, end))
    except Exception:
        logger.debug("Falling back to printing all pages", exc_info=True)

    return list(range(total_pages))


def _render_pdf_page_to_printer(printer, painter: QPainter, page) -> None:
    from PyQt6.QtCore import QRect

    target_rect = printer.pageRect(QPrinter.Unit.DevicePixel)
    if hasattr(target_rect, "toRect"):
        target_rect = target_rect.toRect()
    if target_rect.width() <= 0 or target_rect.height() <= 0:
        raise RuntimeError("Printer page rect is invalid")

    render_scale = min(
        target_rect.width() / max(float(page.rect.width), 1.0),
        target_rect.height() / max(float(page.rect.height), 1.0),
    )
    render_scale = max(1.0, render_scale)

    pix = page.get_pixmap(matrix=fitz.Matrix(render_scale, render_scale), alpha=False)
    image_format = QImage.Format.Format_RGBA8888 if pix.alpha else QImage.Format.Format_RGB888
    image = QImage(bytes(pix.samples), pix.width, pix.height, pix.stride, image_format).copy()
    scaled = image.scaled(
        target_rect.size(),
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    draw_rect = QRect(
        target_rect.x() + max(0, (target_rect.width() - scaled.width()) // 2),
        target_rect.y() + max(0, (target_rect.height() - scaled.height()) // 2),
        scaled.width(),
        scaled.height(),
    )
    painter.drawImage(draw_rect, scaled)

def _print_current_preview(self):
    if hasattr(self, "_current_preview_path") and self._current_preview_path:
        self._print_pdf(self._current_preview_path)
    else:
        QMessageBox.warning(self, tm.get("print_title"), tm.get("print_no_file"))

def _print_pdf(self, path):
    if not path or not os.path.exists(path):
        QMessageBox.warning(self, tm.get("print_title"), tm.get("print_no_file"))
        return

    ready, _password = self._ensure_preview_access(path)
    if not ready:
        QMessageBox.warning(self, tm.get("print_title"), self.preview_label.text())
        return

    try:
        doc = getattr(self, "_current_preview_doc", None)
        if not doc:
            raise RuntimeError(tm.get("print_no_file"))

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setDocName(os.path.basename(path))
        dialog = QPrintDialog(printer, self)
        dialog.setMinMax(1, len(doc))
        dialog.setOption(QAbstractPrintDialog.PrintDialogOption.PrintPageRange, True)
        dialog.setOption(QAbstractPrintDialog.PrintDialogOption.PrintCurrentPage, True)

        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            page_indices = _collect_print_page_indices(
                printer,
                len(doc),
                getattr(self, "_current_preview_page", 0),
            )
            if not page_indices:
                raise RuntimeError(tm.get("print_no_file"))

            painter = QPainter()
            if not painter.begin(printer):
                raise RuntimeError("Failed to initialize printer painter")
            try:
                for render_idx, page_index in enumerate(page_indices):
                    if render_idx > 0 and not printer.newPage():
                        raise RuntimeError("Failed to start a new printer page")
                    _render_pdf_page_to_printer(printer, painter, doc[page_index])
            finally:
                painter.end()

            toast = ToastWidget(tm.get("print_completed"), toast_type="success", duration=2000)
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

def _on_preview_page_requested(self, page_index: int):
    if page_index == getattr(self, "_current_preview_page", -1):
        return
    if page_index < 0 or page_index >= getattr(self, "_preview_total_pages", 0):
        return
    self._current_preview_page = page_index
    self._render_preview_page()

def _schedule_preview_rerender(self):
    if not getattr(self, "_current_preview_path", ""):
        return
    if getattr(self, "_preview_total_pages", 0) <= 0:
        return
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

        preview_size = self.preview_image.display_size()
        target_w = max(280, preview_size.width() - 20)
        target_h = max(400, preview_size.height() - 20)
        render_zoom = float(getattr(self, "_PREVIEW_RENDER_ZOOM", 2.0))
        zoom_bucket = int(render_zoom * 100)
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
            pix = page.get_pixmap(matrix=fitz.Matrix(render_zoom, render_zoom))
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

        self.preview_image.set_preview_pixmap(
            pixmap,
            current_page=self._current_preview_page,
            total_pages=self._preview_total_pages,
            preserve_view=True,
        )
        if hasattr(self, "_sync_rotate_thumbnail_with_preview"):
            self._sync_rotate_thumbnail_with_preview()

def _on_list_item_clicked(self, item):
    path = item.data(Qt.ItemDataRole.UserRole)
    self._update_preview(path)
