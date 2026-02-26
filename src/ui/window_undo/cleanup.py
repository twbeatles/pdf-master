import logging
import os
import shutil
import time

from PyQt6.QtWidgets import QMessageBox

from ...core.i18n import tm

logger = logging.getLogger(__name__)

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
