from ...core.i18n import tm
from ...core.undo_manager import UndoRestoreError
from ..widgets import ToastWidget


def _undo_action(self):
    """실행 취소 (복원 실패 시 스택 유지 + 상태 표시, ISSUE-004)."""
    if self.undo_manager.can_undo:
        try:
            record = self.undo_manager.undo()
        except UndoRestoreError:
            # 다이얼로그는 복원 콜백이 이미 표시 — 여기서는 상태만 표시
            self.status_label.setText(tm.get("restore_failed_title"))
            return
        if record:
            msg = tm.get("undo_action", record.description)
            self.status_label.setText(msg)
            toast = ToastWidget(msg, toast_type="info", duration=2000)
            toast.show_toast(self)
    else:
        self.status_label.setText(tm.get("undo_empty"))


def _redo_action(self):
    """다시 실행 (복원 실패 시 스택 유지 + 상태 표시, ISSUE-004)."""
    if self.undo_manager.can_redo:
        try:
            record = self.undo_manager.redo()
        except UndoRestoreError:
            self.status_label.setText(tm.get("restore_failed_title"))
            return
        if record:
            msg = tm.get("redo_action", record.description)
            self.status_label.setText(msg)
            toast = ToastWidget(msg, toast_type="info", duration=2000)
            toast.show_toast(self)
    else:
        self.status_label.setText(tm.get("redo_empty"))


# NOTE(S2-ISSUE-004): 즉시 백업 방식의 _register_undo_action은 데드코드라 제거했다.
# 유일 등록 경로는 window_worker/success.py::apply_undo_registration + _pending_undo다.
