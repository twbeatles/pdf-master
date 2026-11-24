"""PDF Master 임시 파일 orphan 정리 유틸리티."""

from __future__ import annotations

import glob
import logging
import os
import subprocess
import sys
import tempfile
import time

logger = logging.getLogger(__name__)

# AI 암호 PDF 임시 복호 파일 / atomic save 임시 파일 접두사
AI_TEMP_PREFIX = "pdf_master_ai_"
ATOMIC_TEMP_PREFIX = ".pdf_master_"
# 기본: 60초 이상 된 orphan만 삭제 (진행 중 작업 보호)
DEFAULT_MAX_AGE_SECONDS = 60.0


def cleanup_pdf_master_temp_files(
    *,
    temp_dir: str | None = None,
    max_age_seconds: float | None = DEFAULT_MAX_AGE_SECONDS,
    include_in_progress: bool = False,
) -> int:
    """시스템 temp 디렉터리의 PDF Master orphan 임시 파일을 삭제한다.

    Args:
        temp_dir: 대상 디렉터리 (기본: tempfile.gettempdir())
        max_age_seconds: 이 나이(초) 이상인 파일만 삭제. None이면 나이 무시.
        include_in_progress: True면 max_age를 무시하고 매칭 파일 전부 삭제
            (앱 강제 종료 직후 등).

    Returns:
        삭제한 파일 수.
    """
    root = temp_dir or tempfile.gettempdir()
    if not root or not os.path.isdir(root):
        return 0

    patterns = [
        os.path.join(root, f"{AI_TEMP_PREFIX}*"),
        os.path.join(root, f"{ATOMIC_TEMP_PREFIX}*"),
    ]
    removed = 0
    now = time.time()
    for pattern in patterns:
        for path in glob.glob(pattern):
            if not os.path.isfile(path):
                continue
            try:
                if not include_in_progress and max_age_seconds is not None:
                    age = now - os.path.getmtime(path)
                    if age < max_age_seconds:
                        continue
                os.remove(path)
                removed += 1
                logger.info("Removed orphan temp file: %s", path)
            except OSError:
                logger.debug("Failed to remove temp file: %s", path, exc_info=True)
    return removed


def restrict_temp_file_permissions(path: str) -> bool:
    """임시 평문 PDF를 현재 사용자 전용으로 제한 (best-effort).

    AI 임시 복호본과 Undo 백업 사본이 공유하는 단일 구현.
    Returns:
        True if permission restriction appeared to succeed, False otherwise.
    """
    if not path or not os.path.exists(path):
        return False
    ok = True
    try:
        if os.path.isdir(path):
            os.chmod(path, 0o700)
        else:
            os.chmod(path, 0o600)
    except OSError:
        logger.warning("chmod failed for temp path: %s", path, exc_info=True)
        ok = False
    if sys.platform != "win32":
        return ok
    # Windows: 상속 제거 후 현재 사용자 전용
    try:
        user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
        if not user:
            logger.warning("Windows ACL restrict skipped (no USERNAME) for %s", path)
            return False
        args = ["icacls", path, "/inheritance:r", "/grant:r", f"{user}:(OI)(CI)F"]
        if os.path.isfile(path):
            args = ["icacls", path, "/inheritance:r", "/grant:r", f"{user}:(F)"]
        result = subprocess.run(
            args,
            check=False,
            capture_output=True,
            timeout=8,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            logger.warning(
                "Windows ACL restrict failed for %s (code=%s)",
                path,
                result.returncode,
            )
            ok = False
    except Exception:
        logger.warning("Windows ACL restrict failed for %s", path, exc_info=True)
        ok = False
    return ok


def sweep_output_dir_orphans(
    output_dir: str | None,
    *,
    max_age_seconds: float | None = DEFAULT_MAX_AGE_SECONDS,
) -> int:
    """출력 디렉터리의 원자 저장 orphan 정리 (ISSUE-003).

    원자 저장이 출력 디렉터리에 만드는 ``.pdf_master_*`` 임시 파일은
    시스템 temp 스윕 대상이 아니므로, 비정상 종료 시 잔존한다.
    시작 시 ``last_output_dir``에 한해 같은 접두사·나이 기준으로 정리한다.
    존재하지 않는 경로·파일 경로·빈 값은 0을 반환한다.
    """
    if not output_dir or not isinstance(output_dir, str):
        return 0
    try:
        if not os.path.isdir(output_dir):
            return 0
    except Exception:
        return 0
    return cleanup_pdf_master_temp_files(
        temp_dir=output_dir, max_age_seconds=max_age_seconds
    )


__all__ = [
    "AI_TEMP_PREFIX",
    "ATOMIC_TEMP_PREFIX",
    "DEFAULT_MAX_AGE_SECONDS",
    "cleanup_pdf_master_temp_files",
    "restrict_temp_file_permissions",
    "sweep_output_dir_orphans",
]
