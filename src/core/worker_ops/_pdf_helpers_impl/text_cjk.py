"""PDF helpers: text_cjk."""
from __future__ import annotations

from __future__ import annotations
import json
import logging
import os
from collections.abc import Callable
from typing import Any, cast
from ...optional_deps import fitz
from ...worker_runtime.args import _as_str
logger = logging.getLogger(__name__)

def text_needs_cjk(text: str) -> bool:
    """한글·한자·가나 등 CJK 계열 글리프가 필요하면 True."""
    for ch in text or "":
        code = ord(ch)
        if (
            0x1100 <= code <= 0x11FF  # Hangul Jamo
            or 0x3130 <= code <= 0x318F  # Hangul Compatibility Jamo
            or 0xA960 <= code <= 0xA97F  # Hangul Jamo Extended-A
            or 0xAC00 <= code <= 0xD7AF  # Hangul Syllables
            or 0xD7B0 <= code <= 0xD7FF  # Hangul Jamo Extended-B
            or 0x3040 <= code <= 0x30FF  # Hiragana / Katakana
            or 0x31F0 <= code <= 0x31FF  # Katakana Phonetic Extensions
            or 0x3400 <= code <= 0x4DBF  # CJK Ext-A
            or 0x4E00 <= code <= 0x9FFF  # CJK Unified
            or 0xF900 <= code <= 0xFAFF  # CJK Compatibility Ideographs
        ):
            return True
    return False
