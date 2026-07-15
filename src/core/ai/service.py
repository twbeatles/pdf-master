from __future__ import annotations

import atexit
import logging
import threading
from collections import OrderedDict
from typing import Any, Callable, Optional

from .cache import AICacheMixin
from .client import GENAI_AVAILABLE, GENAI_CLIENT, PerfTimer, _GENAI_MODULE, _response_text, fitz
from .config import AI_DEFAULT_TIMEOUT, AI_MAX_TEXT_LENGTH
from .errors import AIServiceError, APIKeyError, APIRateLimitError, APITimeoutError, retry_with_backoff
from .extraction import AIExtractionMixin
from .generation import AIGenerationMixin
from .prompts import AIPromptMixin
from .schemas import AISchemaMixin
from .session import AIChatSessionMixin

logger = logging.getLogger(__name__)


class AIService(
    AIExtractionMixin,
    AIGenerationMixin,
    AISchemaMixin,
    AIPromptMixin,
    AIChatSessionMixin,
    AICacheMixin,
):
    DEFAULT_MODEL = "gemini-2.5-flash"
    MAX_TEXT_LENGTH = AI_MAX_TEXT_LENGTH
    DEFAULT_TIMEOUT = AI_DEFAULT_TIMEOUT
    _TEXT_CACHE_MAX_BYTES = 16 * 1024 * 1024
    _UPLOAD_CACHE_MAX_ITEMS = 16

    _text_cache: OrderedDict[tuple[Any, ...], tuple[str, int, dict[str, Any]]] = OrderedDict()
    _text_cache_bytes = 0
    _text_cache_lock = threading.Lock()

    _uploaded_file_cache: OrderedDict[tuple[str, int], dict[str, Any]] = OrderedDict()
    _uploaded_file_cache_lock = threading.Lock()

    _chat_sessions: dict[tuple[str, str, int], Any] = {}
    _chat_sessions_lock = threading.Lock()

    def __init__(self, api_key: str = "", model: str | None = None, timeout: int | None = None):
        self._api_key = api_key
        self._model = model or self.DEFAULT_MODEL
        self._timeout = timeout or self.DEFAULT_TIMEOUT
        self._configured = False
        self._client: Any | None = None
        self._types: Any | None = None
        if api_key:
            self._configure_api()

    def _configure_api(self) -> bool:
        if not GENAI_AVAILABLE:
            logger.error("google-genai is not available")
            return False
        if not self._api_key:
            logger.warning("API key not provided")
            return False
        if not self._validate_api_key_format(self._api_key):
            logger.error("Invalid API key format")
            return False

        try:
            genai = _GENAI_MODULE
            client_class = getattr(genai, "Client", None) if genai is not None else None
            self._types = getattr(genai, "types", None) if genai is not None else None
            if client_class is None or self._types is None:
                logger.error("google-genai SDK surface is incomplete")
                return False
            self._client = client_class(api_key=self._api_key)
            self._configured = True
            return True
        except Exception as exc:
            logger.error("Failed to configure google-genai client: %s", exc)
            return False

    def _validate_api_key_format(self, api_key: str) -> bool:
        if not api_key or not isinstance(api_key, str):
            return False
        if len(api_key) < 20:
            return False
        if any(ch in api_key for ch in (" ", "\n", "\t")):
            return False
        return True

    def validate_api_key(self) -> tuple[bool, str]:
        if not GENAI_AVAILABLE:
            return False, "google-genai SDK is not installed."
        if not self._api_key:
            return False, "API key is not configured."
        if not self._validate_api_key_format(self._api_key):
            return False, "API key format is invalid."

        try:
            client = self._client if self._configured else None
            if client is None:
                if not self._configure_api():
                    return False, "Failed to initialize google-genai client."
                client = self._client
            if client is None:
                return False, "Failed to initialize google-genai client."
            response = client.models.generate_content(model=self._model, contents="Hi")
            return bool(response), "API key is valid."
        except APIKeyError:
            return False, "API key is invalid."
        except Exception as exc:
            return False, f"API connection error: {exc}"

    def set_api_key(self, api_key: str) -> bool:
        self._api_key = api_key
        return self._configure_api()

    @property
    def is_available(self) -> bool:
        return bool(GENAI_AVAILABLE and self._configured and self._client is not None)

    def summarize_pdf(
        self,
        pdf_path: str,
        language: str = "ko",
        style: str = "concise",
        max_pages: int | None = None,
        partial_callback: Callable[[str], None] | None = None,
        cancel_check: Callable[[], None] | None = None,
    ) -> dict[str, Any]:
        if not self.is_available:
            raise RuntimeError("AI service not available. Check API key and google-genai installation.")
        self._run_cancel_check(cancel_check)
        prompt = self._build_summary_prompt(language, style, max_pages)
        payload = self._generate_structured_payload(
            prompt=prompt,
            pdf_path=pdf_path,
            schema=self._make_summary_schema(),
            partial_callback=partial_callback,
            fallback_max_pages=max_pages,
            cancel_check=cancel_check,
        )
        self._run_cancel_check(cancel_check)
        payload.setdefault("title", "")
        payload.setdefault("summary", "")
        payload.setdefault("key_points", [])
        meta = self._normalize_meta(payload.get("meta"), default_source="file_api")
        return {
            "title": str(payload.get("title", "")),
            "summary": str(payload.get("summary", "")),
            "key_points": [str(item) for item in payload.get("key_points", []) if str(item).strip()],
            "meta": meta,
        }

    def ask_about_pdf(
        self,
        pdf_path: str,
        question: str,
        conversation_history: list[dict[str, str]] | None = None,
        partial_callback: Callable[[str], None] | None = None,
        cancel_check: Callable[[], None] | None = None,
    ) -> dict[str, Any]:
        if not self.is_available:
            raise RuntimeError("AI service not available. Check API key and google-genai installation.")
        if not question.strip():
            raise RuntimeError("Question is required.")

        self._run_cancel_check(cancel_check)
        schema = self._make_answer_schema()
        config = self._build_generate_config(schema)
        try:
            chat = self._get_or_create_chat(pdf_path, conversation_history)
        except Exception as exc:
            if not self._should_fallback_from_file_api(exc):
                raise
            logger.warning("Chat session initialization failed, falling back to local-context QA: %s", exc)
            prompt = (
                "Answer the user's question about the PDF and return JSON only. "
                'Schema: {"answer": string}. '
                f"Question: {question}"
            )
            payload = self._generate_structured_payload(
                prompt=prompt,
                pdf_path=pdf_path,
                schema=schema,
                partial_callback=partial_callback,
                fallback_max_pages=None,
                cancel_check=cancel_check,
            )
        else:
            if partial_callback is not None:
                chunks: list[str] = []
                for chunk in chat.send_message_stream(question, config=config):
                    self._run_cancel_check(cancel_check)
                    text = _response_text(chunk)
                    if text:
                        chunks.append(text)
                        partial_callback(text)
                self._run_cancel_check(cancel_check)
                raw_text = "".join(chunks)
                payload = self._parse_structured_response(None, raw_text, schema)
            else:
                self._run_cancel_check(cancel_check)
                response = chat.send_message(question, config=config)
                self._run_cancel_check(cancel_check)
                payload = self._parse_structured_response(response, _response_text(response), schema)

        payload.setdefault("answer", "")
        meta = self._normalize_meta(payload.get("meta"), default_source="file_api")
        return {"answer": str(payload.get("answer", "")), "meta": meta}

    def extract_keywords(
        self,
        pdf_path: str,
        max_keywords: int = 10,
        language: str = "ko",
        cancel_check: Callable[[], None] | None = None,
    ) -> dict[str, Any]:
        if not self.is_available:
            raise RuntimeError("AI service not available. Check API key and google-genai installation.")
        self._run_cancel_check(cancel_check)
        prompt = self._build_keywords_prompt(max_keywords, language)
        payload = self._generate_structured_payload(
            prompt=prompt,
            pdf_path=pdf_path,
            schema=self._make_keywords_schema(),
            partial_callback=None,
            fallback_max_pages=None,
            cancel_check=cancel_check,
        )
        self._run_cancel_check(cancel_check)
        keywords = [str(item) for item in payload.get("keywords", []) if str(item).strip()]
        deduped: list[str] = []
        seen: set[str] = set()
        for keyword in keywords:
            lowered = keyword.casefold()
            if lowered in seen:
                continue
            seen.add(lowered)
            deduped.append(keyword)
            if len(deduped) >= max_keywords:
                break
        meta = self._normalize_meta(payload.get("meta"), default_source="file_api")
        return {"keywords": deduped, "meta": meta}


_ai_service_instance: Optional[AIService] = None
_ai_service_lock = threading.Lock()


def get_ai_service() -> AIService:
    global _ai_service_instance
    if _ai_service_instance is None:
        with _ai_service_lock:
            if _ai_service_instance is None:
                _ai_service_instance = AIService()
    return _ai_service_instance


atexit.register(AIService.shutdown_executor)


__all__ = [
    "AIService",
    "AIServiceError",
    "APIKeyError",
    "APITimeoutError",
    "APIRateLimitError",
    "GENAI_AVAILABLE",
    "GENAI_CLIENT",
    "PerfTimer",
    "fitz",
    "get_ai_service",
    "retry_with_backoff",
]
