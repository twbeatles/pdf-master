import logging
import os

from ...core.i18n import tm
from ..widgets import ToastWidget

logger = logging.getLogger(__name__)

def _undo_action(self):
    """실행 취소"""
    if self.undo_manager.can_undo:
        record = self.undo_manager.undo()
        if record:
            msg = tm.get("undo_action", record.description)
            self.status_label.setText(msg)
            toast = ToastWidget(msg, toast_type='info', duration=2000)
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
            toast = ToastWidget(msg, toast_type='info', duration=2000)
            toast.show_toast(self)
    else:
        self.status_label.setText(tm.get("redo_empty"))

def _register_undo_action(self, action_type: str, description: str, 
                          source_path: str, output_path: str):
    """작업을 undo 히스토리에 등록"""
    before_backup_path = self._create_backup_for_undo(source_path)
    if not before_backup_path:
        logger.warning(f"Skipping undo registration for {action_type}: no backup")
        return

    after_backup_path = self._create_backup_for_undo(output_path)
    if not after_backup_path:
        logger.warning(f"Skipping undo registration for {action_type}: no after snapshot")
        try:
            os.remove(before_backup_path)
        except Exception:
            logger.debug("Failed to remove orphaned undo backup", exc_info=True)
        return

    before_state = {
        "before_backup_path": before_backup_path,
        "target_path": output_path
    }
    after_state = {
        "after_backup_path": after_backup_path,
        "target_path": output_path
    }

    self.undo_manager.push(
        action_type=action_type,
        description=description,
        before_state=before_state,
        after_state=after_state,
        undo_callback=self._restore_from_backup,
        redo_callback=self._redo_from_output
    )
