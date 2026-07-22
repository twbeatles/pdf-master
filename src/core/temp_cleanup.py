"""PDF Master 임시 파일 orphan 정리 유틸리티."""

from __future__ import annotations

import glob
import logging
import os
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


__all__ = [
    "AI_TEMP_PREFIX",
    "ATOMIC_TEMP_PREFIX",
    "DEFAULT_MAX_AGE_SECONDS",
    "cleanup_pdf_master_temp_files",
]
