from __future__ import annotations

from src.core import update_installer


def test_invalid_update_paths_write_a_consumable_failure(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert update_installer.apply_update("missing.exe", "staged.exe", 0) == 2
    result = update_installer.consume_update_result()
    assert result is not None
    assert result["status"] == "failed"
    assert update_installer.consume_update_result() is None


def test_stage_root_is_scoped_to_local_app_data(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert update_installer.update_root() == tmp_path / "PDFMaster" / "updates"


def test_parent_alive_permission_error_waits_for_exit(monkeypatch, tmp_path) -> None:
    """os.kill PermissionError(살아있음)를 종료로 오인하면 실행 중 교체 → 액세스 거부."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(update_installer, "PARENT_WAIT_MAX_ATTEMPTS", 3)
    monkeypatch.setattr(update_installer.time, "sleep", lambda *_a, **_k: None)
    calls = {"kill": 0}

    def _alive(pid, sig):
        calls["kill"] += 1
        raise PermissionError(13, "Access is denied")

    monkeypatch.setattr(update_installer.os, "kill", _alive)
    target = tmp_path / "app.exe"
    staged = tmp_path / "staged.exe"
    target.write_bytes(b"old-exe")
    staged.write_bytes(b"new-exe")
    assert update_installer.apply_update(str(target), str(staged), 999999) == 3
    assert calls["kill"] == 3
    assert target.read_bytes() == b"old-exe"


def test_replace_transient_lock_is_retried(monkeypatch, tmp_path) -> None:
    """백신/인덱서 잠금(첫 시도 공유 위반)은 재시도 후 성공해야 한다."""
    import os as _os

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(update_installer, "REPLACE_MAX_ATTEMPTS", 3)
    monkeypatch.setattr(update_installer.time, "sleep", lambda *_a, **_k: None)
    monkeypatch.setattr(update_installer.os, "kill", lambda pid, sig: (_ for _ in ()).throw(OSError("gone")))

    real_replace = _os.replace
    attempts = {"n": 0}

    def _flaky(src, dst):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise PermissionError(13, "Access is denied (sharing violation)")
        return real_replace(src, dst)

    monkeypatch.setattr(update_installer.os, "replace", _flaky)

    class _Completed:
        returncode = 0

    monkeypatch.setattr(update_installer.subprocess, "run", lambda *a, **k: _Completed())
    monkeypatch.setattr(update_installer.subprocess, "Popen", lambda *a, **k: None)
    target = tmp_path / "app.exe"
    staged = tmp_path / "staged.exe"
    target.write_bytes(b"old-exe")
    staged.write_bytes(b"new-exe")
    assert update_installer.apply_update(str(target), str(staged), 123456) == 0
    assert target.read_bytes() == b"new-exe"


def test_nonwritable_target_delegates_to_elevated_helper(monkeypatch, tmp_path) -> None:
    """Program Files 등 보호 위치에서는 UAC 상승 인스턴스에 위임하고 결과 파일을 남기지 않는다."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(update_installer.os, "kill", lambda pid, sig: (_ for _ in ()).throw(OSError("gone")))
    monkeypatch.setattr(update_installer, "_target_dir_writable", lambda _p: False)
    delegated = {}
    monkeypatch.setattr(
        update_installer,
        "_relaunch_elevated",
        lambda *, target, staged, parent_pid: delegated.setdefault("args", (target, staged, parent_pid)) or True,
    )
    target = tmp_path / "app.exe"
    staged = tmp_path / "staged.exe"
    target.write_bytes(b"old-exe")
    staged.write_bytes(b"new-exe")
    assert update_installer.apply_update(str(target), str(staged), 123456) == 5
    assert staged.read_bytes() == b"new-exe"
    assert not update_installer.update_result_path().exists()


def test_nonwritable_target_elevation_declined_keeps_staged(monkeypatch, tmp_path) -> None:
    """상승 실패 시에는 staged를 보존하고 수동 설치 안내를 결과에 남긴다."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(update_installer.os, "kill", lambda pid, sig: (_ for _ in ()).throw(OSError("gone")))
    monkeypatch.setattr(update_installer, "_target_dir_writable", lambda _p: False)
    monkeypatch.setattr(update_installer, "_relaunch_elevated", lambda *, target, staged, parent_pid: False)
    target = tmp_path / "app.exe"
    staged = tmp_path / "staged.exe"
    target.write_bytes(b"old-exe")
    staged.write_bytes(b"new-exe")
    assert update_installer.apply_update(str(target), str(staged), 123456) == 4
    assert target.read_bytes() == b"old-exe"
    assert staged.read_bytes() == b"new-exe"
    result = update_installer.consume_update_result()
    assert result is not None and result["status"] == "failed"
    assert "Access denied" in str(result.get("error"))
