"""
AI Service for PDF Master.

Uses the official `google-genai` SDK only.
"""

from __future__ import annotations

import atexit
import json
import logging
import os
import threading
import time
from collections import OrderedDict
from functools import wraps
from importlib import import_module
from typing import Any, Callable, Optional, ParamSpec, TypeVar, cast

from .optional_deps import fitz
from .path_utils import normalize_path_key

try:
    from .constants import AI_BASE_DELAY, AI_DEFAULT_TIMEOUT, AI_MAX_DELAY, AI_MAX_RETRIES, AI_MAX_TEXT_LENGTH
except ImportError:
    AI_MAX_TEXT_LENGTH = 30000
    AI_DEFAULT_TIMEOUT = 30
    AI_MAX_RETRIES = 3
    AI_BASE_DELAY = 1.0
    AI_MAX_DELAY = 30.0


class _PerfTimerFallback:
    def __init__(self, *_args: object, **_kwargs: object):
        pass

    def __enter__(self):
        return self

    def __exit__(self, _exc_type: object, _exc_val: object, _exc_tb: object):
        return False


try:
    from .perf import PerfTimer
except ImportError:
    PerfTimer = cast(Any, _PerfTimerFallback)


logger = logging.getLogger(__name__)
P = ParamSpec("P")
T = TypeVar("T")


def _import_optional_module(module_name: str) -> Any | None:
    try:
        return import_module(module_name)
    except ImportError:
        return None


_GENAI_MODULE = _import_optional_module("google.genai")

GENAI_AVAILABLE = _GENAI_MODULE is not None
GENAI_CLIENT: Any | None = _GENAI_MODULE

if _GENAI_MODULE is not None:
    logger.info("google-genai SDK loaded successfully")
else:
    logger.warning("google-genai SDK is not installed. AI features are disabled.")


def _response_text(response: object) -> str:
    text = getattr(response, "text", "")
    return text if isinstance(text, str) else ""


class AIServiceError(Exception):
    pass


class APIKeyError(AIServiceError):
    pass


class APITimeoutError(AIServiceError):
    pass


class APIRateLimitError(AIServiceError):
    pass


