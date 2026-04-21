from __future__ import annotations

import logging
import os

from PyQt6.QtWidgets import QMessageBox

from ...core.i18n import tm
from ...core.worker_runtime.io import atomic_text_write
from ..main_window_config import AI_AVAILABLE
from ..widgets import ToastWidget, is_pdf_encrypted
from . import actions as base_actions
from .meta import build_summary_save_text

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
    if not atomic_text_write(save_path, save_text):
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

    history_key = base_actions._chat_history_key(path)
    conversation_history = list(self._chat_histories.get(history_key, []))
    self._record_chat_entry(path, "user", question)
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


def _clear_chat_history(self):
    path = self.sel_chat_pdf.get_path() if hasattr(self, "sel_chat_pdf") else None
    history_key = base_actions._chat_history_key(path)
    if history_key and history_key in self._chat_histories:
        del self._chat_histories[history_key]
        self._save_chat_histories()
    if history_key:
        try:
            from ...core.ai_service import AIService

            AIService.clear_chat_session(history_key)
        except Exception:
            logger.debug("Failed to clear cached chat session for %s", history_key, exc_info=True)
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
