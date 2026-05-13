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


class AIChatSessionMixin:
    def _history_to_contents(self, history: list[dict[str, str]]) -> list[Any]:
        if self._types is None:
            return []
        contents: list[Any] = []
        part_factory = getattr(self._types, "Part", None)
        content_type = getattr(self._types, "Content", None)
        if part_factory is None or content_type is None:
            return []
        for entry in history:
            role = entry.get("role")
            content = entry.get("content", "")
            if role not in {"user", "assistant"} or not content:
                continue
            normalized_role = "model" if role == "assistant" else "user"
            contents.append(
                content_type(
                    role=normalized_role,
                    parts=[part_factory.from_text(text=content)],
                )
            )
        return contents

    def _get_or_create_chat(self, pdf_path: str, conversation_history: list[dict[str, str]] | None) -> Any:
        if self._client is None or self._types is None:
            raise RuntimeError("Gemini client is not configured")
        cache_key = self._make_chat_session_cache_key(pdf_path)
        with self.__class__._chat_sessions_lock:
            cached = self.__class__._chat_sessions.get(cache_key)
            if cached is not None:
                return cached

        uploaded_file = self._upload_pdf_file(pdf_path)
        part_factory = getattr(self._types, "Part", None)
        content_type = getattr(self._types, "Content", None)
        if part_factory is None or content_type is None:
            raise RuntimeError("google-genai content types are unavailable")

        history_contents = [
            content_type(
                role="user",
                parts=[
                    part_factory.from_text(
                        text=(
                            "You are assisting with questions about the attached PDF. "
                            "Use the PDF as the primary source of truth."
                        )
                    ),
                    uploaded_file,
                ],
            )
        ]
        history_contents.extend(self._history_to_contents(conversation_history or []))
        chat = self._client.chats.create(model=self._model, history=history_contents)
        with self.__class__._chat_sessions_lock:
            self.__class__._chat_sessions[cache_key] = chat
        return chat
