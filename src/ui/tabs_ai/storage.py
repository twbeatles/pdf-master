import logging

from ...core.path_utils import make_chat_history_key, parse_chat_history_key
from ...core.settings import save_settings
from ..main_window_config import MAX_CHAT_HISTORY_ENTRIES, MAX_CHAT_HISTORY_PDFS

logger = logging.getLogger(__name__)


def _chat_history_key(path: object) -> str:
    return make_chat_history_key(path)


def _load_chat_histories(self):
    """저장된 채팅 히스토리를 로드하고 path+mtime key로 정규화한다."""
    raw = self.settings.get("chat_histories", {})
    if not isinstance(raw, dict):
        return {}
    cleaned = {}
    for path, entries in raw.items():
        base_path, mtime_ns = parse_chat_history_key(path)
        path_key = make_chat_history_key(base_path, mtime_ns) if mtime_ns is not None else _chat_history_key(path)
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
    """채팅 히스토리 크기를 제한한다."""
    for path, entries in list(self._chat_histories.items()):
        if not isinstance(entries, list) or not entries:
            del self._chat_histories[path]
            continue
        if len(entries) > MAX_CHAT_HISTORY_ENTRIES:
            self._chat_histories[path] = entries[-MAX_CHAT_HISTORY_ENTRIES:]
    if len(self._chat_histories) > MAX_CHAT_HISTORY_PDFS:
        self._chat_histories = dict(list(self._chat_histories.items())[-MAX_CHAT_HISTORY_PDFS:])


def _save_chat_histories(self):
    """채팅 히스토리를 저장한다."""
    self._trim_chat_histories()
    self.settings["chat_histories"] = self._chat_histories
    save_settings(self.settings)


def _record_chat_entry(self, path: str, role: str, content: str):
    """채팅 기록을 추가한다."""
    base_path, mtime_ns = parse_chat_history_key(path)
    path_key = make_chat_history_key(base_path, mtime_ns) if mtime_ns is not None else _chat_history_key(path)
    if not path_key or not content:
        return
    history = self._chat_histories.pop(path_key, [])
    history.append({"role": role, "content": content})
    self._chat_histories[path_key] = history
    self._trim_chat_histories()
