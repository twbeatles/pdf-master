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


class AIGenerationMixin:
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
        extracted_text, meta = self._extract_text_with_meta(pdf_path, max_pages=fallback_max_pages)
        if not extracted_text.strip():
            raise RuntimeError(f"PDF text extraction failed after File API upload failure: {upload_error}")
        contents = [prompt, extracted_text]
        if partial_callback is not None:
            payload = self._stream_generate_content(
                contents=contents,
                schema=schema,
                partial_callback=partial_callback,
            )
        else:
            payload = self._generate_content(contents=contents, schema=schema)
        payload["meta"] = meta
        return payload

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
            payload = self._stream_generate_content(
                contents=contents,
                schema=schema,
                partial_callback=partial_callback,
            )
        else:
            payload = self._generate_content(contents=contents, schema=schema)
        payload["meta"] = self._build_result_meta(
            source="file_api",
            page_focus_limit=fallback_max_pages,
        )
        return payload
