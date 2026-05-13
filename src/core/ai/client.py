from __future__ import annotations

import logging
from importlib import import_module
from typing import Any, cast

from ..optional_deps import fitz

logger = logging.getLogger(__name__)


class _PerfTimerFallback:
    def __init__(self, *_args: object, **_kwargs: object):
        pass

    def __enter__(self):
        return self

    def __exit__(self, _exc_type: object, _exc_val: object, _exc_tb: object):
        return False


try:
    from ..perf import PerfTimer
except ImportError:
    PerfTimer = cast(Any, _PerfTimerFallback)


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


__all__ = [
    "GENAI_AVAILABLE",
    "GENAI_CLIENT",
    "PerfTimer",
    "_GENAI_MODULE",
    "_PerfTimerFallback",
    "_import_optional_module",
    "_response_text",
    "fitz",
]
