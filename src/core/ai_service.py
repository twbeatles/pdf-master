from __future__ import annotations

from .ai import (
    _GENAI_MODULE,
    GENAI_AVAILABLE,
    GENAI_CLIENT,
    AIService,
    AIServiceError,
    APIKeyError,
    APIRateLimitError,
    APITimeoutError,
    PerfTimer,
    _response_text,
    fitz,
    get_ai_service,
    retry_with_backoff,
)
from .ai.client import _import_optional_module, _PerfTimerFallback

__all__ = [
    "AIService",
    "AIServiceError",
    "APIKeyError",
    "APITimeoutError",
    "APIRateLimitError",
    "GENAI_AVAILABLE",
    "GENAI_CLIENT",
    "PerfTimer",
    "_GENAI_MODULE",
    "_PerfTimerFallback",
    "_import_optional_module",
    "_response_text",
    "fitz",
    "get_ai_service",
    "retry_with_backoff",
]
