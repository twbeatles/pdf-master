"""Compatibility shim for undo mixin.

Keeps original import path stable while delegating implementation
to the folder-based window_undo package.
"""

import logging
import os
import shutil
import time

from PyQt6.QtWidgets import QMessageBox

from ..core.i18n import tm
from .window_undo import MainWindowUndoMixin

logger = logging.getLogger(__name__)
