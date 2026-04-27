from __future__ import annotations

import os


CHAT_HISTORY_KEY_PREFIX = "v2:"


def normalize_path_key(path: object) -> str:
    if not isinstance(path, str):
        return ""
    stripped = path.strip()
    if not stripped:
        return ""
    return os.path.normcase(os.path.abspath(stripped))


def path_mtime_ns(path: object) -> int:
    path_key = normalize_path_key(path)
    if not path_key:
        return 0
    try:
        return int(os.stat(path_key).st_mtime_ns)
    except OSError:
        return 0


def make_chat_history_key(path: object, mtime_ns: int | None = None) -> str:
    path_key = normalize_path_key(path)
    if not path_key:
        return ""
    resolved_mtime_ns = path_mtime_ns(path_key) if mtime_ns is None else int(mtime_ns)
    return f"{CHAT_HISTORY_KEY_PREFIX}{resolved_mtime_ns}:{path_key}"


def parse_chat_history_key(key: object) -> tuple[str, int | None]:
    if not isinstance(key, str):
        return "", None
    text = key.strip()
    if not text:
        return "", None
    if text.startswith(CHAT_HISTORY_KEY_PREFIX):
        remainder = text[len(CHAT_HISTORY_KEY_PREFIX):]
        mtime_text, sep, path_text = remainder.partition(":")
        if not sep:
            return "", None
        try:
            mtime_ns = int(mtime_text)
        except ValueError:
            return "", None
        path_key = normalize_path_key(path_text)
        return path_key, mtime_ns
    return normalize_path_key(text), None


def chat_history_path_from_key(key: object) -> str:
    path_key, _mtime_ns = parse_chat_history_key(key)
    return path_key
