from __future__ import annotations

from .compress_meta import WorkerTransformCompressMetaMixin
from .convert import WorkerTransformConvertMixin
from .geometry import WorkerTransformGeometryMixin


class WorkerTransformOpsMixin(
    WorkerTransformConvertMixin,
    WorkerTransformCompressMetaMixin,
    WorkerTransformGeometryMixin,
):
    """Composed WorkerTransformOpsMixin surface split by SOLID/SRP domain modules."""

    pass


__all__ = ["WorkerTransformOpsMixin"]
