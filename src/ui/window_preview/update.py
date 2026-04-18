import logging
import os

from PyQt6.QtPdf import QPdfDocument

from ...core.constants import RECENT_FILES_MAX
from ...core.i18n import tm
from ...core.path_utils import normalize_path_key
from ...core.settings import save_settings

logger = logging.getLogger(__name__)


def _preview_metadata(doc: QPdfDocument, field) -> str:
    try:
        value = doc.metaData(field)
    except Exception:
        return "-"
    return value if isinstance(value, str) and value else "-"


def _update_preview(self, path, restore_state=None):
    path_key = normalize_path_key(path)
    if not path_key or not os.path.exists(path_key):
        self.preview_label.setText(tm.get("preview_default"))
        self._reset_preview_state()
        return

    try:
        doc, locked_state = self._ensure_preview_document(path_key)
        if not doc:
            if locked_state == "error":
                raise RuntimeError(tm.get("err_pdf_corrupted"))
            if locked_state == "wrong":
                self.preview_label.setText(tm.get("preview_password_wrong"))
            else:
                self.preview_label.setText(tm.get("preview_encrypted"))
            self._reset_preview_state(close_doc=False)
            return

        size_kb = os.path.getsize(path_key) / 1024
        title = _preview_metadata(doc, QPdfDocument.MetaDataField.Title)
        author = _preview_metadata(doc, QPdfDocument.MetaDataField.Author)
        total_pages = doc.pageCount()
        info = tm.get(
            "preview_info",
            os.path.basename(path_key),
            total_pages,
            size_kb,
            title,
            author,
        )
        self.preview_label.setText(info)

        self._current_preview_path = path_key
        self._preview_total_pages = total_pages
        self._current_preview_page = 0
        self._set_preview_navigation_enabled(total_pages > 0)

        if restore_state and hasattr(self, "preview_image"):
            self.preview_image.restore_view_state(restore_state)
            self._current_preview_page = int(restore_state.get("page", 0) or 0)
        elif total_pages > 0:
            self.preview_image.set_page_state(0, total_pages)
            self.preview_image.go_to_page(0, emit_signal=False)

        if hasattr(self, "_sync_rotate_thumbnail_with_preview"):
            self._sync_rotate_thumbnail_with_preview()
        self._add_to_recent_files(path_key)
    except Exception as exc:
        self.preview_label.setText(tm.get("preview_error", str(exc)))
        self._reset_preview_state()


def _add_to_recent_files(self, path):
    path_key = normalize_path_key(path)
    if not path_key or not os.path.exists(path_key):
        return
    recent = [item for item in self.settings.get("recent_files", []) if isinstance(item, str)]
    if path_key in recent:
        recent.remove(path_key)
    recent.insert(0, path_key)
    self.settings["recent_files"] = recent[:RECENT_FILES_MAX]
    if hasattr(self, "_schedule_settings_save"):
        self._schedule_settings_save()
    else:
        save_settings(self.settings)
