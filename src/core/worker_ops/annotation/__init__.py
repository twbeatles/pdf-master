from __future__ import annotations

from .annotations_crud import WorkerAnnotationCrudMixin
from .markup import WorkerAnnotationMarkupMixin
from .redaction import WorkerAnnotationRedactionMixin
from .shapes_links import WorkerAnnotationShapesLinksMixin
from .signatures import WorkerAnnotationSignaturesMixin
from .watermark import WorkerAnnotationWatermarkMixin


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
