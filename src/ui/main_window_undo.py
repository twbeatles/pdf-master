"""Compatibility shim for undo mixin.

Keeps original import path stable while delegating implementation
to the folder-based window_undo package.
"""

import logging

from .window_undo import MainWindowUndoMixin  # noqa: F401 -- keeper used by main_window.py,test_undo_backup_flow.py

logger = logging.getLogger(__name__)
