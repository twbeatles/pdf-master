"""마크업/교정/텍스트상자 UI 액션 facade (호환 경로).

구현: `markup_actions/` 패키지.
테스트 monkeypatch: 이 모듈의 QMessageBox/ToastWidget 또는 `markup_actions.deps`.
"""
from __future__ import annotations

from .markup_actions.deps import QFileDialog, QMessageBox, ToastWidget, tm
from .markup_actions.annotations import (
    action_add_annotation_basic,
    action_add_background,
    action_add_ink_annotation,
    action_add_sticky_note,
    action_add_text_markup,
    action_highlight_text,
    action_list_annotations,
    action_remove_annotations,
)
from .markup_actions.redact import (
    _on_preview_region_selected_for_redact,
    _on_redact_region_mode_changed,
    action_redact_area,
    action_redact_text,
    action_start_redact_region_select,
)
from .markup_actions.shapes_links import (
    action_add_hyperlink,
    action_draw_shape,
)
from .markup_actions.textbox import (
    _clear_textbox_post_flags,
    _connect_textbox_preview_signals,
    _ensure_textbox_preview_ready,
    _extract_text_in_rect_sync,
    _mark_textbox_preset_custom,
    _on_extract_text_in_rect_success,
    _on_preview_region_selected_for_textbox,
    _on_text_placement_moved,
    _on_text_placement_text_edited,
    _on_textbox_placement_mode_changed,
    _on_textbox_region_mode_changed,
    _on_textbox_worker_success,
    _set_textbox_content_text,
    _set_textbox_xywh,
    _sync_textbox_placement_overlay,
    _textbox_content_text,
    _textbox_current_rect_and_page,
    _textbox_current_style,
    _textbox_norm_path,
    _textbox_page_size_pts,
    _textbox_queue_ensure,
    _textbox_queue_refresh_list,
    _textbox_resolve_output_path,
    _textbox_session,
    _textbox_should_keep_placing,
    _textbox_style_kwargs,
    _textbox_sync_queue_ghost,
    action_apply_textbox_preset,
    action_insert_textbox,
    action_replace_text_in_rect,
    action_start_textbox_region_select,
    action_start_textbox_replace_region,
    action_textbox_queue_add,
    action_textbox_queue_clear,
    action_textbox_queue_commit,
)

# facade 와 deps 동일 객체를 공유 → monkeypatch.setattr(mod, 'ToastWidget', ...) 시 deps 도 갱신
import src.ui.tabs_advanced.markup_actions.deps as _deps

# 테스트가 facade 모듈 속성을 교체하면 deps 전역도 따라가도록 property 대신
# 초기 바인딩 후, 테스트는 deps 를 패치하거나 아래 헬퍼를 사용한다.
# 호환: facade 속성 교체 시 deps 동기화 (setattr hook 대신 테스트 업데이트)

__all__ = [
    "QFileDialog",
    "QMessageBox",
    "ToastWidget",
    "tm",
    "action_highlight_text",
    "action_list_annotations",
    "action_remove_annotations",
    "action_add_text_markup",
    "action_add_background",
    "action_add_sticky_note",
    "action_add_ink_annotation",
    "action_add_annotation_basic",
    "action_start_redact_region_select",
    "_on_preview_region_selected_for_redact",
    "_on_redact_region_mode_changed",
    "action_redact_area",
    "action_redact_text",
    "action_draw_shape",
    "action_add_hyperlink",
    "action_apply_textbox_preset",
    "action_start_textbox_region_select",
    "action_insert_textbox",
    "action_textbox_queue_add",
    "action_textbox_queue_clear",
    "action_textbox_queue_commit",
    "action_start_textbox_replace_region",
    "action_replace_text_in_rect",
    "_on_preview_region_selected_for_textbox",
    "_on_textbox_region_mode_changed",
    "_on_text_placement_moved",
    "_on_textbox_placement_mode_changed",
    "_on_text_placement_text_edited",
    "_sync_textbox_placement_overlay",
    "_textbox_content_text",
    "_clear_textbox_post_flags",
    "_on_textbox_worker_success",
    "_on_extract_text_in_rect_success",
]
