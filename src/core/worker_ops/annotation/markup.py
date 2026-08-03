"""WorkerAnnotationMarkupMixin — highlight + textbox 합성 facade."""
from __future__ import annotations

from .highlight_markup import WorkerAnnotationHighlightMixin
from .textbox import WorkerAnnotationTextboxMixin


class WorkerAnnotationMarkupMixin(
    WorkerAnnotationHighlightMixin,
    WorkerAnnotationTextboxMixin,
):
    """호환 surface: highlight/markup + textbox 삽입 계열."""

    pass


__all__ = ["WorkerAnnotationMarkupMixin"]
