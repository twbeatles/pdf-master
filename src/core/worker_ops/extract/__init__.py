from __future__ import annotations

from .text_info import WorkerExtractTextInfoMixin
from .bookmarks import WorkerExtractBookmarksMixin
from .search_tables import WorkerExtractSearchTablesMixin
from .annotations_links import WorkerExtractAnnotationsLinksMixin
from .attachments import WorkerExtractAttachmentsMixin
from .images_markdown import WorkerExtractImagesMarkdownMixin


class WorkerExtractOpsMixin(
    WorkerExtractTextInfoMixin,
    WorkerExtractBookmarksMixin,
    WorkerExtractSearchTablesMixin,
    WorkerExtractAnnotationsLinksMixin,
    WorkerExtractAttachmentsMixin,
    WorkerExtractImagesMarkdownMixin,
):
    """Composed WorkerExtractOpsMixin surface split by SOLID/SRP domain modules."""

    pass


__all__ = ["WorkerExtractOpsMixin"]
