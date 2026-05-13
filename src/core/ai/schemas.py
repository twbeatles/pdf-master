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


class AISchemaMixin:
    def _build_result_meta(
        self,
        *,
        source: str,
        truncated: bool = False,
        page_focus_limit: int | None = None,
        fallback_pages_total: int | None = None,
        fallback_pages_used: int | None = None,
        max_text_chars: int | None = None,
    ) -> dict[str, Any]:
        return {
            "source": source,
            "truncated": bool(truncated),
            "page_focus_limit": int(page_focus_limit) if isinstance(page_focus_limit, int) and page_focus_limit > 0 else None,
            "fallback_pages_total": (
                int(fallback_pages_total)
                if isinstance(fallback_pages_total, int) and fallback_pages_total > 0
                else None
            ),
            "fallback_pages_used": (
                int(fallback_pages_used)
                if isinstance(fallback_pages_used, int) and fallback_pages_used > 0
                else None
            ),
            "max_text_chars": int(max_text_chars) if isinstance(max_text_chars, int) and max_text_chars > 0 else None,
        }

    def _normalize_meta(self, meta: Any, *, default_source: str = "file_api") -> dict[str, Any]:
        if not isinstance(meta, dict):
            return self._build_result_meta(source=default_source)
        return self._build_result_meta(
            source=str(meta.get("source") or default_source),
            truncated=bool(meta.get("truncated", False)),
            page_focus_limit=meta.get("page_focus_limit"),
            fallback_pages_total=meta.get("fallback_pages_total"),
            fallback_pages_used=meta.get("fallback_pages_used"),
            max_text_chars=meta.get("max_text_chars"),
        )

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
