"""WorkerRuntimeMixin — runtime 단계 믹스인 합성 facade.

public import 경로 유지:
`src.core.worker_runtime.WorkerRuntimeMixin`
`src.core.worker_runtime.mixin.WorkerRuntimeMixin`
실제 구현은 `mixin_payload` / `mixin_progress` / `mixin_files` /
`mixin_access` / `mixin_run` 에 있다.
"""
from __future__ import annotations

from .mixin_access import WorkerRuntimeAccessMixin
from .mixin_files import WorkerRuntimeFilesMixin
from .mixin_payload import WorkerRuntimePayloadMixin
from .mixin_progress import WorkerRuntimeProgressMixin
from .mixin_run import WorkerRuntimeRunMixin


class WorkerRuntimeMixin(
    WorkerRuntimePayloadMixin,
    WorkerRuntimeProgressMixin,
    WorkerRuntimeFilesMixin,
    WorkerRuntimeAccessMixin,
    WorkerRuntimeRunMixin,
):
    """호환 surface: payload + 진행/취소 + 파일 저장 + 접근/검증 + run."""

    pass


__all__ = ["WorkerRuntimeMixin"]
