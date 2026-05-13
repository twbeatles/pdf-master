from __future__ import annotations
# pyright: reportAttributeAccessIssue=false

import json
import logging
import os
import threading
import time
from collections import OrderedDict
from typing import Any, Callable, cast

from ..path_utils import normalize_path_key
from .client import GENAI_AVAILABLE, GENAI_CLIENT, PerfTimer, _GENAI_MODULE, _response_text, fitz
from .config import AI_BASE_DELAY, AI_DEFAULT_TIMEOUT, AI_MAX_DELAY, AI_MAX_RETRIES, AI_MAX_TEXT_LENGTH
from .errors import APIKeyError, APIRateLimitError, APITimeoutError, retry_with_backoff

logger = logging.getLogger(__name__)


class AICacheMixin:
    def _make_text_cache_key(self, pdf_path: str, max_pages: int | None) -> tuple[Any, ...]:
        abs_path = normalize_path_key(pdf_path)
        try:
            mtime_ns = os.stat(abs_path).st_mtime_ns
        except OSError:
            mtime_ns = 0
        return abs_path, mtime_ns, max_pages, self.MAX_TEXT_LENGTH

    @staticmethod
    def _estimate_text_bytes(text: str) -> int:
        return len(text.encode("utf-8", errors="ignore"))

    def _get_cached_text(self, key: tuple[Any, ...]) -> tuple[str, dict[str, Any]] | None:
        cls = self.__class__
        with cls._text_cache_lock:
            item = cls._text_cache.get(key)
            if item is None:
                return None
            text, _size, meta = item
            cls._text_cache.move_to_end(key)
            return text, dict(meta)

    def _put_cached_text(self, key: tuple[Any, ...], text: str, meta: dict[str, Any]) -> None:
        cls = self.__class__
        size = self._estimate_text_bytes(text)
        if size > cls._TEXT_CACHE_MAX_BYTES:
            return
        with cls._text_cache_lock:
            old = cls._text_cache.pop(key, None)
            if old:
                cls._text_cache_bytes -= old[1]
            cls._text_cache[key] = (text, size, dict(meta))
            cls._text_cache_bytes += size
            while cls._text_cache_bytes > cls._TEXT_CACHE_MAX_BYTES and cls._text_cache:
                _, (_old_text, old_size, _old_meta) = cls._text_cache.popitem(last=False)
                cls._text_cache_bytes -= old_size

    def _make_upload_cache_key(self, pdf_path: str) -> tuple[str, int]:
        abs_path = normalize_path_key(pdf_path)
        try:
            mtime_ns = os.stat(abs_path).st_mtime_ns
        except OSError:
            mtime_ns = 0
        return abs_path, mtime_ns

    def _make_chat_session_cache_key(self, pdf_path: str) -> tuple[str, str, int]:
        abs_path = normalize_path_key(pdf_path)
        try:
            mtime_ns = os.stat(abs_path).st_mtime_ns
        except OSError:
            mtime_ns = 0
        return self._model, abs_path, mtime_ns

    def _delete_uploaded_file_entry(self, entry: Any) -> None:
        if not isinstance(entry, dict):
            return
        remote_name = entry.get("name")
        client = entry.get("client")
        if not isinstance(remote_name, str) or not remote_name:
            return
        files_api = getattr(client, "files", None)
        if files_api is None or not hasattr(files_api, "delete"):
            return
        try:
            files_api.delete(name=remote_name)
        except Exception:
            logger.debug("Failed to delete remote Gemini file %s", remote_name, exc_info=True)

    def _get_cached_uploaded_file(self, key: tuple[str, int]) -> Any | None:
        cls = self.__class__
        with cls._uploaded_file_cache_lock:
            item = cls._uploaded_file_cache.get(key)
            if item is None:
                return None
            cls._uploaded_file_cache.move_to_end(key)
            return item.get("file")

    def _put_cached_uploaded_file(self, key: tuple[str, int], uploaded_file: Any) -> None:
        cls = self.__class__
        evicted_entries: list[dict[str, Any]] = []
        with cls._uploaded_file_cache_lock:
            previous = cls._uploaded_file_cache.pop(key, None)
            if previous is not None:
                evicted_entries.append(previous)
            cls._uploaded_file_cache[key] = {
                "file": uploaded_file,
                "name": getattr(uploaded_file, "name", None),
                "client": self._client,
            }
            while len(cls._uploaded_file_cache) > cls._UPLOAD_CACHE_MAX_ITEMS:
                _cache_key, entry = cls._uploaded_file_cache.popitem(last=False)
                evicted_entries.append(entry)
        for entry in evicted_entries:
            self._delete_uploaded_file_entry(entry)

    @classmethod
    def clear_chat_session(cls, pdf_path: str, all_versions: bool = True) -> None:
        abs_path = normalize_path_key(pdf_path)
        if not abs_path:
            return

        with cls._chat_sessions_lock:
            if all_versions:
                stale_keys = [key for key in cls._chat_sessions if len(key) >= 2 and key[1] == abs_path]
                for key in stale_keys:
                    cls._chat_sessions.pop(key, None)
            else:
                try:
                    mtime_ns = os.stat(abs_path).st_mtime_ns
                except OSError:
                    mtime_ns = 0
                stale_keys = [key for key in cls._chat_sessions if key[1] == abs_path and key[2] == mtime_ns]
                for key in stale_keys:
                    cls._chat_sessions.pop(key, None)

        stale_upload_entries: list[dict[str, Any]] = []
        with cls._uploaded_file_cache_lock:
            if all_versions:
                stale_upload_keys = [key for key in cls._uploaded_file_cache if key[0] == abs_path]
            else:
                try:
                    upload_mtime_ns = os.stat(abs_path).st_mtime_ns
                except OSError:
                    upload_mtime_ns = 0
                stale_upload_keys = [key for key in cls._uploaded_file_cache if key == (abs_path, upload_mtime_ns)]
            for key in stale_upload_keys:
                entry = cls._uploaded_file_cache.pop(key, None)
                if entry is not None:
                    stale_upload_entries.append(entry)

        service = cls()
        for entry in stale_upload_entries:
            service._delete_uploaded_file_entry(entry)

    @classmethod
    def shutdown_executor(cls):
        stale_upload_entries: list[dict[str, Any]] = []
        with cls._uploaded_file_cache_lock:
            stale_upload_entries = list(cls._uploaded_file_cache.values())
            cls._uploaded_file_cache.clear()
        with cls._chat_sessions_lock:
            cls._chat_sessions.clear()

        service = cls()
        for entry in stale_upload_entries:
            service._delete_uploaded_file_entry(entry)
        return None
