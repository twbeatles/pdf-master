from __future__ import annotations

from .watermark import WorkerAnnotationWatermarkMixin
from .annotations_crud import WorkerAnnotationCrudMixin
from .markup import WorkerAnnotationMarkupMixin
from .shapes_links import WorkerAnnotationShapesLinksMixin
from .redaction import WorkerAnnotationRedactionMixin
from .signatures import WorkerAnnotationSignaturesMixin


class WorkerAnnotationOpsMixin(
    WorkerAnnotationWatermarkMixin,
    WorkerAnnotationCrudMixin,
    WorkerAnnotationMarkupMixin,
    WorkerAnnotationShapesLinksMixin,
    WorkerAnnotationRedactionMixin,
    WorkerAnnotationSignaturesMixin,
):
    """Composed WorkerAnnotationOpsMixin surface split by SOLID/SRP domain modules."""

    pass


__all__ = ["WorkerAnnotationOpsMixin"]
