import logging
import os
import subprocess
import sys
from collections import OrderedDict

import fitz
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ..core.constants import RECENT_FILES_MAX
from ..core.i18n import tm
from ..core.perf import PerfTimer
from ..core.settings import save_settings
from .widgets import ToastWidget

logger = logging.getLogger(__name__)


class MainWindowPreviewMixin:
    _PREVIEW_CACHE_MAX_BYTES = 128 * 1024 * 1024
    _PREVIEW_RENDER_ZOOM = 1.5

    def _create_preview_panel(self):
        panel = QGroupBox(tm.get("preview_title"))
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        self._ensure_preview_cache()

        self.preview_label = QLabel(tm.get("preview_default"))
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("color: #666; padding: 10px; font-size: 12px;")
        self.preview_label.setWordWrap(True)
        self.preview_label.setMaximumHeight(120)
        layout.addWidget(self.preview_label)

        self.preview_image = QLabel()
        self.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image.setMinimumSize(250, 350)
        self.preview_image.setStyleSheet("background: #0f0f23; border-radius: 8px; border: 1px solid #333;")
        self.preview_image.setSizePolicy(
            self.preview_image.sizePolicy().horizontalPolicy(),
            self.preview_image.sizePolicy().verticalPolicy(),
        )
        layout.addWidget(self.preview_image, 1)

        nav_layout = QHBoxLayout()
        self.btn_prev_page = QPushButton(tm.get("prev_page"))
        self.btn_prev_page.setObjectName("navBtn")
        self.btn_prev_page.setFixedSize(80, 30)
        self.btn_prev_page.clicked.connect(self._prev_preview_page)
        nav_layout.addWidget(self.btn_prev_page)

        self.page_counter = QLabel("1 / 1")
        self.page_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_counter.setStyleSheet("font-weight: bold; min-width: 60px; color: #eaeaea;")
        nav_layout.addWidget(self.page_counter)

        self.btn_next_page = QPushButton(tm.get("next_page"))
        self.btn_next_page.setObjectName("navBtn")
        self.btn_next_page.setFixedSize(80, 30)
        self.btn_next_page.clicked.connect(self._next_preview_page)
        nav_layout.addWidget(self.btn_next_page)

        self.btn_print_preview = QPushButton(tm.get("btn_print_preview"))
        self.btn_print_preview.setObjectName("secondaryBtn")
        self.btn_print_preview.setFixedSize(70, 30)
        self.btn_print_preview.setToolTip(tm.get("tooltip_print_preview"))
        self.btn_print_preview.clicked.connect(self._print_current_preview)
        nav_layout.addWidget(self.btn_print_preview)

        layout.addLayout(nav_layout)
        self._set_preview_navigation_enabled(False)
        return panel

    def _ensure_preview_cache(self):
        if not hasattr(self, "_preview_pixmap_cache"):
            self._preview_pixmap_cache = OrderedDict()
            self._preview_pixmap_cache_bytes = 0

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

    def _close_preview_document(self):
        doc = getattr(self, "_current_preview_doc", None)
        if doc:
            try:
                doc.close()
            except Exception:
                logger.debug("Failed to close preview document", exc_info=True)
        self._current_preview_doc = None

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

    def _set_preview_navigation_enabled(self, enabled: bool):
        self.btn_prev_page.setEnabled(enabled)
        self.btn_next_page.setEnabled(enabled)
        self.btn_print_preview.setEnabled(enabled)
        if not enabled:
            self.page_counter.setText("0 / 0")

    def _reset_preview_state(self, close_doc: bool = True):
        self.preview_image.clear()
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
            info = f"""{os.path.basename(path)}

페이지: {len(doc)}p  크기: {size_kb:.1f}KB
제목: {title or '-'}
작성자: {author or '-'}"""
            self.preview_label.setText(info)

            self._current_preview_path = path
            self._preview_total_pages = len(doc)
            self._current_preview_page = 0
            self.page_counter.setText(f"1 / {len(doc)}")
            self._set_preview_navigation_enabled(True)
            if len(doc) > 0:
                self._render_preview_page()
        except Exception as e:
            self.preview_label.setText(f"미리보기 오류: {e}")
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
