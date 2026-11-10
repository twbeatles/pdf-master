from __future__ import annotations

import os
from pathlib import Path

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


def test_is_cross_device_error_covers_winerror_17() -> None:
    """WinError 17(드라이브 간 이동 불가)을 크로스-드라이브 오류로 판정."""
    cross = OSError("cross-drive move")
    cross.winerror = 17  # type: ignore[attr-defined]
    assert update_installer._is_cross_device_error(cross) is True
    assert update_installer._is_cross_device_error(OSError(2, "missing")) is False


def test_replace_cross_drive_falls_back_to_copy(monkeypatch, tmp_path) -> None:
    """C: 스테이징 → D: 설치처럼 os.replace가 EXDEV로 실패해도 교체 성공."""
    import errno as _errno
    import os as _os

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(update_installer.time, "sleep", lambda *_a, **_k: None)
    monkeypatch.setattr(update_installer.os, "kill", lambda pid, sig: (_ for _ in ()).throw(OSError("gone")))

    real_replace = _os.replace
    calls = {"n": 0}

    def _cross_device(src, dst):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError(_errno.EXDEV, "Invalid cross-device link")
        return real_replace(src, dst)

    monkeypatch.setattr(update_installer.os, "replace", _cross_device)

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
    assert not staged.exists()


def test_launch_helper_prefers_staged_copy(monkeypatch, tmp_path) -> None:
    """헬퍼는 실행 중 EXE 대신 스테이징된 신버전 EXE를 복사한다."""
    staged = tmp_path / "staged.exe"
    staged.write_bytes(b"new-exe")
    target = tmp_path / "app.exe"
    target.write_bytes(b"old-exe")
    captured: dict[str, list[str]] = {}

    def _popen(args: list[str], **kwargs: object) -> None:
        captured["args"] = list(args)

    monkeypatch.setattr(update_installer.subprocess, "Popen", _popen)
    update_installer.launch_update_helper(target=target, staged=staged)
    assert "args" in captured
    helper = Path(captured["args"][0])
    assert helper.parent == tmp_path
    assert helper.read_bytes() == b"new-exe"


def _mock_quiet_parent(monkeypatch) -> None:
    """부모 종료 대기·슬립을 우회하는 공통 목."""
    monkeypatch.setattr(update_installer.time, "sleep", lambda *_a, **_k: None)
    monkeypatch.setattr(update_installer.os, "kill", lambda pid, sig: (_ for _ in ()).throw(OSError("gone")))


class _Completed:
    returncode = 0


def test_backup_created_by_rename_not_copy(monkeypatch, tmp_path) -> None:
    """WinError 5 회피: 설치본은 그 자리에서 덮어쓰지 않고 백업 이름으로 옮긴다."""
    import shutil as _shutil

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    _mock_quiet_parent(monkeypatch)
    monkeypatch.setattr(update_installer.subprocess, "run", lambda *a, **k: _Completed())
    monkeypatch.setattr(update_installer.subprocess, "Popen", lambda *a, **k: None)

    copies: list[tuple[str, str]] = []
    real_copy2 = _shutil.copy2

    def _spy_copy2(src, dst, *a, **k):
        copies.append((str(src), str(dst)))
        return real_copy2(src, dst, *a, **k)

    monkeypatch.setattr(update_installer.shutil, "copy2", _spy_copy2)
    target = tmp_path / "app.exe"
    staged = tmp_path / "staged.exe"
    target.write_bytes(b"old-exe")
    staged.write_bytes(b"new-exe")
    assert update_installer.apply_update(str(target), str(staged), 123456) == 0
    assert target.read_bytes() == b"new-exe"
    assert copies == []


def test_stale_backup_is_overwritten(monkeypatch, tmp_path) -> None:
    """이전 시도가 남긴 낡은 백업이 다음 시도를 막지 않는다."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    _mock_quiet_parent(monkeypatch)
    monkeypatch.setattr(update_installer.subprocess, "run", lambda *a, **k: _Completed())
    monkeypatch.setattr(update_installer.subprocess, "Popen", lambda *a, **k: None)
    target = tmp_path / "app.exe"
    staged = tmp_path / "staged.exe"
    target.write_bytes(b"old-exe")
    staged.write_bytes(b"new-exe")
    (tmp_path / "app.exe.bak").write_bytes(b"stale-backup")
    assert update_installer.apply_update(str(target), str(staged), 123456) == 0
    assert target.read_bytes() == b"new-exe"
    assert not (tmp_path / "app.exe.bak").exists()
    result = update_installer.consume_update_result()
    assert result is not None and result["status"] == "applied"


def test_interrupted_swap_between_moves_recovers_backup(monkeypatch, tmp_path) -> None:
    """두 이동 사이에서 중단됐다면 다음 실행에서 백업으로 복구 후 교체한다."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    _mock_quiet_parent(monkeypatch)
    monkeypatch.setattr(update_installer.subprocess, "run", lambda *a, **k: _Completed())
    monkeypatch.setattr(update_installer.subprocess, "Popen", lambda *a, **k: None)
    target = tmp_path / "app.exe"
    staged = tmp_path / "staged.exe"
    backup = tmp_path / "app.exe.bak"
    backup.write_bytes(b"old-exe")
    staged.write_bytes(b"new-exe")
    assert not target.exists()
    assert update_installer.apply_update(str(target), str(staged), 123456) == 0
    assert target.read_bytes() == b"new-exe"
    assert not backup.exists()


