import logging
import os
import shutil

from PyQt6.QtWidgets import QMessageBox

from ..core.i18n import tm
from .widgets import ToastWidget

logger = logging.getLogger(__name__)


class MainWindowUndoMixin:

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

    def _register_undo_action(self, action_type: str, description: str, 
                              source_path: str, output_path: str):
        """작업을 undo 히스토리에 등록"""
        backup_path = self._create_backup_for_undo(source_path)
        if not backup_path:
            logger.warning(f"Skipping undo registration for {action_type}: no backup")
            return
        
        before_state = {
            "backup_path": backup_path,
            "target_path": output_path
        }
        after_state = {
            "output_path": output_path,
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

    def _cleanup_old_undo_backups(self, max_age_hours: int = 24):
        """오래된 undo 백업 파일 정리
        
        Args:
            max_age_hours: 이 시간(시간 단위) 이상 된 파일 삭제
        """
        if not os.path.exists(self._undo_backup_dir):
            return
        
        import time
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        cleaned_count = 0
        
        try:
            for filename in os.listdir(self._undo_backup_dir):
                if not filename.startswith("undo_"):
                    continue
                filepath = os.path.join(self._undo_backup_dir, filename)
                try:
                    file_age = current_time - os.path.getmtime(filepath)
                    if file_age > max_age_seconds:
                        os.remove(filepath)
                        cleaned_count += 1
                except Exception as e:
                    logger.debug(f"Failed to remove old backup {filename}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old undo backup files")
        except Exception as e:
            logger.warning(f"Error during backup cleanup: {e}")

    def _cleanup_unused_undo_backups(self):
        """현재 undo 스택에 없는 백업 파일 정리"""
        if not os.path.exists(self._undo_backup_dir):
            return
        
        # 현재 undo/redo 스택에서 사용 중인 백업 경로 수집
        active_backups = set()
        for record in self.undo_manager._undo_stack:
            backup = record.before_state.get("backup_path", "")
            if backup:
                active_backups.add(os.path.basename(backup))
        for record in self.undo_manager._redo_stack:
            backup = record.before_state.get("backup_path", "")
            if backup:
                active_backups.add(os.path.basename(backup))
        
        cleaned_count = 0
        try:
            for filename in os.listdir(self._undo_backup_dir):
                if not filename.startswith("undo_"):
                    continue
                if filename not in active_backups:
                    filepath = os.path.join(self._undo_backup_dir, filename)
                    try:
                        os.remove(filepath)
                        cleaned_count += 1
                    except Exception as e:
                        logger.debug(f"Failed to remove unused backup {filename}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} unused undo backup files")
        except Exception as e:
            logger.warning(f"Error during unused backup cleanup: {e}")

    def _cleanup_undo_backups_by_size(self, max_size_mb: int = 500):
        """v4.5: 백업 폴더 용량 제한으로 오래된 파일부터 삭제
        
        Args:
            max_size_mb: 허용 최대 크기 (MB)
        """
        if not os.path.exists(self._undo_backup_dir):
            return
        
        max_size_bytes = max_size_mb * 1024 * 1024
        
        try:
            # 백업 파일들과 정보 수집
            backup_files = []
            total_size = 0
            
            for filename in os.listdir(self._undo_backup_dir):
                if not filename.startswith("undo_"):
                    continue
                filepath = os.path.join(self._undo_backup_dir, filename)
                try:
                    stat_info = os.stat(filepath)
                    backup_files.append({
                        'path': filepath,
                        'size': stat_info.st_size,
                        'mtime': stat_info.st_mtime
                    })
                    total_size += stat_info.st_size
                except Exception:
                    continue
            
            # 용량 초과 시 오래된 파일부터 삭제
            if total_size > max_size_bytes:
                # 오래된 순 정렬
                backup_files.sort(key=lambda x: x['mtime'])
                cleaned_count = 0
                
                for bf in backup_files:
                    if total_size <= max_size_bytes:
                        break
                    try:
                        os.remove(bf['path'])
                        total_size -= bf['size']
                        cleaned_count += 1
                    except Exception:
                        pass
                
                if cleaned_count > 0:
                    logger.info(f"Cleaned up {cleaned_count} backup files (size limit {max_size_mb}MB)")
        
        except Exception as e:
            logger.warning(f"Error during size-based backup cleanup: {e}")

    # ===================== Tab 1: 병합 =====================
