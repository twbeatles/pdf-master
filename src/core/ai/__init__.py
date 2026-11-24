from __future__ import annotations

from .client import (
    _GENAI_MODULE,
    GENAI_AVAILABLE,
    GENAI_CLIENT,
    PerfTimer,
    _response_text,
    fitz,
)
from .errors import (
    AIServiceError,
    APIKeyError,
    APIRateLimitError,
    APITimeoutError,
    retry_with_backoff,
)
from .models import (
    DEFAULT_MODEL,
    MODEL_CATALOG,
    MODEL_FALLBACKS,
    RETIRED_MODEL_MAP,
    available_model_choices,
    candidate_models,
    is_model_not_found_error,
    is_retired_model,
    list_remote_models,
    merge_model_choices,
    model_display_name,
    normalize_model_id,
    resolve_model_id,
)
from .service import AIService, get_ai_service

__all__ = [
    "AIService",
    "AIServiceError",
    "APIKeyError",
    "APITimeoutError",
    "APIRateLimitError",
    "DEFAULT_MODEL",
    "MODEL_CATALOG",
    "MODEL_FALLBACKS",
    "RETIRED_MODEL_MAP",
    "GENAI_AVAILABLE",
    "GENAI_CLIENT",
    "PerfTimer",
    "_GENAI_MODULE",
    "_response_text",
    "available_model_choices",
    "candidate_models",
    "fitz",
    "get_ai_service",
    "is_model_not_found_error",
    "is_retired_model",
    "list_remote_models",
    "merge_model_choices",
    "model_display_name",
    "normalize_model_id",
    "resolve_model_id",
    "retry_with_backoff",
]