def test_first_move_lock_keeps_installed_exe(monkeypatch, tmp_path) -> None:
    """첫 이동이 잠금으로 실패하면 설치본은 그대로 남고 staged는 보존된다."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(update_installer, "REPLACE_MAX_ATTEMPTS", 2)
    _mock_quiet_parent(monkeypatch)
    real_replace = os.replace

    def _locked(src, dst):
        if Path(dst).name.startswith("app"):
            raise PermissionError(13, "Access is denied")
        return real_replace(src, dst)

    monkeypatch.setattr(update_installer.os, "replace", _locked)
    target = tmp_path / "app.exe"
    staged = tmp_path / "staged.exe"
    target.write_bytes(b"old-exe")
    staged.write_bytes(b"new-exe")
    assert update_installer.apply_update(str(target), str(staged), 123456) == 4
    assert target.read_bytes() == b"old-exe"
    assert staged.read_bytes() == b"new-exe"
    assert not (tmp_path / "app.exe.bak").exists()
    result = update_installer.consume_update_result()
    assert result is not None and result["status"] == "failed"
    assert "preserved" in str(result.get("error"))


def test_clean_bootloader_env_strips_all_handoff_prefixes() -> None:
    dirty = {
        "_MEIPASS": "x", "_MEIPASS2": "x", "_MEI12345": "x",
        "_PYI_ARCHIVE_FILE": "x", "_PYI_PARENT_PROCESS_LEVEL": "x",
        "_PYINSTALLER_FOO": "x", "PYINSTALLER_BAR": "x",
        "PATH": "keep", "KEEP": "yes",
    }
    assert update_installer.clean_bootloader_env(dict(dirty)) == {"PATH": "keep", "KEEP": "yes"}


def test_helper_and_relaunch_strip_bootloader_env(monkeypatch, tmp_path) -> None:
    """헬퍼·재기동 자식은 부트로더 핸드오프 변수 없는 환경으로 실행."""
    monkeypatch.setenv("_MEIPASS2", "C:\\fake\\_MEI12345")
    monkeypatch.setenv("_PYI_ARCHIVE_FILE", "C:\\fake\\app.exe")
    monkeypatch.setenv("_PYI_PARENT_PROCESS_LEVEL", "1")
    monkeypatch.setenv("PYINSTALLER_FOO", "1")
    monkeypatch.setenv("KEEP_ME", "yes")

    captured: dict[str, object] = {}
    monkeypatch.setattr(update_installer.subprocess, "Popen", lambda *a, **k: captured.setdefault("env", k.get("env")))
    staged = tmp_path / "staged.exe"
    staged.write_bytes(b"new-exe")
    update_installer.launch_update_helper(target=tmp_path / "app.exe", staged=staged)
    helper_env = captured.get("env")
    assert isinstance(helper_env, dict)
    for key in ("_MEIPASS2", "_PYI_ARCHIVE_FILE", "_PYI_PARENT_PROCESS_LEVEL", "PYINSTALLER_FOO"):
        assert key not in helper_env
    assert helper_env.get("KEEP_ME") == "yes"

    captured.clear()
    update_installer._relaunch(tmp_path / "app.exe")
    relaunch_env = captured.get("env")
    assert isinstance(relaunch_env, dict)
    for key in ("_MEIPASS2", "_PYI_ARCHIVE_FILE", "_PYI_PARENT_PROCESS_LEVEL", "PYINSTALLER_FOO"):
        assert key not in relaunch_env
    assert relaunch_env.get("KEEP_ME") == "yes"


def test_smoke_child_strips_bootloader_env(monkeypatch, tmp_path) -> None:
    """--smoke 자식은 부트로더 핸드오프 변수 없는 환경으로 실행."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("_MEIPASS2", "C:\\fake\\_MEI12345")
    monkeypatch.setenv("_PYI_ARCHIVE_FILE", "C:\\fake\\app.exe")
    _mock_quiet_parent(monkeypatch)
    seen: dict[str, object] = {}

    def _run(*a, **k):
        seen["env"] = k.get("env")
        return _Completed()

    monkeypatch.setattr(update_installer.subprocess, "run", _run)
    monkeypatch.setattr(update_installer.subprocess, "Popen", lambda *a, **k: None)
    target = tmp_path / "app.exe"
    staged = tmp_path / "staged.exe"
    target.write_bytes(b"old-exe")
    staged.write_bytes(b"new-exe")
    assert update_installer.apply_update(str(target), str(staged), 123456) == 0
    smoke_env = seen.get("env")
    assert isinstance(smoke_env, dict)
    assert "_MEIPASS2" not in smoke_env and "_PYI_ARCHIVE_FILE" not in smoke_env
