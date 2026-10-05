"""창 없는(windowed) Windows 앱에서 자식 프로세스의 콘솔 창이 뜨지 않게 한다.

콘솔이 없는 EXE가 콘솔 프로그램(cmd, icacls 등)을 띄우면 Windows가 새 콘솔 창을
만들어 잠깐 번쩍인다. 우리 코드뿐 아니라 표준 라이브러리도 그런 호출을 한다
(예: `platform` 모듈이 Windows 버전을 구할 때 폴백으로 `cmd /c ver` 실행).
호출 지점을 일일이 고칠 수 없으므로 `subprocess.Popen`의 기본 creationflags에
CREATE_NO_WINDOW를 더한다. 출력 캡처·종료 코드에는 영향이 없다.
"""

from __future__ import annotations

import functools
import subprocess
import sys

_CREATE_NO_WINDOW = 0x08000000
_CREATE_NEW_CONSOLE = 0x00000010

_original_popen_init = None


def suppress_child_console_windows() -> bool:
    """Popen 기본값에 CREATE_NO_WINDOW를 적용. 적용됐으면 True (Windows 전용)."""
    global _original_popen_init
    if sys.platform != "win32":
        return False
    if _original_popen_init is not None:
        return True

    original = subprocess.Popen.__init__

    @functools.wraps(original)
    def _init_without_console(self, *args, **kwargs):
        flags = kwargs.get("creationflags", 0) or 0
        # 호출자가 일부러 새 콘솔을 요청한 경우는 그대로 둔다.
        if not flags & _CREATE_NEW_CONSOLE:
            kwargs["creationflags"] = flags | _CREATE_NO_WINDOW
        original(self, *args, **kwargs)

    _original_popen_init = original
    subprocess.Popen.__init__ = _init_without_console  # type: ignore[method-assign]
    return True


def restore_child_console_windows() -> None:
    """suppress_child_console_windows 적용을 되돌린다 (테스트용)."""
    global _original_popen_init
    if _original_popen_init is not None:
        subprocess.Popen.__init__ = _original_popen_init  # type: ignore[method-assign]
        _original_popen_init = None
