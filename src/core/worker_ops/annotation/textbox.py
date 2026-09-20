"""WorkerAnnotationTextboxMixin — textbox_impl 합성 facade.

public import 경로 유지:
`src.core.worker_ops.annotation.textbox.WorkerAnnotationTextboxMixin`
실제 구현은 `textbox_impl/` (single/batch/replace/extract + args/base).
"""
from __future__ import annotations

from .textbox_impl import (
    WorkerTextboxBatchMixin,
    WorkerTextboxExtractMixin,
    WorkerTextboxReplaceMixin,
    WorkerTextboxSingleMixin,
)


class WorkerAnnotationTextboxMixin(
    WorkerTextboxSingleMixin,
    WorkerTextboxBatchMixin,
    WorkerTextboxReplaceMixin,
    WorkerTextboxExtractMixin,
):
    """호환 surface: insert_textbox/insert_textboxes/replace/extract."""

    pass


__all__ = ["WorkerAnnotationTextboxMixin"]
