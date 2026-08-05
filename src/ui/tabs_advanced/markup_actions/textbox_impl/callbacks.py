"""텍스트상자 UI 액션 구현 (SOLID 분할)."""
from __future__ import annotations

from .. import deps
from .coords_style import (
    _clear_textbox_post_flags,
    _set_textbox_content_text,
    _textbox_session,
    _textbox_should_keep_placing,
)
from .placement import action_start_textbox_region_select
from .queue import _textbox_queue_refresh_list

def _on_textbox_worker_success(self) -> None:
    """삽입/교체 성공 후 큐 정리 및 연속 배치 재개."""
    sess = _textbox_session(self)
    clear_q = bool(sess.clear_queue_after_success) or bool(
        getattr(self, "_textbox_clear_queue_after_success", False)
    )
    reopen = bool(sess.reopen_after_success) or bool(
        getattr(self, "_textbox_reopen_placement_after_success", False)
    )
    # 성공 시에도 플래그는 즉시 소비 (재진입 방지)
    _clear_textbox_post_flags(self)
    if clear_q:
        sess.clear_queue()
        self._textbox_queue = sess.queue
        _textbox_queue_refresh_list(self)
    if reopen and _textbox_should_keep_placing(self):
        from PyQt6.QtCore import QTimer

        QTimer.singleShot(150, lambda: action_start_textbox_region_select(self))

def _on_extract_text_in_rect_success(self, payload: dict) -> None:
    """extract_text_in_rect Worker 결과 → 본문 필드 반영."""
    text = str(payload.get("text", "") or "")
    if text:
        _set_textbox_content_text(self, text)
    sess = _textbox_session(self)
    sess.pending_extract = None
    deps.ToastWidget(deps.tm.get("msg_textbox_replace_region_ready"), toast_type="info", duration=2500).show_toast(self)
