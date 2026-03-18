from .annotation_ops import WorkerAnnotationOpsMixin
from .batch_ops import WorkerBatchOpsMixin
from .compose_ops import WorkerComposeOpsMixin
from .extract_ops import WorkerExtractOpsMixin
from .security_ops import WorkerSecurityOpsMixin
from .transform_ops import WorkerTransformOpsMixin


class WorkerPdfOpsMixin(
    WorkerBatchOpsMixin,
    WorkerSecurityOpsMixin,
    WorkerExtractOpsMixin,
    WorkerAnnotationOpsMixin,
    WorkerTransformOpsMixin,
    WorkerComposeOpsMixin,
):
    pass


__all__ = ["WorkerPdfOpsMixin"]
