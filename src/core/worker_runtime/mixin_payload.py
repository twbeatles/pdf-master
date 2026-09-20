"""결과 payload/부분 결과 믹스인."""
from __future__ import annotations

from typing import Any

from .._typing import WorkerHost
from .dispatch import get_operation_spec


class WorkerRuntimePayloadMixin(WorkerHost):
    def _set_result_payload(self, payload: dict[str, Any] | None = None, **extra: Any) -> None:
        merged: dict[str, Any] = {}
        if isinstance(payload, dict):
            merged.update(payload)
        if extra:
            merged.update(extra)
        self.result_payload = merged

    def _update_result_payload(self, **payload: Any) -> None:
        if not isinstance(getattr(self, "result_payload", None), dict):
            self.result_payload = {}
        self.result_payload.update(payload)

    def _emit_partial_result(self, **payload: Any) -> None:
        if not payload:
            return
        payload.setdefault("mode", self.mode)
        spec = get_operation_spec(self.mode)
        if spec is not None:
            payload.setdefault("result_kind", spec.result_kind)
        self.partial_result_signal.emit(payload)


__all__ = ["WorkerRuntimePayloadMixin"]
