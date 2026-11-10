"""Compatibility shim for advanced tabs mixin.

This module keeps the original import path stable while delegating
implementation to the folder-based tabs_advanced package.
"""

from PySide6.QtWidgets import (
    QFileDialog,  # noqa: F401 -- keeper used by test_advanced_new_modes_ui_flow.py,test_freehand_signature_ui_flow.py,test_link_index_policy.py,test_page_index_policy.py
    QMessageBox,  # noqa: F401 -- keeper used by test_advanced_new_modes_ui_flow.py,test_freehand_signature_ui_flow.py,test_link_index_policy.py,test_page_index_policy.py
)

from .tabs_advanced import MainWindowTabsAdvancedMixin

__all__ = ["MainWindowTabsAdvancedMixin"]
