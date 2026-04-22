import logging
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...core.i18n import tm
from ...core.path_utils import normalize_path_key
from ...core.settings import KEYRING_AVAILABLE, get_api_key, save_settings, set_api_key
from ..main_window_config import AI_AVAILABLE, MAX_CHAT_HISTORY_ENTRIES, MAX_CHAT_HISTORY_PDFS
from ..widgets import FileSelectorWidget, ToastWidget, is_pdf_encrypted

logger = logging.getLogger(__name__)


def _chat_history_key(path: object) -> str:
    return normalize_path_key(path)


def _load_chat_histories(self):
    """??λ맂 梨꾪똿 ?덉뒪?좊━ 濡쒕뱶"""
    raw = self.settings.get("chat_histories", {})
    if not isinstance(raw, dict):
        return {}
    cleaned = {}
    for path, entries in raw.items():
        path_key = _chat_history_key(path)
        if not path_key or not isinstance(entries, list):
            continue
        cleaned_entries = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            role = entry.get("role")
            content = entry.get("content")
            if role in ("user", "assistant") and isinstance(content, str) and content:
                cleaned_entries.append({"role": role, "content": content})
        if cleaned_entries:
            merged = cleaned.setdefault(path_key, [])
            merged.extend(cleaned_entries)
            cleaned[path_key] = merged[-MAX_CHAT_HISTORY_ENTRIES:]
    if len(cleaned) > MAX_CHAT_HISTORY_PDFS:
        cleaned = dict(list(cleaned.items())[-MAX_CHAT_HISTORY_PDFS:])
    return cleaned


def _trim_chat_histories(self):
    """梨꾪똿 ?덉뒪?좊━ ?ш린 ?쒗븳"""
    for path, entries in list(self._chat_histories.items()):
        if not isinstance(entries, list) or not entries:
            del self._chat_histories[path]
            continue
        if len(entries) > MAX_CHAT_HISTORY_ENTRIES:
            self._chat_histories[path] = entries[-MAX_CHAT_HISTORY_ENTRIES:]
    if len(self._chat_histories) > MAX_CHAT_HISTORY_PDFS:
        self._chat_histories = dict(list(self._chat_histories.items())[-MAX_CHAT_HISTORY_PDFS:])


def _save_chat_histories(self):
    """梨꾪똿 ?덉뒪?좊━ ???"""
    self._trim_chat_histories()
    self.settings["chat_histories"] = self._chat_histories
    save_settings(self.settings)


def _record_chat_entry(self, path: str, role: str, content: str):
    """梨꾪똿 湲곕줉 異붽?"""
    path_key = _chat_history_key(path)
    if not path_key or not content:
        return
    history = self._chat_histories.pop(path_key, [])
    history.append({"role": role, "content": content})
    self._chat_histories[path_key] = history
    self._trim_chat_histories()
