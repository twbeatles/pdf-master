from __future__ import annotations

import logging

from .._typing import PreviewWidgetHost

logger = logging.getLogger(__name__)


class PreviewThemeMixin(PreviewWidgetHost):
    def set_theme(self, is_dark: bool):
        if is_dark:
            base_style = """
                QPdfView, QListWidget, QTreeView {
                    background: #161b22;
                    border: 1px solid #30363d;
                    border-radius: 8px;
                    color: #e6edf3;
                }
            """
        else:
            base_style = """
                QPdfView, QListWidget, QTreeView {
                    background: #ffffff;
                    border: 1px solid #d0d7de;
                    border-radius: 8px;
                    color: #1f2328;
                }
            """
        self.pdf_view.setStyleSheet(base_style)
        self.search_results.setStyleSheet(base_style)
        self.bookmark_tree.setStyleSheet(base_style)
