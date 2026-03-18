from .._typing import WorkerHost
from ._pdf_impl import WorkerPdfOpsMixin as _LegacyWorkerPdfOpsMixin


class WorkerTransformOpsMixin(WorkerHost):
    convert_to_img = _LegacyWorkerPdfOpsMixin.convert_to_img
    delete_pages = _LegacyWorkerPdfOpsMixin.delete_pages
    rotate = _LegacyWorkerPdfOpsMixin.rotate
    resize_pages = _LegacyWorkerPdfOpsMixin.resize_pages
    crop_pdf = _LegacyWorkerPdfOpsMixin.crop_pdf
    compress = _LegacyWorkerPdfOpsMixin.compress
    metadata_update = _LegacyWorkerPdfOpsMixin.metadata_update
    add_background = _LegacyWorkerPdfOpsMixin.add_background
