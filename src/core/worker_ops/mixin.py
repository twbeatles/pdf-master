from __future__ import annotations

from .annotation_ops import WorkerAnnotationOpsMixin
from .batch_ops import WorkerBatchOpsMixin
from .compare_ops import WorkerCompareOpsMixin
from .compose_ops import WorkerComposeOpsMixin
from .extract_ops import WorkerExtractOpsMixin
from .form_ops import WorkerFormOpsMixin
from .page_ops import WorkerPageOpsMixin
from .security_ops import WorkerSecurityOpsMixin
from .transform_ops import WorkerTransformOpsMixin


class WorkerPdfOpsMixin(
    WorkerBatchOpsMixin,
    WorkerSecurityOpsMixin,
    WorkerExtractOpsMixin,
    WorkerFormOpsMixin,
    WorkerCompareOpsMixin,
    WorkerAnnotationOpsMixin,
    WorkerTransformOpsMixin,
    WorkerPageOpsMixin,
    WorkerComposeOpsMixin,
):
    """Composed worker operation surface grouped by domain modules."""

    pass


__all__ = ["WorkerPdfOpsMixin"]
