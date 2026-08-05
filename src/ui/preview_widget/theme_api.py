from __future__ import annotations

from .._typing import PreviewWidgetHost
import logging
from PyQt6.QtCore import QEvent, QModelIndex, QPointF, QRect, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QColor
from PyQt6.QtPdf import QPdfBookmarkModel, QPdfDocument, QPdfSearchModel
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QTreeView,
    QVBoxLayout,
    QWidget,
)
from ...core.i18n import tm
logger = logging.getLogger(__name__)
from .region_select import (
    RegionSelectOverlay,
    compute_page_display_rect,
    format_rect_coords,
    map_page_points_to_viewport_rect,
    map_viewport_rect_to_page_points,
)
from .queue_overlay import QueueGhostOverlay
from .search import PreviewSearchLineEdit
from .text_placement import TextPlacementOverlay


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
