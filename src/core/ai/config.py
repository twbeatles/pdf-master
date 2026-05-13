from __future__ import annotations

try:
    from ..constants import AI_BASE_DELAY, AI_DEFAULT_TIMEOUT, AI_MAX_DELAY, AI_MAX_RETRIES, AI_MAX_TEXT_LENGTH
except ImportError:
    AI_MAX_TEXT_LENGTH = 30000
    AI_DEFAULT_TIMEOUT = 30
    AI_MAX_RETRIES = 3
    AI_BASE_DELAY = 1.0
    AI_MAX_DELAY = 30.0

__all__ = [
    "AI_BASE_DELAY",
    "AI_DEFAULT_TIMEOUT",
    "AI_MAX_DELAY",
    "AI_MAX_RETRIES",
    "AI_MAX_TEXT_LENGTH",
]
