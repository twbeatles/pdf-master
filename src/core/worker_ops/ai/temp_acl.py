"""AI 임시 평문 PDF ACL 제한."""
from __future__ import annotations

import logging
import os
import subprocess
import sys

logger = logging.getLogger(__name__)


def _restrict_temp_file_permissions(path: str) -> bool:
    """임시 평문 PDF를 현재 사용자 전용으로 제한 (best-effort).

    Returns:
        True if permission restriction appeared to succeed, False otherwise.
    """
    if not path or not os.path.isfile(path):
        return False
    ok = True
    try:
        os.chmod(path, 0o600)
    except OSError:
        logger.warning("chmod 0o600 failed for AI temp PDF: %s", path, exc_info=True)
        ok = False
    if sys.platform != "win32":
        return ok
    # Windows: 상속 제거 후 현재 사용자 Full control
    try:
        user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
        if not user:
            logger.warning("Windows ACL restrict skipped (no USERNAME) for %s", path)
            return False
        result = subprocess.run(
            ["icacls", path, "/inheritance:r", f"/grant:r", f"{user}:(F)"],
            check=False,
            capture_output=True,
            timeout=8,
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


__all__ = ["_restrict_temp_file_permissions"]
