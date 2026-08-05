"""보안/편집 탭 facade."""
from __future__ import annotations

from .security_impl import (
    setup_edit_sec_tab,
    _load_metadata,
    action_metadata,
    action_watermark,
    action_protect,
    action_unlock,
    action_compress,
)

__all__ = ['setup_edit_sec_tab', '_load_metadata', 'action_metadata', 'action_watermark', 'action_protect', 'action_unlock', 'action_compress']
