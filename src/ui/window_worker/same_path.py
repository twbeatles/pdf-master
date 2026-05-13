from __future__ import annotations

import os

from .helpers import _is_same_path_pdf_mutation, _normalize_abs_path


def _prepare_preview_for_same_path_output(self, mode, kwargs):
    self._same_path_preview_restore = None
    if not _is_same_path_pdf_mutation(mode, kwargs):
        return

    preview_path = _normalize_abs_path(getattr(self, "_current_preview_path", ""))
    input_path = _normalize_abs_path(kwargs.get("file_path"))
    preview_doc = getattr(self, "_current_preview_doc", None)
    if not preview_doc or not preview_path or preview_path != input_path:
        return

    self._same_path_preview_restore = {
        "path": kwargs.get("file_path"),
        "page": getattr(self, "_current_preview_page", 0),
        "password": getattr(self, "_current_preview_password", None),
        "view_state": self.preview_image.capture_view_state() if hasattr(self, "preview_image") else None,
    }
    self._close_preview_document()

def _restore_preview_after_same_path_output(self):
    restore = getattr(self, "_same_path_preview_restore", None)
    self._same_path_preview_restore = None
    if not restore:
        return

    path = restore.get("path")
    if not isinstance(path, str) or not path or not os.path.exists(path):
        return

    restore_page = restore.get("page", 0)
    restore_password = restore.get("password")
    restore_view_state = restore.get("view_state")
    self._preview_password_hint = restore_password if isinstance(restore_password, str) else None
    try:
        if restore_view_state is not None:
            self._update_preview(path, restore_state=restore_view_state)
        else:
            self._update_preview(path)
        total_pages = int(getattr(self, "_preview_total_pages", 0) or 0)
        if total_pages <= 0:
            return
        try:
            page_index = int(restore_page)
        except (TypeError, ValueError):
            page_index = 0
        page_index = max(0, min(total_pages - 1, page_index))
        self._current_preview_page = page_index
        self._render_preview_page()
    finally:
        self._preview_password_hint = None
