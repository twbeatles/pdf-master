"""PDF helpers: diff_sample."""
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

def _sample_diff_text(lines: list[str], max_items: int = 2) -> str:
    visible = [line.strip() for line in lines if isinstance(line, str) and line.strip()]
    return " | ".join(visible[:max_items]) if visible else "∅"
