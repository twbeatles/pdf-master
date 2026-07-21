from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from datetime import datetime

from ..constants import MAX_CHAT_HISTORY_ENTRIES, MAX_CHAT_HISTORY_PDFS
from ..optional_deps import KEYRING_AVAILABLE, keyring
from ..path_utils import make_chat_history_key, normalize_path_key, parse_chat_history_key
from .config import KEYRING_SERVICE, KEYRING_USERNAME, SETTINGS_FILE, logger

def _normalize_recent_files(value) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        path_key = normalize_path_key(item)
        if not path_key or path_key in seen or not os.path.exists(path_key):
            continue
        seen.add(path_key)
        normalized.append(path_key)
    return normalized

def _normalize_chat_histories(value) -> dict:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, list[dict[str, str]]] = {}
    for raw_path, raw_entries in value.items():
        path_key, version_mtime_ns = parse_chat_history_key(raw_path)
        if not path_key or not isinstance(raw_entries, list) or not os.path.exists(path_key):
            continue
        history_key = (
            make_chat_history_key(path_key, version_mtime_ns)
            if version_mtime_ns is not None
            else make_chat_history_key(path_key)
        )
        if not history_key:
            continue
        cleaned_entries = normalized.setdefault(history_key, [])
        for entry in raw_entries:
            if not isinstance(entry, dict):
                continue
            role = entry.get("role")
            content = entry.get("content")
            if role in ("user", "assistant") and isinstance(content, str) and content:
                cleaned_entries.append({"role": role, "content": content})

    trimmed: dict[str, list[dict[str, str]]] = {}
    for path_key, entries in normalized.items():
        if not entries:
            continue
        trimmed[path_key] = entries[-MAX_CHAT_HISTORY_ENTRIES:]

    if len(trimmed) > MAX_CHAT_HISTORY_PDFS:
        trimmed = dict(list(trimmed.items())[-MAX_CHAT_HISTORY_PDFS:])
    return trimmed

def _normalize_splitter_sizes(value) -> list[int] | None:
    if value is None:
        return None
    if not isinstance(value, (list, tuple)):
        return None

    normalized: list[int] = []
    for item in value:
        if not isinstance(item, (int, float)):
            return None
        size = int(item)
        if size < 0:
            return None
        normalized.append(size)

    return normalized or None

def _normalize_theme(value) -> str:
    return value if value in {"dark", "light"} else "dark"

def _normalize_language(value) -> str:
    return value if value in {"auto", "ko", "en"} else "auto"

def _normalize_window_geometry(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value
    return None

def _normalize_last_output_dir(value) -> str:
    return value if isinstance(value, str) else ""

def _normalize_bool(value, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off", ""}:
            return False
    return bool(default)
