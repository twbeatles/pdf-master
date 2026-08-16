"""Stage and atomically apply a verified Windows executable update."""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4
from urllib.request import Request, urlopen

from .update_manifest import ReleaseManifest


def stage_update(manifest: ReleaseManifest) -> Path:
    root = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "PDFMaster" / "updates"
    root.mkdir(parents=True, exist_ok=True)
    staged = root / f"PDF_Master_v{manifest.version}-{uuid4().hex}.exe"
    digest, total = hashlib.sha256(), 0
    try:
        with urlopen(Request(manifest.artifact_url, headers={"User-Agent": "PDF-Master-Updater"}), timeout=30) as response, open(staged, "xb") as out:
            if response.url.lower().split(":", 1)[0] != "https":
                raise ValueError("Artifact redirect must remain HTTPS")
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > manifest.artifact_size:
                    raise ValueError("Update artifact size mismatch")
                digest.update(chunk)
                out.write(chunk)
        if total != manifest.artifact_size or digest.hexdigest().lower() != manifest.artifact_sha256:
            raise ValueError("Update artifact integrity check failed")
        return staged
    except Exception:
        staged.unlink(missing_ok=True)
        raise


def launch_update_helper(*, target: Path, staged: Path) -> None:
    helper = staged.parent / f"pdf-master-update-helper-{uuid4().hex}.exe"
    shutil.copy2(Path(sys.executable).resolve(), helper)
    subprocess.Popen([str(helper), "--apply-update", "--update-target", str(target), "--update-staged", str(staged), "--update-parent-pid", str(os.getpid())], close_fds=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def apply_update(target: str, staged: str, parent_pid: int) -> int:
    target_path, staged_path = Path(target).resolve(), Path(staged).resolve()
    if parent_pid <= 0 or target_path.suffix.lower() != ".exe" or staged_path.suffix.lower() != ".exe" or not staged_path.is_file():
        return 2
    # The parent has to release its executable before Windows permits replacement.
    for _ in range(120):
        try:
            os.kill(parent_pid, 0)
        except OSError:
            break
        time.sleep(0.25)
    else:
        return 3
    backup = target_path.with_suffix(target_path.suffix + ".bak")
    try:
        backup.unlink(missing_ok=True)
        shutil.copy2(target_path, backup)
        os.replace(staged_path, target_path)
        if subprocess.run([str(target_path), "--smoke"], timeout=60, check=False).returncode != 0:
            raise RuntimeError("Updated executable smoke check failed")
        backup.unlink(missing_ok=True)
        subprocess.Popen([str(target_path)], close_fds=True)
        return 0
    except Exception:
        if backup.is_file():
            os.replace(backup, target_path)
        return 4
