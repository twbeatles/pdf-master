"""Staging, result reporting, and safe application of Windows EXE updates."""
from __future__ import annotations

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


def launch_update_helper(*, target: Path, staged: Path) -> None:
    helper = staged.parent / f"pdf-master-update-helper-{uuid4().hex}.exe"
    shutil.copy2(Path(sys.executable).resolve(), helper)
    subprocess.Popen([str(helper), "--apply-update", "--update-target", str(target), "--update-staged", str(staged), "--update-parent-pid", str(os.getpid())], close_fds=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def apply_update(target: str, staged: str, parent_pid: int) -> int:
    target_path, staged_path = Path(target).resolve(), Path(staged).resolve()
    if parent_pid <= 0 or target_path.suffix.lower() != ".exe" or staged_path.suffix.lower() != ".exe" or not target_path.is_file() or not staged_path.is_file():
        _write_result("failed", error="Invalid update paths"); return 2
    for _ in range(120):
        try: os.kill(parent_pid, 0)
        except OSError: break
        time.sleep(0.25)
    else:
        _write_result("failed", error="Timed out waiting for the application to close"); return 3
    backup = target_path.with_suffix(target_path.suffix + ".bak")
    try:
        backup.unlink(missing_ok=True); shutil.copy2(target_path, backup); os.replace(staged_path, target_path)
        if subprocess.run([str(target_path), "--smoke"], timeout=60, check=False).returncode != 0: raise RuntimeError("Updated executable smoke check failed")
        backup.unlink(missing_ok=True); _write_result("applied"); subprocess.Popen([str(target_path)], close_fds=True); return 0
    except Exception as exc:
        rolled_back = False
        try:
            if backup.is_file(): os.replace(backup, target_path); rolled_back = True
        except OSError: pass
        _write_result("rolled_back" if rolled_back else "failed", error=str(exc))
        if rolled_back:
            try: subprocess.Popen([str(target_path)], close_fds=True)
            except OSError: pass
        return 4
