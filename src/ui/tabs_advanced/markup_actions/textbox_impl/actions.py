"""텍스트상자 UI 액션 구현 (SOLID 분할)."""
from __future__ import annotations

from .. import deps
from .coords_style import (
    _textbox_current_rect_and_page,
    _textbox_resolve_output_path,
    _textbox_session,
    _textbox_should_keep_placing,
    _textbox_style_kwargs,
)
from .placement import (
    _connect_textbox_preview_signals,
    _ensure_textbox_preview_ready,
)

def action_insert_textbox(self):
    """텍스트 상자 삽입 (same-path / 연속 배치 옵션 지원)."""
    path = self.sel_textbox.get_path() if hasattr(self, "sel_textbox") else ""
    style = _textbox_style_kwargs(self)
    text = style["text"]

    if not path:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("msg_select_pdf"))
    if not text:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("msg_enter_text"))

    preview = getattr(self, "preview_image", None)
    keep = _textbox_should_keep_placing(self)
    if preview is not None:
        if hasattr(preview, "is_region_select_mode") and preview.is_region_select_mode():
            preview.set_region_select_mode(False)
        # same-path 저장 전 미리보기가 닫히므로 배치는 항상 종료 후 성공 시 재개
        if hasattr(preview, "is_text_placement_mode") and preview.is_text_placement_mode():
            preview.set_text_placement_mode(False)

    page_num, rect = _textbox_current_rect_and_page(self)
    out = _textbox_resolve_output_path(self, path, destructive=False)
    if not out:
        return None

    sess = _textbox_session(self)
    sess.set_post_flags(reopen=keep, clear_queue=False)
    self._textbox_reopen_placement_after_success = sess.reopen_after_success
    self._textbox_clear_queue_after_success = sess.clear_queue_after_success
    self.run_worker(
        "insert_textbox",
        file_path=path,
        output_path=out,
        page_num=page_num,
        rect=rect,
        text=text,
        fontsize=style["fontsize"],
        color=style["color"],
        fontname=style["fontname"],
        opacity=style["opacity"],
        rotation=style["rotation"],
        align=style["align"],
        layer=style["layer"],
    )

def action_start_textbox_replace_region(self):
    """실험: 영역 드래그 후 기존 텍스트 교체 준비."""
    path = self.sel_textbox.get_path() if hasattr(self, "sel_textbox") else ""
    if not path:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("msg_select_pdf"))
    preview = _ensure_textbox_preview_ready(self, path)
    if preview is None or not hasattr(preview, "set_region_select_mode"):
        return deps.QMessageBox.warning(
            self, deps.tm.get("warning"), deps.tm.get("err_textbox_drag_preview_unavailable")
        )
    _connect_textbox_preview_signals(self, preview)
    if preview.is_region_select_mode() and getattr(self, "_region_select_target", None) == "textbox_replace":
        preview.set_region_select_mode(False)
        self._region_select_target = None
        if hasattr(self, "lbl_tb_drag_hint"):
            self.lbl_tb_drag_hint.setText(deps.tm.get("hint_textbox_drag_idle"))
        return None
    if hasattr(preview, "is_text_placement_mode") and preview.is_text_placement_mode():
        preview.set_text_placement_mode(False)
    self._region_select_target = "textbox_replace"
    preview.set_region_select_mode(True)
    if hasattr(self, "lbl_tb_drag_hint"):
        self.lbl_tb_drag_hint.setText(deps.tm.get("hint_textbox_replace_drag_active"))
    deps.ToastWidget(deps.tm.get("msg_textbox_replace_drag_started"), toast_type="info", duration=2500).show_toast(self)
    return None

def action_replace_text_in_rect(self):
    """선택된 영역(좌표)의 기존 내용을 교정 후 새 텍스트 삽입."""
    path = self.sel_textbox.get_path() if hasattr(self, "sel_textbox") else ""
    style = _textbox_style_kwargs(self)
    if not path:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("msg_select_pdf"))
    if not style["text"]:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("msg_enter_text"))
    page_num, rect = _textbox_current_rect_and_page(self)
    out = _textbox_resolve_output_path(self, path, destructive=True)
    if not out:
        return None
    reply = deps.QMessageBox.question(
        self,
        deps.tm.get("confirm"),
        deps.tm.get("msg_confirm_replace_text_in_rect"),
        deps.QMessageBox.StandardButton.Yes | deps.QMessageBox.StandardButton.No,
    )
    if reply != deps.QMessageBox.StandardButton.Yes:
        return None
    preview = getattr(self, "preview_image", None)
    if preview is not None:
        if hasattr(preview, "is_region_select_mode") and preview.is_region_select_mode():
            preview.set_region_select_mode(False)
        if hasattr(preview, "is_text_placement_mode") and preview.is_text_placement_mode():
            preview.set_text_placement_mode(False)
    sess = _textbox_session(self)
    keep = _textbox_should_keep_placing(self)
    sess.set_post_flags(reopen=keep, clear_queue=False)
    self._textbox_reopen_placement_after_success = sess.reopen_after_success
    self._textbox_clear_queue_after_success = sess.clear_queue_after_success
    self.run_worker(
        "replace_text_in_rect",
        file_path=path,
        output_path=out,
        page_num=page_num,
        rect=rect,
        text=style["text"],
        fontsize=style["fontsize"],
        color=style["color"],
        fontname=style["fontname"],
        opacity=style["opacity"],
        rotation=style["rotation"],
        align=style["align"],
        layer=style["layer"],
    )
    return None
