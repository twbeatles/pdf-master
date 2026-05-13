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


class AIExtractionMixin:
    def _extract_text_with_meta(self, pdf_path: str, max_pages: int | None = None) -> tuple[str, dict[str, Any]]:
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
                pages_used = 0
                truncated = False

                for i in range(page_count):
                    page = doc[i]
                    raw_text = page.get_text()
                    text = raw_text if isinstance(raw_text, str) else ""
                    if text.strip():
                        chunk = f"[Page {i + 1}]\n{text}"
                        if current_length + len(chunk) > self.MAX_TEXT_LENGTH:
                            remaining = self.MAX_TEXT_LENGTH - current_length
                            if remaining > 0:
                                text_parts.append(chunk[:remaining])
                            truncated = True
                            pages_used = i + 1
                            break
                        text_parts.append(chunk)
                        current_length += len(chunk)
                    pages_used = i + 1

                full_text = "\n\n".join(text_parts)
                if truncated and full_text and not full_text.endswith("[... truncated ...]"):
                    full_text = full_text.rstrip() + "\n\n[... truncated ...]"
                meta = self._build_result_meta(
                    source="text_fallback",
                    truncated=truncated,
                    page_focus_limit=max_pages,
                    fallback_pages_total=len(doc),
                    fallback_pages_used=pages_used,
                    max_text_chars=self.MAX_TEXT_LENGTH if truncated else None,
                )
                self._put_cached_text(cache_key, full_text, meta)
                return full_text, meta
            finally:
                if doc:
                    doc.close()

    def extract_text_from_pdf(self, pdf_path: str, max_pages: int | None = None) -> str:
        text, _meta = self._extract_text_with_meta(pdf_path, max_pages=max_pages)
        return text
