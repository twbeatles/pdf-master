from ...core.i18n import tm
from ..widgets import ToastWidget


def _undo_action(self):
    """실행 취소"""
    if self.undo_manager.can_undo:
        record = self.undo_manager.undo()
        if record:
            msg = tm.get("undo_action", record.description)
            self.status_label.setText(msg)
            toast = ToastWidget(msg, toast_type="info", duration=2000)
            toast.show_toast(self)
    else:
        self.status_label.setText(tm.get("undo_empty"))


def _redo_action(self):
    """다시 실행"""
    if self.undo_manager.can_redo:
        record = self.undo_manager.redo()
        if record:
            msg = tm.get("redo_action", record.description)
            self.status_label.setText(msg)
            toast = ToastWidget(msg, toast_type="info", duration=2000)
            toast.show_toast(self)
    else:
        self.status_label.setText(tm.get("redo_empty"))


# NOTE(S2-ISSUE-004): 즉시 백업 방식의 _register_undo_action은 데드코드라 제거했다.
# 유일 등록 경로는 window_worker/success.py::apply_undo_registration + _pending_undo다.
