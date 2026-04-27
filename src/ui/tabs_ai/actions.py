from __future__ import annotations

import logging
import os

from PyQt6.QtWidgets import QDialog, QMessageBox, QPushButton, QVBoxLayout

from ...core.i18n import tm
from ...core.worker_runtime.io import atomic_text_write
from ..main_window_config import AI_AVAILABLE
from ..widgets import ToastWidget, is_pdf_encrypted
from .meta import build_summary_save_text
from .storage import _chat_history_key

logger = logging.getLogger(__name__)


def _reset_ai_meta_label(label) -> None:
    if label is None:
        return
    clear = getattr(label, "clear", None)
    if callable(clear):
        clear()
    else:
        label.setText("")
    set_visible = getattr(label, "setVisible", None)
    if callable(set_visible):
        set_visible(False)


def _ensure_preview_ready(self, path):
    ensure_preview_access = getattr(self, "_ensure_preview_access", None)
    if callable(ensure_preview_access):
        result = ensure_preview_access(path)
        if result is None:
            self._update_preview(path)
            return True, None
        if isinstance(result, tuple):
            return bool(result[0]), result[1] if len(result) > 1 else None
        return bool(result), None

    self._update_preview(path)
    return True, None


def _save_summary_result(self):
    text = self.txt_summary_result.toPlainText()
    if not text:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_no_summary"))

    save_path, _selected_filter = self._choose_save_file(
        tm.get("dlg_save_summary"),
        "summary.txt",
        tm.get("file_filter_text"),
    )
    if not save_path:
        return None

    save_text = build_summary_save_text(text, getattr(self, "_summary_result_meta", {}))
    try:
        atomic_text_write(save_path, save_text)
    except Exception:
        logger.exception("Failed to save AI summary")
        return QMessageBox.warning(self, tm.get("error"), tm.get("msg_summary_save_failed"))

    ToastWidget(tm.get("msg_summary_saved"), toast_type="success", duration=2000).show_toast(self)
    return None


def action_ai_summarize(self):
    if not AI_AVAILABLE:
        return QMessageBox.critical(self, tm.get("error"), tm.get("msg_ai_unavailable"))

    path = self.sel_ai_pdf.get_path()
    api_key = self.txt_api_key.text().strip()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    if not api_key:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_enter_key"))
    if is_pdf_encrypted(path):
        return QMessageBox.warning(self, tm.get("warning"), tm.get("err_pdf_encrypted", os.path.basename(path)))

    style = self.cmb_summary_style.currentData() or "concise"
    lang = self.cmb_summary_lang.currentData() or "ko"
    max_pages = self.spn_max_pages.value()
    if max_pages == 0:
        max_pages = None

    self.txt_summary_result.clear()
    self.txt_summary_result.setPlaceholderText(tm.get("msg_ai_working"))
    self._summary_result_meta = {}
    _reset_ai_meta_label(getattr(self, "lbl_summary_meta", None))

    self._ai_worker_mode = True
    self.run_worker(
        "ai_summarize",
        file_path=path,
        api_key=api_key,
        language=lang,
        style=style,
        max_pages=max_pages,
    )
    return None


def _ask_ai_question(self):
    if not AI_AVAILABLE:
        return QMessageBox.critical(self, tm.get("error"), tm.get("msg_ai_unavailable"))

    path = self.sel_chat_pdf.get_path()
    api_key = self.txt_api_key.text().strip()
    question = self.txt_ai_question.text().strip()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    if not api_key:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_enter_key"))
    if is_pdf_encrypted(path):
        return QMessageBox.warning(self, tm.get("warning"), tm.get("err_pdf_encrypted", os.path.basename(path)))
    if not question:
        return None

    history_key = _chat_history_key(path)
    conversation_history = list(self._chat_histories.get(history_key, []))
    self._record_chat_entry(history_key, "user", question)
    self._save_chat_histories()

    self.txt_chat_history.append(f"<b>{tm.get('chat_user_prefix')}</b> {question}")
    self.txt_chat_history.append(f"<i>{tm.get('msg_ai_thinking')}</i>")
    self.txt_ai_question.clear()
    self._chat_result_meta = {}
    _reset_ai_meta_label(getattr(self, "lbl_chat_meta", None))

    self._chat_worker_mode = True
    self._chat_pending_path = history_key
    self.run_worker(
        "ai_ask_question",
        file_path=path,
        api_key=api_key,
        question=question,
        conversation_history=conversation_history,
    )
    return None


