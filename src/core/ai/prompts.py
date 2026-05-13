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


class AIPromptMixin:
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
