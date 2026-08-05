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

def _textbox_queue_ensure(self) -> list:
    return _textbox_session(self).queue

def _textbox_norm_path(path: str) -> str:
    from ...textbox_session import _norm_path

    return _norm_path(path)

def _textbox_sync_queue_ghost(self) -> None:
    """큐 고스트 오버레이를 미리보기에 반영."""
    preview = getattr(self, "preview_image", None)
    if preview is None or not hasattr(preview, "set_queue_ghost_boxes"):
        return
    sess = _textbox_session(self)
    preview.set_queue_ghost_boxes(sess.queue_snapshot())

def _textbox_queue_refresh_list(self) -> None:
    lst = getattr(self, "lst_tb_queue", None)
    q = _textbox_queue_ensure(self)
    if lst is not None and hasattr(lst, "clear"):
        lst.clear()
        for i, item in enumerate(q, start=1):
            page = int(item.get("page_num", 0)) + 1
            text = str(item.get("text", ""))[:40].replace("\n", " ")
            rect = item.get("rect") or [0, 0, 0, 0]
            stem = str(item.get("file_path", "") or "")
            if stem:
                import os

                stem = os.path.basename(stem)
            label = f"{i}. [{stem or '?'}] p{page} ({rect[0]:.0f},{rect[1]:.0f}) {text}"
            if hasattr(lst, "addItem"):
                lst.addItem(label)
    lbl = getattr(self, "lbl_tb_queue_count", None)
    if lbl is not None and hasattr(lbl, "setText"):
        lbl.setText(deps.tm.get("hint_textbox_queue_count", len(q)))
    _textbox_sync_queue_ghost(self)

def action_textbox_queue_add(self):
    """현재 좌표·텍스트를 다중 삽입 큐에 추가 (파일 경로 고정)."""
    path = self.sel_textbox.get_path() if hasattr(self, "sel_textbox") else ""
    style = _textbox_style_kwargs(self)
    if not path:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("msg_select_pdf"))
    if not style["text"]:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("msg_enter_text"))
    page_num, rect = _textbox_current_rect_and_page(self)
    sess = _textbox_session(self)
    if sess.path_mismatch_with(path):
        reply = deps.QMessageBox.question(
            self,
            deps.tm.get("confirm"),
            deps.tm.get("msg_confirm_textbox_queue_path_mismatch"),
            deps.QMessageBox.StandardButton.Yes | deps.QMessageBox.StandardButton.No,
        )
        if reply != deps.QMessageBox.StandardButton.Yes:
            return None
        sess.clear_queue()
    item = {
        "file_path": path,
        "page_num": page_num,
        "rect": rect,
        **style,
    }
    n = sess.add_box(item)
    self._textbox_queue = sess.queue
    _textbox_queue_refresh_list(self)
    deps.ToastWidget(deps.tm.get("msg_textbox_queued", n), toast_type="success", duration=1800).show_toast(self)
    return None

def action_textbox_queue_clear(self):
    sess = _textbox_session(self)
    sess.clear_queue()
    self._textbox_queue = sess.queue
    _textbox_queue_refresh_list(self)

def action_textbox_queue_commit(self):
    """큐에 쌓인 텍스트 상자를 일괄 삽입."""
    path = self.sel_textbox.get_path() if hasattr(self, "sel_textbox") else ""
    sess = _textbox_session(self)
    q = sess.queue_snapshot()
    if not path:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("msg_select_pdf"))
    err_key = sess.commit_path_error(path)
    if err_key:
        return deps.QMessageBox.warning(self, deps.tm.get("error" if err_key != "err_textbox_queue_empty" else "info"), deps.tm.get(err_key))
    queued_path = str(q[0].get("file_path", "") or "")
    out = _textbox_resolve_output_path(self, queued_path, destructive=False)
    if not out:
        return None
    keep = _textbox_should_keep_placing(self)
    sess.set_post_flags(reopen=keep, clear_queue=True)
    self._textbox_reopen_placement_after_success = sess.reopen_after_success
    self._textbox_clear_queue_after_success = sess.clear_queue_after_success
    self.run_worker(
        "insert_textboxes",
        file_path=queued_path,
        output_path=out,
        boxes=q,
    )
    return None
