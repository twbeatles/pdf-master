from __future__ import annotations

from .mutate import WorkerPageMutateMixin
from .reorder_rotate import WorkerPageReorderRotateMixin
from .split_delete import WorkerPageSplitDeleteMixin


class WorkerPageOpsMixin(
    WorkerPageSplitDeleteMixin,
    WorkerPageReorderRotateMixin,
    WorkerPageMutateMixin,
):
    """Composed WorkerPageOpsMixin surface split by SOLID/SRP domain modules."""

    pass


__all__ = ["WorkerPageOpsMixin"]
