from __future__ import annotations

from .convert import WorkerTransformConvertMixin
from .compress_meta import WorkerTransformCompressMetaMixin
from .geometry import WorkerTransformGeometryMixin


class WorkerTransformOpsMixin(
    WorkerTransformConvertMixin,
    WorkerTransformCompressMetaMixin,
    WorkerTransformGeometryMixin,
):
    """Composed WorkerTransformOpsMixin surface split by SOLID/SRP domain modules."""

    pass


__all__ = ["WorkerTransformOpsMixin"]
