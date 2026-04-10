from pathlib import Path

from _deps import require_pyqt6


class _ToastStub:
    def __init__(self, *_args, **_kwargs):
        pass

    def show_toast(self, _parent):
        return None


class _UndoHost:
    def __init__(self, backup_dir, undo_manager):
        self._undo_backup_dir = str(backup_dir)
        self.undo_manager = undo_manager
        self._pending_undo = None
        self.preview_updates = []

    def _update_preview(self, path):
        self.preview_updates.append(path)


def test_undo_redo_restores_before_and_after_snapshots(monkeypatch, tmp_path):
    require_pyqt6()
    import src.ui.window_undo.backup as backup_module
    from src.core.undo_manager import UndoManager
    from src.ui.main_window_undo import MainWindowUndoMixin

    monkeypatch.setattr(backup_module, "ToastWidget", _ToastStub)

    backup_dir = tmp_path / "undo"
    backup_dir.mkdir()
    target = tmp_path / "target.pdf"
    target.write_text("before", encoding="utf-8")

    class Host(_UndoHost, MainWindowUndoMixin):
        pass

    host = Host(backup_dir, UndoManager())
    before_backup = host._create_backup_for_undo(str(target))

    target.write_text("after", encoding="utf-8")
    after_backup = host._create_backup_for_undo(str(target))

    host.undo_manager.push(
        action_type="metadata_update",
        description="Update metadata",
        before_state={"before_backup_path": before_backup, "target_path": str(target)},
        after_state={"after_backup_path": after_backup, "target_path": str(target)},
        undo_callback=host._restore_from_backup,
        redo_callback=host._redo_from_output,
    )

    record = host.undo_manager.undo()
    assert record is not None
    assert target.read_text(encoding="utf-8") == "before"

    record = host.undo_manager.redo()
    assert record is not None
    assert target.read_text(encoding="utf-8") == "after"
    assert host.preview_updates == [str(target), str(target)]


def test_cleanup_unused_undo_backups_keeps_active_snapshots(monkeypatch, tmp_path):
    require_pyqt6()
    import src.ui.window_undo.backup as backup_module
    from src.core.undo_manager import UndoManager
    from src.ui.main_window_undo import MainWindowUndoMixin

    monkeypatch.setattr(backup_module, "ToastWidget", _ToastStub)

    backup_dir = tmp_path / "undo"
    backup_dir.mkdir()
    target = tmp_path / "target.pdf"
    target.write_text("before", encoding="utf-8")

    class Host(_UndoHost, MainWindowUndoMixin):
        pass

    host = Host(backup_dir, UndoManager())
    before_backup = Path(host._create_backup_for_undo(str(target)))
    target.write_text("after", encoding="utf-8")
    after_backup = Path(host._create_backup_for_undo(str(target)))

    host.undo_manager.push(
        action_type="rotate",
        description="Rotate pages",
        before_state={"before_backup_path": str(before_backup), "target_path": str(target)},
        after_state={"after_backup_path": str(after_backup), "target_path": str(target)},
        undo_callback=host._restore_from_backup,
        redo_callback=host._redo_from_output,
    )
    host._pending_undo = {
        "before_backup_path": str(before_backup),
        "after_backup_path": str(after_backup),
    }

    orphan = backup_dir / "undo_orphan_target.pdf"
    orphan.write_text("orphan", encoding="utf-8")

    host._cleanup_unused_undo_backups()
    assert before_backup.exists()
    assert after_backup.exists()
    assert not orphan.exists()

    extra = backup_dir / "undo_extra_target.pdf"
    extra.write_text("extra", encoding="utf-8")

    host._cleanup_undo_backups_by_size(max_size_mb=0)
    assert before_backup.exists()
    assert after_backup.exists()
    assert not extra.exists()

    host.undo_manager.clear()
    host._pending_undo = None
    host._cleanup_unused_undo_backups()
    assert not before_backup.exists()
    assert not after_backup.exists()
