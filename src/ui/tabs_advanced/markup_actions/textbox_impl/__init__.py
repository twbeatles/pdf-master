"""텍스트상자 UI 액션 구현 패키지."""
from __future__ import annotations

from .coords_style import (
    _textbox_page_size_pts,
    _set_textbox_xywh,
    _mark_textbox_preset_custom,
    action_apply_textbox_preset,
    _textbox_content_text,
    _set_textbox_content_text,
    _on_text_placement_text_edited,
    _textbox_style_kwargs,
    _textbox_current_rect_and_page,
    _textbox_resolve_output_path,
    _textbox_should_keep_placing,
    _textbox_session,
    _clear_textbox_post_flags,
    _textbox_current_style,
)

from .placement import (
    _ensure_textbox_preview_ready,
    _connect_textbox_preview_signals,
    action_start_textbox_region_select,
    _on_text_placement_moved,
    _on_textbox_placement_mode_changed,
    _sync_textbox_placement_overlay,
    _on_preview_region_selected_for_textbox,
    _extract_text_in_rect_sync,
    _on_textbox_region_mode_changed,
)

from .queue import (
    _textbox_queue_ensure,
    _textbox_norm_path,
    _textbox_sync_queue_ghost,
    _textbox_queue_refresh_list,
    action_textbox_queue_add,
    action_textbox_queue_clear,
    action_textbox_queue_commit,
)

from .actions import (
    action_insert_textbox,
    action_start_textbox_replace_region,
    action_replace_text_in_rect,
)

from .callbacks import (
    _on_textbox_worker_success,
    _on_extract_text_in_rect_success,
)

__all__ = [
    "_textbox_page_size_pts",
    "_set_textbox_xywh",
    "_mark_textbox_preset_custom",
    "action_apply_textbox_preset",
    "_textbox_content_text",
    "_set_textbox_content_text",
    "_on_text_placement_text_edited",
    "_textbox_style_kwargs",
    "_textbox_current_rect_and_page",
    "_textbox_resolve_output_path",
    "_textbox_should_keep_placing",
    "_textbox_session",
    "_clear_textbox_post_flags",
    "_textbox_current_style",
    "_ensure_textbox_preview_ready",
    "_connect_textbox_preview_signals",
    "action_start_textbox_region_select",
    "_on_text_placement_moved",
    "_on_textbox_placement_mode_changed",
    "_sync_textbox_placement_overlay",
    "_on_preview_region_selected_for_textbox",
    "_extract_text_in_rect_sync",
    "_on_textbox_region_mode_changed",
    "_textbox_queue_ensure",
    "_textbox_norm_path",
    "_textbox_sync_queue_ghost",
    "_textbox_queue_refresh_list",
    "action_textbox_queue_add",
    "action_textbox_queue_clear",
    "action_textbox_queue_commit",
    "action_insert_textbox",
    "action_start_textbox_replace_region",
    "action_replace_text_in_rect",
    "_on_textbox_worker_success",
    "_on_extract_text_in_rect_success",
]