def _on_chat_pdf_changed(self, path: str):
    self._update_preview(path)
    self._load_chat_history_for_path(path)
    self._chat_result_meta = {}
    _reset_ai_meta_label(getattr(self, "lbl_chat_meta", None))


def _load_chat_history_for_path(self, path: str):
    if not hasattr(self, "txt_chat_history"):
        return
    self.txt_chat_history.clear()
    if not path:
        return
    history = self._chat_histories.get(_chat_history_key(path), [])
    for entry in history:
        role = entry.get("role")
        content = entry.get("content", "")
        if role == "user":
            self.txt_chat_history.append(f"<b>{tm.get('chat_user_prefix')}</b> {content}")
        elif role == "assistant":
            self.txt_chat_history.append(f"<b>{tm.get('chat_assistant_prefix')}</b> {content}")
            self.txt_chat_history.append("<hr>")


def _clear_chat_history(self):
    path = self.sel_chat_pdf.get_path() if hasattr(self, "sel_chat_pdf") else None
    history_key = _chat_history_key(path)
    if history_key and history_key in self._chat_histories:
        del self._chat_histories[history_key]
        self._save_chat_histories()
    if path:
        try:
            from ...core.ai_service import AIService

            AIService.clear_chat_session(path)
        except Exception:
            logger.debug("Failed to clear cached chat session for %s", path, exc_info=True)
    self.txt_chat_history.clear()
    self._chat_result_meta = {}
    _reset_ai_meta_label(getattr(self, "lbl_chat_meta", None))
    ToastWidget(tm.get("msg_chat_cleared"), toast_type="info", duration=2000).show_toast(self)


def _extract_keywords(self):
    if not AI_AVAILABLE:
        return QMessageBox.critical(self, tm.get("error"), tm.get("msg_ai_unavailable"))

    path = self.sel_kw_pdf.get_path()
    api_key = self.txt_api_key.text().strip()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    if not api_key:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_enter_key"))
    if is_pdf_encrypted(path):
        return QMessageBox.warning(self, tm.get("warning"), tm.get("err_pdf_encrypted", os.path.basename(path)))

    max_keywords = self.spn_max_keywords.value()
    lang = self.cmb_summary_lang.currentData() or "ko"
    self.lbl_keywords_result.setText(tm.get("msg_ai_thinking"))
    self._keywords_result_meta = {}
    _reset_ai_meta_label(getattr(self, "lbl_keywords_meta", None))

    self._keyword_worker_mode = True
    self.run_worker(
        "ai_extract_keywords",
        file_path=path,
        api_key=api_key,
        max_keywords=max_keywords,
        language=lang,
    )
    return None


def _show_thumbnail_grid(self):
    path = self.sel_thumb_pdf.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))

    from ..thumbnail_grid import ThumbnailGridWidget

    dialog = QDialog(self)
    dialog.setWindowTitle(tm.get("title_thumb_grid").format(os.path.basename(path)))
    dialog.resize(800, 600)

    layout = QVBoxLayout(dialog)
    thumbnail_grid = ThumbnailGridWidget()
    thumbnail_grid.pageSelected.connect(
        lambda pg, current_path=path: self._on_grid_page_selected(pg, current_path, dialog)
    )
    layout.addWidget(thumbnail_grid)

    btn_close = QPushButton(tm.get("close"))
    btn_close.clicked.connect(dialog.accept)
    layout.addWidget(btn_close)

    ready, password = _ensure_preview_ready(self, path)
    if ready:
        thumbnail_grid.load_pdf(path, password=password)
        if getattr(self, "_current_preview_path", "") and os.path.abspath(self._current_preview_path) == os.path.abspath(path):
            thumbnail_grid.set_active_page(getattr(self, "_current_preview_page", 0), emit_signal=False)
    else:
        thumbnail_grid.show_status_message(self.preview_label.text())

    dialog.exec()
    return None


def _on_grid_page_selected(self, page_index: int, path: str, dialog: QDialog):
    ready, _password = _ensure_preview_ready(self, path)
    if not ready:
        return
    self._current_preview_page = page_index
    self._render_preview_page()
    self.status_label.setText(tm.get("status_page_sel").format(page_index + 1))
