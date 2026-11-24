from __future__ import annotations

# pyright: reportAttributeAccessIssue=false
import logging
import threading
from collections.abc import Callable
from typing import Any

from .config import MAX_CHAT_CONTEXT_CHARS, MAX_CHAT_CONTEXT_ENTRIES
from .models import candidate_models as _candidate_models_fn
from .models import is_model_not_found_error as _is_model_not_found_error

logger = logging.getLogger(__name__)


class AIChatSessionMixin:
    @staticmethod
    def _trim_history_for_context(
        history: list[dict[str, str]] | None,
    ) -> list[dict[str, str]]:
        """API 전송용 히스토리 축소 (ISSUE-002).

        저장소(최대 40개)와 별개로 전송은 최신분만 보낸다: 항목 수 상한을
        먼저 적용한 뒤, 문자 예산을 초과하지 않는 범위에서 최신 항목부터
        유지한다. 가장 최근 항목은 예산 초과 시에도 반드시 포함한다
        (현재 질문이 별도 전송되므로 빈 컨텍스트는 허용하지 않는다).
        """
        if not isinstance(history, list):
            return []
        valid = [
            entry
            for entry in history
            if isinstance(entry, dict)
            and entry.get("role") in {"user", "assistant"}
            and isinstance(entry.get("content"), str)
            and entry.get("content", "").strip()
        ]
        if len(valid) > MAX_CHAT_CONTEXT_ENTRIES:
            valid = valid[-MAX_CHAT_CONTEXT_ENTRIES :]
        kept: list[dict[str, str]] = []
        total = 0
        for entry in reversed(valid):
            size = len(str(entry.get("content", "")))
            if kept and total + size > MAX_CHAT_CONTEXT_CHARS:
                break
            kept.append(entry)
            total += size
        kept.reverse()
        return kept

    def _history_to_contents(self, history: list[dict[str, str]]) -> list[Any]:
        if self._types is None:
            return []
        contents: list[Any] = []
        part_factory = getattr(self._types, "Part", None)
        content_type = getattr(self._types, "Content", None)
        if part_factory is None or content_type is None:
            return []
        for entry in self._trim_history_for_context(history):
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

    def _get_or_create_chat(
        self,
        pdf_path: str,
        conversation_history: list[dict[str, str]] | None,
        cancel_check: Callable[[], None] | None = None,
    ) -> Any:
        if self._client is None or self._types is None:
            raise RuntimeError("Gemini client is not configured")
        cache_key = self._make_chat_session_cache_key(pdf_path)
        cls = self.__class__
        # single-flight: 같은 cache_key 생성은 한 번에 하나만
        create_lock = cls._chat_create_locks.setdefault(cache_key, threading.Lock())
        with create_lock:
            with cls._chat_sessions_lock:
                cached = cls._chat_sessions.get(cache_key)
                if cached is not None:
                    return cached

            self._run_cancel_check(cancel_check)
            uploaded_file = self._upload_pdf_file(pdf_path, cancel_check=cancel_check)
            self._run_cancel_check(cancel_check)
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
            history_contents.extend(
                self._history_to_contents(conversation_history or [])
            )
            self._run_cancel_check(cancel_check)
            # 퇴역·미지원 모델이면 폴백 모델로 채팅 재생성
            chat = None
            last_model_error: Exception | None = None
            for candidate in _candidate_models_fn(getattr(self, "_model", "")):
                self._run_cancel_check(cancel_check)
                try:
                    chat = self._client.chats.create(
                        model=candidate, history=history_contents
                    )
                except Exception as exc:
                    if _is_model_not_found_error(exc):
                        logger.warning(
                            "Chat model %s unavailable, trying fallback: %s",
                            candidate,
                            exc,
                        )
                        last_model_error = exc
                        continue
                    raise
                if candidate != self._model:
                    logger.info("AI chat model fell back to %s", candidate)
                    self._model = candidate
                break
            if chat is None:
                raise last_model_error or RuntimeError("No AI model available")
            # 폴백으로 모델이 바뀌었으면 실제 사용 모델 키로 저장
            store_key = (self._model, cache_key[1], cache_key[2])
            with cls._chat_sessions_lock:
                # double-check: 대기 중 다른 경로가 채웠을 수 있음
                existing = cls._chat_sessions.get(
                    cache_key
                ) or cls._chat_sessions.get(store_key)
                if existing is not None:
                    return existing
                cls._chat_sessions[store_key] = chat
            return chat
