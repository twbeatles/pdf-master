from .backup import _create_backup_for_undo, _redo_from_output, _restore_from_backup
from .cleanup import (
    _cleanup_old_undo_backups,
    _cleanup_undo_backups_by_size,
    _cleanup_unused_undo_backups,
)
from .history import _redo_action, _register_undo_action, _undo_action


class MainWindowUndoMixin:
    _undo_action = _undo_action
    _redo_action = _redo_action
    _create_backup_for_undo = _create_backup_for_undo
    _restore_from_backup = _restore_from_backup
    _redo_from_output = _redo_from_output
    _register_undo_action = _register_undo_action
    _cleanup_old_undo_backups = _cleanup_old_undo_backups
    _cleanup_unused_undo_backups = _cleanup_unused_undo_backups
    _cleanup_undo_backups_by_size = _cleanup_undo_backups_by_size