def retry_with_backoff(
    max_retries: int = AI_MAX_RETRIES,
    base_delay: float = AI_BASE_DELAY,
    max_delay: float = AI_MAX_DELAY,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    import random

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_error: Exception | None = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_error = exc
                    error_text = str(exc).lower()
                    if any(token in error_text for token in ("api key", "authentication", "invalid api key")):
                        raise APIKeyError(str(exc)) from exc
                    if any(token in error_text for token in ("rate limit", "quota", "429")):
                        if attempt >= max_retries:
                            raise APIRateLimitError(str(exc)) from exc
                    if attempt >= max_retries:
                        raise
                    delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
                    logger.warning("AI call failed, retrying in %.1fs: %s", delay, exc)
                    time.sleep(delay)
            if last_error is not None:
                raise last_error
            raise RuntimeError("retry loop exited without returning")

        return wrapper

    return decorator


class AIService:
    DEFAULT_MODEL = "gemini-2.5-flash"
    MAX_TEXT_LENGTH = AI_MAX_TEXT_LENGTH
    DEFAULT_TIMEOUT = AI_DEFAULT_TIMEOUT
    _TEXT_CACHE_MAX_BYTES = 16 * 1024 * 1024
    _UPLOAD_CACHE_MAX_ITEMS = 16

    _text_cache: OrderedDict[tuple[Any, ...], tuple[str, int]] = OrderedDict()
    _text_cache_bytes = 0
    _text_cache_lock = threading.Lock()

    _uploaded_file_cache: OrderedDict[tuple[str, int], Any] = OrderedDict()
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

    def _get_cached_text(self, key: tuple[Any, ...]) -> str | None:
        cls = self.__class__
        with cls._text_cache_lock:
            item = cls._text_cache.get(key)
            if item is None:
                return None
            text, _size = item
            cls._text_cache.move_to_end(key)
            return text

    def _put_cached_text(self, key: tuple[Any, ...], text: str) -> None:
        cls = self.__class__
        size = self._estimate_text_bytes(text)
        if size > cls._TEXT_CACHE_MAX_BYTES:
            return
        with cls._text_cache_lock:
            old = cls._text_cache.pop(key, None)
            if old:
                cls._text_cache_bytes -= old[1]
            cls._text_cache[key] = (text, size)
            cls._text_cache_bytes += size
            while cls._text_cache_bytes > cls._TEXT_CACHE_MAX_BYTES and cls._text_cache:
                _, (_old_text, old_size) = cls._text_cache.popitem(last=False)
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

    @staticmethod
    def _collect_exception_text(exc: BaseException) -> str:
        parts: list[str] = []
        current: BaseException | None = exc
        seen: set[int] = set()
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            text = str(current).strip()
            if text:
                parts.append(text)
            current = current.__cause__ or current.__context__
        return " | ".join(parts).lower()

    def _should_fallback_from_file_api(self, exc: BaseException) -> bool:
        text = self._collect_exception_text(exc)
        if not text:
            return False

        allow_tokens = (
            "file",
            "upload",
            "mime",
            "unsupported",
            "too large",
            "size",
            "invalid argument",
        )
        deny_tokens = (
            "api key",
            "auth",
            "quota",
            "rate",
            "permission",
            "timeout",
            "schema",
            "json",
            "parse",
            "internal",
        )
        return any(token in text for token in allow_tokens) and not any(token in text for token in deny_tokens)

    def _generate_structured_payload_from_extracted_text(
        self,
        *,
        prompt: str,
        pdf_path: str,
        schema: dict[str, Any],
        partial_callback: Callable[[str], None] | None = None,
        fallback_max_pages: int | None = None,
        upload_error: Exception | None = None,
    ) -> dict[str, Any]:
        extracted_text = self.extract_text_from_pdf(pdf_path, max_pages=fallback_max_pages)
        if not extracted_text.strip():
            raise RuntimeError(f"PDF text extraction failed after File API upload failure: {upload_error}")
        contents = [prompt, extracted_text]
        if partial_callback is not None:
            return self._stream_generate_content(
                contents=contents,
                schema=schema,
                partial_callback=partial_callback,
            )
        return self._generate_content(contents=contents, schema=schema)

    def _get_cached_uploaded_file(self, key: tuple[str, int]) -> Any | None:
        cls = self.__class__
        with cls._uploaded_file_cache_lock:
            item = cls._uploaded_file_cache.get(key)
            if item is None:
                return None
            cls._uploaded_file_cache.move_to_end(key)
            return item

    def _put_cached_uploaded_file(self, key: tuple[str, int], uploaded_file: Any) -> None:
        cls = self.__class__
        with cls._uploaded_file_cache_lock:
            cls._uploaded_file_cache.pop(key, None)
            cls._uploaded_file_cache[key] = uploaded_file
            while len(cls._uploaded_file_cache) > cls._UPLOAD_CACHE_MAX_ITEMS:
                cls._uploaded_file_cache.popitem(last=False)

    @retry_with_backoff()
    def _upload_pdf_file(self, pdf_path: str) -> Any:
        if not self.is_available or self._client is None:
            raise RuntimeError("AI service not available")
        cache_key = self._make_upload_cache_key(pdf_path)
        cached = self._get_cached_uploaded_file(cache_key)
        if cached is not None:
            return cached
        files_api = getattr(self._client, "files", None)
        if files_api is None or not hasattr(files_api, "upload"):
            raise RuntimeError("google-genai client does not expose File API upload")
        uploaded = files_api.upload(file=pdf_path)
        self._put_cached_uploaded_file(cache_key, uploaded)
        return uploaded

    def extract_text_from_pdf(self, pdf_path: str, max_pages: int | None = None) -> str:
        cache_key = self._make_text_cache_key(pdf_path, max_pages)
        with PerfTimer(
            "core.ai.extract_text",
            logger=logger,
            extra={"file": os.path.basename(pdf_path), "max_pages": max_pages},
        ):
            cached = self._get_cached_text(cache_key)
            if cached is not None:
                return cached

            doc = None
            try:
                doc = fitz.open(pdf_path)
                text_parts: list[str] = []
                page_count = len(doc) if max_pages is None else min(len(doc), max_pages)
                current_length = 0

                for i in range(page_count):
                    page = doc[i]
                    raw_text = page.get_text()
                    text = raw_text if isinstance(raw_text, str) else ""
                    if text.strip():
                        chunk = f"[Page {i + 1}]\n{text}"
                        text_parts.append(chunk)
                        current_length += len(chunk)
                        if current_length > self.MAX_TEXT_LENGTH:
                            break

                full_text = "\n\n".join(text_parts)
                if len(full_text) > self.MAX_TEXT_LENGTH:
                    full_text = full_text[: self.MAX_TEXT_LENGTH] + "\n\n[... truncated ...]"
                self._put_cached_text(cache_key, full_text)
                return full_text
            finally:
                if doc:
                    doc.close()

    def _make_summary_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "key_points": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["title", "summary", "key_points"],
            "additionalProperties": False,
        }

    def _make_answer_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "answer": {"type": "string"},
            },
            "required": ["answer"],
            "additionalProperties": False,
        }

    def _make_keywords_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["keywords"],
            "additionalProperties": False,
        }

    def _build_generate_config(self, schema: dict[str, Any]) -> Any:
        if self._types is None:
            raise RuntimeError("google-genai types module is not available")
        return self._types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=schema,
        )

    def _coerce_payload(self, parsed: Any, schema: dict[str, Any]) -> dict[str, Any]:
        if hasattr(parsed, "model_dump"):
            parsed = parsed.model_dump()
        if isinstance(parsed, dict):
            return parsed
        required = schema.get("required", [])
        return {key: "" if key != "key_points" and key != "keywords" else [] for key in required}

    def _parse_structured_response(self, response: Any, raw_text: str, schema: dict[str, Any]) -> dict[str, Any]:
        parsed = getattr(response, "parsed", None) if response is not None else None
        if parsed is not None:
            return self._coerce_payload(parsed, schema)
        if raw_text.strip():
            loaded = json.loads(raw_text)
            if isinstance(loaded, dict):
                return loaded
        raise RuntimeError("Structured response parsing failed")

    def _stream_generate_content(
        self,
        *,
        contents: list[Any],
        schema: dict[str, Any],
        partial_callback: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        if self._client is None:
            raise RuntimeError("Gemini client is not configured")

        config = self._build_generate_config(schema)
        chunks: list[str] = []
        for chunk in self._client.models.generate_content_stream(
            model=self._model,
            contents=contents,
            config=config,
        ):
            text = _response_text(chunk)
            if text:
                chunks.append(text)
                if partial_callback is not None:
                    partial_callback(text)
        raw_text = "".join(chunks)
        return self._parse_structured_response(None, raw_text, schema)

    @retry_with_backoff()
    def _generate_content(
        self,
        *,
        contents: list[Any],
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        if self._client is None:
            raise RuntimeError("Gemini client is not configured")
        config = self._build_generate_config(schema)
        response = self._client.models.generate_content(
            model=self._model,
            contents=contents,
            config=config,
        )
        return self._parse_structured_response(response, _response_text(response), schema)

    def _generate_structured_payload(
        self,
        *,
        prompt: str,
        pdf_path: str,
        schema: dict[str, Any],
        partial_callback: Callable[[str], None] | None = None,
        fallback_max_pages: int | None = None,
    ) -> dict[str, Any]:
        try:
            uploaded_file = self._upload_pdf_file(pdf_path)
        except Exception as exc:
            if not self._should_fallback_from_file_api(exc):
                raise
            logger.warning("Gemini File API upload failed, falling back to local text extraction: %s", exc)
            return self._generate_structured_payload_from_extracted_text(
                prompt=prompt,
                pdf_path=pdf_path,
                schema=schema,
                partial_callback=partial_callback,
                fallback_max_pages=fallback_max_pages,
                upload_error=exc,
            )

        contents = [prompt, uploaded_file]
        if partial_callback is not None:
            return self._stream_generate_content(
                contents=contents,
                schema=schema,
                partial_callback=partial_callback,
            )
        return self._generate_content(contents=contents, schema=schema)

    def _build_summary_prompt(self, language: str, style: str, max_pages: int | None) -> str:
        style_map = {
            "concise": "Keep the summary compact and easy to scan.",
            "detailed": "Provide a fuller summary with more detail.",
            "bullet": "Prefer concise bullet-style phrasing in the summary and key points.",
        }
        language_name = "Korean" if language == "ko" else "English"
        page_limit = (
            f"If the document is long, focus on the first {max_pages} page(s)."
            if max_pages and max_pages > 0
            else "Summarize the whole document."
        )
        return (
            f"Analyze the attached PDF and return JSON only. Respond in {language_name}. "
            f"{style_map.get(style, style_map['concise'])} "
            f"{page_limit} "
            'Schema: {"title": string, "summary": string, "key_points": string[]}. '
            "The title should be concise and the key points should be distinct."
        )

    def _build_keywords_prompt(self, max_keywords: int, language: str) -> str:
        language_name = "Korean" if language == "ko" else "English"
        return (
            f"Extract up to {max_keywords} important keywords from the attached PDF and return JSON only. "
            f"Use {language_name}. "
            'Schema: {"keywords": string[]}. '
            "Return short, deduplicated keywords only."
        )

    def summarize_pdf(
        self,
        pdf_path: str,
        language: str = "ko",
        style: str = "concise",
        max_pages: int | None = None,
        partial_callback: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        if not self.is_available:
            raise RuntimeError("AI service not available. Check API key and google-genai installation.")
        prompt = self._build_summary_prompt(language, style, max_pages)
        payload = self._generate_structured_payload(
            prompt=prompt,
            pdf_path=pdf_path,
            schema=self._make_summary_schema(),
            partial_callback=partial_callback,
            fallback_max_pages=max_pages,
        )
        payload.setdefault("title", "")
        payload.setdefault("summary", "")
        payload.setdefault("key_points", [])
        return {
            "title": str(payload.get("title", "")),
            "summary": str(payload.get("summary", "")),
            "key_points": [str(item) for item in payload.get("key_points", []) if str(item).strip()],
        }

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
                return

            try:
                mtime_ns = os.stat(abs_path).st_mtime_ns
            except OSError:
                mtime_ns = 0
            stale_keys = [key for key in cls._chat_sessions if key[1] == abs_path and key[2] == mtime_ns]
            for key in stale_keys:
                cls._chat_sessions.pop(key, None)

    def ask_about_pdf(
        self,
        pdf_path: str,
        question: str,
        conversation_history: list[dict[str, str]] | None = None,
        partial_callback: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        if not self.is_available:
            raise RuntimeError("AI service not available. Check API key and google-genai installation.")
        if not question.strip():
            raise RuntimeError("Question is required.")

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
            )
        else:
            if partial_callback is not None:
                chunks: list[str] = []
                for chunk in chat.send_message_stream(question, config=config):
                    text = _response_text(chunk)
                    if text:
                        chunks.append(text)
                        partial_callback(text)
                raw_text = "".join(chunks)
                payload = self._parse_structured_response(None, raw_text, schema)
            else:
                response = chat.send_message(question, config=config)
                payload = self._parse_structured_response(response, _response_text(response), schema)

        payload.setdefault("answer", "")
        return {"answer": str(payload.get("answer", ""))}

    def extract_keywords(
        self,
        pdf_path: str,
        max_keywords: int = 10,
        language: str = "ko",
    ) -> dict[str, Any]:
        if not self.is_available:
            raise RuntimeError("AI service not available. Check API key and google-genai installation.")
        prompt = self._build_keywords_prompt(max_keywords, language)
        payload = self._generate_structured_payload(
            prompt=prompt,
            pdf_path=pdf_path,
            schema=self._make_keywords_schema(),
            partial_callback=None,
            fallback_max_pages=None,
        )
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
        return {"keywords": deduped}

    @classmethod
    def shutdown_executor(cls):
        return None


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
