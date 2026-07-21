from __future__ import annotations

from .split_delete import WorkerPageSplitDeleteMixin
from .reorder_rotate import WorkerPageReorderRotateMixin
from .mutate import WorkerPageMutateMixin


class WorkerPageOpsMixin(
    WorkerPageSplitDeleteMixin,
    WorkerPageReorderRotateMixin,
    WorkerPageMutateMixin,
):
    """Composed WorkerPageOpsMixin surface split by SOLID/SRP domain modules."""

    pass


__all__ = ["WorkerPageOpsMixin"]
