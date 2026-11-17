"""security 탭 구현."""

from __future__ import annotations

from .actions import (
    _load_metadata,
    action_compress,
    action_metadata,
    action_protect,
    action_unlock,
    action_watermark,
)
from .setup import setup_edit_sec_tab

__all__ = [
    "setup_edit_sec_tab",
    "_load_metadata",
    "action_metadata",
    "action_watermark",
    "action_protect",
    "action_unlock",
    "action_compress",
]
