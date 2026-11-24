"""ISSUE-004: Undo/Redo 복원 실패는 스택을 움직이지 않아야 한다."""

from __future__ import annotations

from pathlib import Path

import pytest
from _deps import require_pyside6


class _ToastStub:
    def __init__(self, *_args, **_kwargs):
        pass

    def show_toast(self, _parent):
        return None


class _LabelStub:
    def __init__(self):
        self.texts: list[str] = []

    def setText(self, text):
        self.texts.append(text)


def _make_host(tmp_path: Path, monkeypatch):
    require_pyside6()
    import src.ui.window_undo.backup as backup_module
    from src.ui.main_window_undo import MainWindowUndoMixin

    monkeypatch.setattr(backup_module, "ToastWidget", _ToastStub)
    monkeypatch.setattr(backup_module.QMessageBox, "warning", lambda *a, **k: 0)

    backup_dir = tmp_path / "undo"
    backup_dir.mkdir(exist_ok=True)

    class Host(MainWindowUndoMixin):
        def __init__(self):
            from src.core.undo_manager import UndoManager

            self._undo_backup_dir = str(backup_dir)
            self.undo_manager = UndoManager()
            self.status_label = _LabelStub()

        def _update_preview(self, path, restore_state=None):
            return None

    return Host()


def _push_missing_backup_record(host, target: str):
    host.undo_manager.push(
        action_type="metadata_update",
        description="Update metadata",
        before_state={
            "before_backup_path": "/nonexistent/before.pdf",
            "target_path": target,
        },
        after_state={
            "after_backup_path": "/nonexistent/after.pdf",
            "target_path": target,
        },
        undo_callback=host._restore_from_backup,
        redo_callback=host._redo_from_output,
    )


def test_undo_with_missing_backup_raises_and_keeps_stacks(monkeypatch, tmp_path):
    from src.core.undo_manager import UndoRestoreError

    host = _make_host(tmp_path, monkeypatch)
    target = str(tmp_path / "target.pdf")
    Path(target).write_text("current", encoding="utf-8")
    _push_missing_backup_record(host, target)

    with pytest.raises(UndoRestoreError):
        host.undo_manager.undo()

    assert host.undo_manager.can_undo
    assert not host.undo_manager.can_redo
    assert Path(target).read_text(encoding="utf-8") == "current"


def test_redo_with_missing_backup_raises_and_keeps_stacks(monkeypatch, tmp_path):
    from src.core.undo_manager import UndoRestoreError

    host = _make_host(tmp_path, monkeypatch)
    target = str(tmp_path / "target.pdf")
    Path(target).write_text("current", encoding="utf-8")
    _push_missing_backup_record(host, target)

    # redo 스택으로 직접 이동 후 redo 시도
    record = host.undo_manager._undo_stack.pop()
    host.undo_manager._redo_stack.append(record)

    with pytest.raises(UndoRestoreError):
        host.undo_manager.redo()

    assert host.undo_manager.can_redo
    assert not host.undo_manager.can_undo
    assert Path(target).read_text(encoding="utf-8") == "current"


def test_undo_action_handles_restore_failure_without_raise(monkeypatch, tmp_path):
    host = _make_host(tmp_path, monkeypatch)
    target = str(tmp_path / "target.pdf")
    Path(target).write_text("current", encoding="utf-8")
    _push_missing_backup_record(host, target)

    host._undo_action()

    assert host.undo_manager.can_undo
    assert not host.undo_manager.can_redo
    assert host.status_label.texts, "failure status was not shown"
