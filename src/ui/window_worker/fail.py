"""on_fail / on_cancelled 본문 헬퍼."""
from __future__ import annotations

import logging
from typing import Any

from ...core.i18n import tm
from .helpers import _chat_history_key_for
from .results import _clear_meta_label, _replace_last_chat_block

logger = logging.getLogger(__name__)


def clear_ai_worker_flags_on_cancel(host: Any) -> None:
    if hasattr(host, "_ai_worker_mode"):
        host._ai_worker_mode = False
        host._summary_partial_text = ""
        host._summary_result_meta = {}
        _clear_meta_label(getattr(host, "lbl_summary_meta", None))
    if hasattr(host, "_keyword_worker_mode"):
        host._keyword_worker_mode = False
        host._keywords_result_meta = {}
        _clear_meta_label(getattr(host, "lbl_keywords_meta", None))
    if hasattr(host, "_chat_worker_mode"):
        host._chat_worker_mode = False
        host._chat_pending_path = None
        host._chat_partial_text = ""
        host._chat_result_meta = {}
        _clear_meta_label(getattr(host, "lbl_chat_meta", None))


def clear_ai_worker_flags_on_fail(host: Any) -> None:
    if hasattr(host, "_ai_worker_mode"):
        host._ai_worker_mode = False
        host._summary_partial_text = ""
        host._summary_result_meta = {}
        _clear_meta_label(getattr(host, "lbl_summary_meta", None))
    if hasattr(host, "_keyword_worker_mode"):
        host._keyword_worker_mode = False
        host._keywords_result_meta = {}
        _clear_meta_label(getattr(host, "lbl_keywords_meta", None))


def rollback_chat_on_fail(host: Any, msg: str) -> None:
    if not (hasattr(host, "_chat_worker_mode") and host._chat_worker_mode):
        return
    host._chat_worker_mode = False
    raw_pending_path = host._chat_pending_path
    pending_path = _chat_history_key_for(raw_pending_path)
    host._chat_pending_path = None
    host._chat_partial_text = ""
    host._chat_result_meta = {}
    _clear_meta_label(getattr(host, "lbl_chat_meta", None))
    history_keys = [key for key in (pending_path, raw_pending_path) if isinstance(key, str) and key]
    seen_history_keys: set[str] = set()
    for history_key in history_keys:
        if history_key in seen_history_keys or history_key not in host._chat_histories:
            continue
        seen_history_keys.add(history_key)
        history = host._chat_histories.get(history_key, [])
        if history and history[-1].get("role") == "user":
            history.pop()
            if not history:
                del host._chat_histories[history_key]
            host._save_chat_histories()
    if hasattr(host, "txt_chat_history"):
        _replace_last_chat_block(host.txt_chat_history, f"<span style='color:#ef4444'>❌ {msg}</span>")


def clear_textbox_post_flags(host: Any, *, context: str) -> None:
    clear_tb = getattr(host, "_clear_textbox_post_flags", None)
    if callable(clear_tb):
        try:
            clear_tb()
        except Exception:
            logger.debug("clear textbox flags on %s failed", context, exc_info=True)
