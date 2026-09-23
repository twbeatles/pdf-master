"""업데이트 확인·다운로드 thin service (PROJECT_AUDIT.md Phase 3).

`UpdateMixin`(Qt 상태/UI)과 네트워크·설치 로직의 경계를 분리해 단위 테스트
가능 영역을 넓힌다. Qt 의존성 없이 호출 가능한 순수 함수만 둔다.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .update_installer import STAGE_UPDATE_MAX_RETRIES, stage_update
from .update_manifest import (
    NoUpdateAvailableError,
    ReleaseManifest,
    download_release_manifest,
    verify_release_manifest,
)

__all__ = [
    "NoUpdateAvailableError",
    "check_for_update",
    "download_update",
]


def check_for_update(*, manifest_url: str, public_key: str, current_version: str) -> ReleaseManifest:
    """매니페스트 다운로드+검증. 새 버전이 없으면 NoUpdateAvailableError."""
    return verify_release_manifest(
        download_release_manifest(manifest_url),
        public_key=public_key,
        current_version=current_version,
    )


def download_update(
    manifest: ReleaseManifest,
    progress: Callable[[int], None] | None = None,
    *,
    max_retries: int = STAGE_UPDATE_MAX_RETRIES,
) -> Path:
    """아티팩트 스테이징. 일시 오류 재시도는 update_installer가 담당."""
    return stage_update(manifest, progress, max_retries=max_retries)
