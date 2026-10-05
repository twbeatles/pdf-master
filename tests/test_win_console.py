"""창 없는 EXE에서 자식 프로세스 콘솔 창이 뜨지 않게 하는 가드 회귀."""

import subprocess
import sys

import pytest

from src.core import win_console

CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_CONSOLE = 0x00000010


@pytest.fixture
def created_flags(monkeypatch):
    if sys.platform != "win32":
        pytest.skip("Windows only")
    import _winapi

    flags = []
    original = _winapi.CreateProcess

    def recording_create_process(*args, **kwargs):
        flags.append(args[5])
        return original(*args, **kwargs)

    monkeypatch.setattr(_winapi, "CreateProcess", recording_create_process)
    win_console.restore_child_console_windows()
    assert win_console.suppress_child_console_windows() is True
    try:
        yield flags
    finally:
        win_console.restore_child_console_windows()


def test_children_get_no_window_flag_by_default(created_flags):
    # 표준 라이브러리 platform 모듈의 폴백과 같은 형태의 호출
    output = subprocess.check_output("ver", shell=True, text=True)
    assert "Windows" in output  # 출력 캡처는 그대로 동작
    subprocess.run([sys.executable, "-c", "pass"], check=True, creationflags=subprocess.DETACHED_PROCESS)
    assert len(created_flags) == 2
    assert all(flag & CREATE_NO_WINDOW for flag in created_flags)
    assert created_flags[1] & subprocess.DETACHED_PROCESS  # 호출자가 준 플래그는 유지


def test_explicit_new_console_request_is_respected(created_flags):
    proc = subprocess.Popen([sys.executable, "-c", "pass"], creationflags=CREATE_NEW_CONSOLE)
    proc.wait(timeout=30)
    assert created_flags == [CREATE_NEW_CONSOLE]


def test_guard_is_idempotent_and_restorable():
    if sys.platform != "win32":
        assert win_console.suppress_child_console_windows() is False
        return
    win_console.restore_child_console_windows()
    pristine = subprocess.Popen.__init__
    assert win_console.suppress_child_console_windows() is True
    patched = subprocess.Popen.__init__
    assert win_console.suppress_child_console_windows() is True
    assert subprocess.Popen.__init__ is patched  # 두 번 감싸지 않는다
    win_console.restore_child_console_windows()
    assert subprocess.Popen.__init__ is pristine


def test_main_applies_guard_before_qt_imports():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
    assert source.index("suppress_child_console_windows()") < source.index("from PyQt6.QtCore import")
