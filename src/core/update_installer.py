"""Staging, result reporting, and safe application of Windows EXE updates."""
from __future__ import annotations

import errno
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4

from .update_manifest import ReleaseManifest


def update_root() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "PDFMaster" / "updates"


def update_result_path() -> Path:
    return update_root() / "last-update-result.json"


def _write_result(status: str, **extra: object) -> None:
    root = update_root(); root.mkdir(parents=True, exist_ok=True)
    target = update_result_path(); tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps({"status": status, **extra}, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, target)


def consume_update_result() -> dict[str, object] | None:
    path = update_result_path()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    finally:
        try: path.unlink(missing_ok=True)
        except OSError: pass


def _cleanup_old_helpers(root: Path) -> None:
    for path in root.glob("pdf-master-update-helper-*.exe"):
        try:
            if time.time() - path.stat().st_mtime > 24 * 3600: path.unlink()
        except OSError: pass


#: 일시적 네트워크 오류 시 다운로드 재시도 횟수 (PROJECT_AUDIT.md ISSUE-003 대응).
STAGE_UPDATE_MAX_RETRIES = 3

#: 재시도 사이 백오프 기준 (초, 지수 백오프 배율로 사용).
STAGE_UPDATE_RETRY_BACKOFF = 1.0

_TRANSIENT_MARKERS = ("integrity check failed", "size mismatch")


def _is_transient_stage_error(exc: BaseException) -> bool:
    """재시도할 가치가 있는 일시 오류인지 판정. 서명/HTTPS 정책 오류는 제외."""
    message = str(exc)
    if "HTTPS" in message or "signature" in message.lower():
        return False
    if isinstance(exc, ValueError):
        return any(marker in message for marker in _TRANSIENT_MARKERS)
    return isinstance(exc, (OSError, TimeoutError, ConnectionError))


def _stage_update_once(manifest: ReleaseManifest, progress: Callable[[int], None] | None, staged: Path) -> Path:
    digest, total = hashlib.sha256(), 0
    with urlopen(Request(manifest.artifact_url, headers={"User-Agent": "PDF-Master-Updater"}), timeout=30) as response, open(staged, "xb") as out:
        final = urlsplit(response.geturl())
        if final.scheme.lower() != "https" or not final.hostname:
            raise ValueError("Artifact redirect must remain HTTPS")
        while chunk := response.read(1024 * 1024):
            total += len(chunk)
            if total > manifest.artifact_size: raise ValueError("Update artifact size mismatch")
            digest.update(chunk); out.write(chunk)
            if progress: progress(min(99, int(total * 100 / manifest.artifact_size)))
    if total != manifest.artifact_size or digest.hexdigest().lower() != manifest.artifact_sha256:
        raise ValueError("Update artifact integrity check failed")
    if progress: progress(100)
    return staged


def stage_update(
    manifest: ReleaseManifest,
    progress: Callable[[int], None] | None = None,
    *,
    max_retries: int = STAGE_UPDATE_MAX_RETRIES,
    retry_backoff: float = STAGE_UPDATE_RETRY_BACKOFF,
) -> Path:
    """서명 아티팩트를 스테이징. 일시 네트워크 오류에 한해 재시도한다."""
    root = update_root(); root.mkdir(parents=True, exist_ok=True); _cleanup_old_helpers(root)
    staged = root / f"PDF_Master_v{manifest.version}-{uuid4().hex}.exe"
    attempts = max(1, int(max_retries))
    last_error: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return _stage_update_once(manifest, progress, staged)
        except Exception as exc:
            last_error = exc
            staged.unlink(missing_ok=True)
            if attempt >= attempts or not _is_transient_stage_error(exc):
                raise
            # 부분 진행률 잔상 방지: 다음 시도 전 0%로 되돌림
            if progress:
                try: progress(0)
                except Exception: pass
            time.sleep(retry_backoff * (2 ** (attempt - 1)))
    assert last_error is not None
    raise last_error


#: 헬퍼 실행(Popen) 재시도 횟수 — 백신/인덱서가 복사 직후 헬퍼를 잠깐 잡는 경우 대응.
LAUNCH_HELPER_MAX_ATTEMPTS = 3

#: 헬퍼 실행 재시도 간격 (초).
LAUNCH_HELPER_RETRY_INTERVAL = 0.5


def launch_update_helper(*, target: Path, staged: Path) -> None:
    helper = staged.parent / f"pdf-master-update-helper-{uuid4().hex}.exe"
    shutil.copy2(Path(sys.executable).resolve(), helper)
    args = [str(helper), "--apply-update", "--update-target", str(target), "--update-staged", str(staged), "--update-parent-pid", str(os.getpid())]
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    last_error: OSError | None = None
    for _ in range(max(1, LAUNCH_HELPER_MAX_ATTEMPTS)):
        try:
            subprocess.Popen(args, close_fds=True, creationflags=flags)
            return
        except OSError as exc:
            last_error = exc
            time.sleep(LAUNCH_HELPER_RETRY_INTERVAL)
    assert last_error is not None
    raise last_error


#: 부모 종료 대기 폴링 횟수·간격 (120 × 0.25s ≈ 30s).
PARENT_WAIT_MAX_ATTEMPTS = 120

#: 부모 종료 대기 폴링 간격 (초).
PARENT_WAIT_INTERVAL = 0.25

