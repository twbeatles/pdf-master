from .._typing import WorkerHost
from ._pdf_impl import WorkerPdfOpsMixin as _LegacyWorkerPdfOpsMixin


class WorkerComposeOpsMixin(WorkerHost):
    merge = _LegacyWorkerPdfOpsMixin.merge
    split = _LegacyWorkerPdfOpsMixin.split
    split_by_pages = _LegacyWorkerPdfOpsMixin.split_by_pages
    images_to_pdf = _LegacyWorkerPdfOpsMixin.images_to_pdf
    reorder = _LegacyWorkerPdfOpsMixin.reorder
    duplicate_page = _LegacyWorkerPdfOpsMixin.duplicate_page
    reverse_pages = _LegacyWorkerPdfOpsMixin.reverse_pages
    replace_page = _LegacyWorkerPdfOpsMixin.replace_page
    copy_page_between_docs = _LegacyWorkerPdfOpsMixin.copy_page_between_docs
    insert_blank_page = _LegacyWorkerPdfOpsMixin.insert_blank_page
