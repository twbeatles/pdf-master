"""Compatibility shim for core window mixin.

Keeps original import path stable while delegating implementation
to the folder-based window_core package.
"""

import logging

from .window_core import MainWindowCoreMixin  # noqa: F401 -- keeper used by main_window.py

logger = logging.getLogger(__name__)
