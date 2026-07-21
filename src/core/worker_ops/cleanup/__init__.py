from __future__ import annotations

from .blank_dedupe import WorkerCleanupBlankDedupeMixin
from .bookmark_ops import WorkerCleanupBookmarkOpsMixin
from .helpers import (
    _collect_heading_toc,
    _content_bbox,
    _is_blank_page,
    _page_drawing_count,
    _page_image_count,
    _page_signature,
    _page_text_len,
)
from .sanitize_nup import WorkerCleanupSanitizeNupMixin


class WorkerCleanupOpsMixin(
    WorkerCleanupBlankDedupeMixin,
    WorkerCleanupBookmarkOpsMixin,
    WorkerCleanupSanitizeNupMixin,
):
    """Composed WorkerCleanupOpsMixin surface split by SOLID/SRP domain modules."""

    pass


__all__ = [
    "WorkerCleanupOpsMixin",
    "_collect_heading_toc",
    "_content_bbox",
    "_is_blank_page",
    "_page_drawing_count",
    "_page_image_count",
    "_page_signature",
    "_page_text_len",
]
