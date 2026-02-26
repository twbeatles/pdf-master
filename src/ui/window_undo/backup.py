import logging
import os
import shutil
import time

from PyQt6.QtWidgets import QMessageBox

from ...core.i18n import tm

logger = logging.getLogger(__name__)

def _create_backup_for_undo(self, source_path: str) -> str:
    """작업 전 원본 파일 백업 생성"""
    if not source_path or not os.path.exists(source_path):
        return ""
    try:
        import uuid
        backup_name = f"undo_{uuid.uuid4().hex[:8]}_{os.path.basename(source_path)}"
        backup_path = os.path.join(self._undo_backup_dir, backup_name)
        shutil.copy2(source_path, backup_path)
        logger.debug(f"Created undo backup: {backup_path}")
        return backup_path
    except Exception as e:
        logger.warning(f"Failed to create backup: {e}")
        return ""

def _restore_from_backup(self, state: dict):
    """백업에서 파일 복원 (undo 콜백)"""
    backup_path = state.get("backup_path", "")
    target_path = state.get("target_path", "")
    if not backup_path or not target_path:
        logger.warning("Undo: Missing paths")
        return
    if not os.path.exists(backup_path):
        logger.warning(f"Undo: Backup not found: {backup_path}")
        QMessageBox.warning(self, tm.get("undo_failed_title"), tm.get("undo_backup_not_found"))
        return
    try:
        shutil.copy2(backup_path, target_path)
        logger.info(f"Restored from backup: {target_path}")
        # 미리보기 갱신
        self._update_preview(target_path)
        toast = ToastWidget(tm.get("restore_success"), toast_type='success', duration=2000)
        toast.show_toast(self)
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        QMessageBox.warning(self, tm.get("restore_failed_title"), tm.get("restore_failed_msg", str(e)))

def _redo_from_output(self, state: dict):
    """출력 파일로 다시 적용 (redo 콜백)"""
    output_path = state.get("output_path", "")
    target_path = state.get("target_path", "")
    if output_path and target_path and os.path.exists(output_path):
        try:
            shutil.copy2(output_path, target_path)
            logger.info(f"Redo applied: {target_path}")
            self._update_preview(target_path)
        except Exception as e:
            logger.error(f"Redo failed: {e}")
