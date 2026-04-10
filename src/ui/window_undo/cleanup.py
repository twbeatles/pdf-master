import logging
import os
import time

logger = logging.getLogger(__name__)


def _normalize_backup_path(self, path: str) -> str:
    if not isinstance(path, str) or not path:
        return ""
    try:
        abs_path = os.path.abspath(path)
        backup_dir = os.path.abspath(self._undo_backup_dir)
        if os.path.commonpath([backup_dir, abs_path]) != backup_dir:
            return ""
        return abs_path
    except Exception:
        return ""


def _collect_active_backup_paths(self) -> set[str]:
    active_paths: set[str] = set()
    state_keys = ("backup_path", "before_backup_path", "after_backup_path")

    stacks = [getattr(self.undo_manager, "_undo_stack", []), getattr(self.undo_manager, "_redo_stack", [])]
    for stack in stacks:
        for record in stack:
            for state in (getattr(record, "before_state", {}), getattr(record, "after_state", {})):
                if not isinstance(state, dict):
                    continue
                for key in state_keys:
                    normalized = _normalize_backup_path(self, state.get(key, ""))
                    if normalized:
                        active_paths.add(normalized)

    pending_undo = getattr(self, "_pending_undo", None)
    if isinstance(pending_undo, dict):
        for key in ("before_backup_path", "after_backup_path"):
            normalized = _normalize_backup_path(self, pending_undo.get(key, ""))
            if normalized:
                active_paths.add(normalized)

    return active_paths

def _cleanup_old_undo_backups(self, max_age_hours: int = 24):
    """오래된 undo 백업 파일 정리

    Args:
        max_age_hours: 이 시간(시간 단위) 이상 된 파일 삭제
    """
    if not os.path.exists(self._undo_backup_dir):
        return

    current_time = time.time()
    max_age_seconds = max_age_hours * 3600
    cleaned_count = 0
    active_backups = _collect_active_backup_paths(self)

    try:
        for filename in os.listdir(self._undo_backup_dir):
            if not filename.startswith("undo_"):
                continue
            filepath = os.path.join(self._undo_backup_dir, filename)
            try:
                if os.path.abspath(filepath) in active_backups:
                    continue
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

    active_backups = _collect_active_backup_paths(self)

    cleaned_count = 0
    try:
        for filename in os.listdir(self._undo_backup_dir):
            if not filename.startswith("undo_"):
                continue
            filepath = os.path.join(self._undo_backup_dir, filename)
            if os.path.abspath(filepath) not in active_backups:
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
    active_backups = _collect_active_backup_paths(self)

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
                if os.path.abspath(bf["path"]) in active_backups:
                    continue
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
