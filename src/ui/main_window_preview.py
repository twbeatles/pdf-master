"""Compatibility shim for preview mixin.

Keeps original import path stable while delegating implementation
to the folder-based window_preview package.
"""

import logging


from .window_preview import MainWindowPreviewMixin  # noqa: F401 -- keeper used by main_window.py,test_preview_doc_reuse.py

logger = logging.getLogger(__name__)