#: 실행 파일 교체 시 파일 잠금(공유 위반·액세스 거부) 재시도 횟수·간격 (≈15s).
REPLACE_MAX_ATTEMPTS = 60

#: 교체 재시도 간격 (초).
REPLACE_RETRY_INTERVAL = 0.25


def _parent_process_exited(pid: int) -> bool:
    """부모 프로세스 종료 여부. 살아있는데 권한만 없으면 False를 반환한다.

    Windows에서 실행 중 EXE를 교체하면 공유 위반(WinError 5)으로 실패하므로,
    ``PermissionError``를 종료로 오인(EACCES → break)하던 기존 동작을 고친다.
    """
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    except OSError as exc:
        if exc.errno == errno.ESRCH:
            return True
        if exc.errno in (errno.EACCES, errno.EPERM):
            return False
        # errno 없는 OSError(테스트 더블 등)는 기존 동작대로 종료로 간주
        return True
    else:
        return False


def _wait_for_parent_exit(parent_pid: int) -> bool:
    for _ in range(max(1, PARENT_WAIT_MAX_ATTEMPTS)):
        if _parent_process_exited(parent_pid):
            return True
        time.sleep(PARENT_WAIT_INTERVAL)
    return False


def _replace_with_retry(source: Path, dest: Path) -> None:
    """잠금 해제를 기다리며 교체. 공유 위반은 PermissionError로 올라온다."""
    last_error: PermissionError | None = None
    for _ in range(max(1, REPLACE_MAX_ATTEMPTS)):
        try:
            os.replace(source, dest)
            return
        except PermissionError as exc:
            last_error = exc
            time.sleep(REPLACE_RETRY_INTERVAL)
    assert last_error is not None
    raise last_error


def _target_dir_writable(target_path: Path) -> bool:
    try:
        probe = target_path.parent / f".pdf_master_write_test_{uuid4().hex}.tmp"
        fd = os.open(probe, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try: os.close(fd)
        finally: probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _relaunch_elevated(*, target: Path, staged: Path, parent_pid: int) -> bool:
    """UAC 권한 상승으로 자기 자신을 다시 실행. 위임 성공 시 True.

    Program Files 등 보호 위치에 설치된 경우 비상승 헬퍼의 교체는
    WinError 5로 실패할 수밖에 없으므로, 상승된 인스턴스에 작업을 넘긴다.
    """
    if sys.platform != "win32" or "--update-elevated" in sys.argv:
        return False
    try:
        import ctypes

        params = (
            f'--apply-update --update-target "{target}" '
            f'--update-staged "{staged}" '
            f"--update-parent-pid {parent_pid} --update-elevated"
        )
        rc = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", str(Path(sys.executable).resolve()), params, None, 1,
        )
        return int(rc) > 32
    except OSError:
        return False


def _relaunch(path: Path) -> None:
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen([str(path)], close_fds=True, creationflags=flags)


def apply_update(target: str, staged: str, parent_pid: int) -> int:
    target_path, staged_path = Path(target).resolve(), Path(staged).resolve()
    if parent_pid <= 0 or target_path.suffix.lower() != ".exe" or staged_path.suffix.lower() != ".exe" or not target_path.is_file() or not staged_path.is_file():
        _write_result("failed", error="Invalid update paths"); return 2
    if not _wait_for_parent_exit(parent_pid):
        _write_result("failed", error="Timed out waiting for the application to close"); return 3
    if not _target_dir_writable(target_path):
        # 보호 위치(Program Files 등): 상승된 헬퍼에 위임하고 조용히 종료.
        # 결과 파일은 쓰지 않는다 — 상승 인스턴스가 최종 결과를 기록한다.
        if _relaunch_elevated(target=target_path, staged=staged_path, parent_pid=parent_pid):
            return 5
        _write_result("failed", error=f"Access denied replacing {target_path} (administrator permission required). Staged update preserved at {staged_path}")
        return 4
    backup = target_path.with_suffix(target_path.suffix + ".bak")
    try:
        backup.unlink(missing_ok=True); shutil.copy2(target_path, backup); _replace_with_retry(staged_path, target_path)
        if subprocess.run([str(target_path), "--smoke"], timeout=60, check=False).returncode != 0: raise RuntimeError("Updated executable smoke check failed")
        backup.unlink(missing_ok=True); _write_result("applied"); _relaunch(target_path); return 0
    except PermissionError as exc:
        rolled_back = False
        try:
            if backup.is_file(): _replace_with_retry(backup, target_path); rolled_back = True
        except OSError: pass
        if rolled_back:
            error = f"Access denied replacing {target_path} ({exc}); restored the previous version"
        else:
            error = f"Access denied replacing {target_path} ({exc}); staged update preserved at {staged_path}"
        _write_result("rolled_back" if rolled_back else "failed", error=error)
        if rolled_back:
            try: _relaunch(target_path)
            except OSError: pass
        return 4
    except Exception as exc:
        rolled_back = False
        try:
            if backup.is_file(): os.replace(backup, target_path); rolled_back = True
        except OSError: pass
        _write_result("rolled_back" if rolled_back else "failed", error=str(exc))
        if rolled_back:
            try: _relaunch(target_path)
            except OSError: pass
        return 4
