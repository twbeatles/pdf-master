from __future__ import annotations

from ...core.path_utils import normalize_path_key
from .helpers import _collect_payload_input_paths, _delete_undo_backup_file


def _discard_pending_undo(self, delete_backups: bool = False):
    undo_info = getattr(self, "_pending_undo", None)
    self._pending_undo = None
    if not undo_info or not delete_backups:
        return
    _delete_undo_backup_file(undo_info.get("before_backup_path", ""))
    _delete_undo_backup_file(undo_info.get("after_backup_path", ""))

def _augment_worker_passwords_from_preview(self, kwargs: dict) -> None:
    preview_password = getattr(self, "_current_preview_password", None)
    if not isinstance(preview_password, str) or not preview_password:
        return
    preview_path = normalize_path_key(getattr(self, "_current_preview_path", ""))
    if not preview_path or preview_path not in _collect_payload_input_paths(kwargs):
        return
    passwords = kwargs.get("passwords")
    if not isinstance(passwords, dict):
        passwords = {}
        kwargs["passwords"] = passwords
    passwords.setdefault(preview_path, preview_password)
