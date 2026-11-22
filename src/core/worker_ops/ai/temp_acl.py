"""AI 임시 평문 PDF ACL 제한 (facade).

실구현은 `src/core/temp_cleanup.py::restrict_temp_file_permissions`에 있으며
Undo 백업 사본과 공유한다. public import 경로를 유지한다.
"""

from __future__ import annotations

from ...temp_cleanup import restrict_temp_file_permissions as _restrict


def _restrict_temp_file_permissions(path: str) -> bool:
    """임시 평문 PDF를 현재 사용자 전용으로 제한 (best-effort)."""
    return bool(_restrict(path))


__all__ = ["_restrict_temp_file_permissions"]
