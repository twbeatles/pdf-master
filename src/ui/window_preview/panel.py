import logging
import os

import fitz
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QPixmap
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.i18n import tm
from ...core.settings import save_settings
from ..widgets import FileSelectorWidget
from ..zoomable_preview import ZoomablePreviewWidget

logger = logging.getLogger(__name__)

def _create_preview_panel(self):
    panel = QGroupBox(tm.get("preview_title"))
    layout = QVBoxLayout(panel)
    layout.setSpacing(10)
    self._ensure_preview_cache()

    self.preview_label = QLabel(tm.get("preview_default"))
    self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.preview_label.setStyleSheet("color: #666; padding: 10px; font-size: 12px;")
    self.preview_label.setWordWrap(True)
    self.preview_label.setMaximumHeight(120)
    layout.addWidget(self.preview_label)

    self.preview_image = QLabel()
    self.preview_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.preview_image.setMinimumSize(250, 350)
    self.preview_image.setStyleSheet("background: #0f0f23; border-radius: 8px; border: 1px solid #333;")
    self.preview_image.setSizePolicy(
        self.preview_image.sizePolicy().horizontalPolicy(),
        self.preview_image.sizePolicy().verticalPolicy(),
    )
    layout.addWidget(self.preview_image, 1)

    nav_layout = QHBoxLayout()
    self.btn_prev_page = QPushButton(tm.get("prev_page"))
    self.btn_prev_page.setObjectName("navBtn")
    self.btn_prev_page.setFixedSize(80, 30)
    self.btn_prev_page.clicked.connect(self._prev_preview_page)
    nav_layout.addWidget(self.btn_prev_page)

    self.page_counter = QLabel("1 / 1")
    self.page_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.page_counter.setStyleSheet("font-weight: bold; min-width: 60px; color: #eaeaea;")
    nav_layout.addWidget(self.page_counter)

    self.btn_next_page = QPushButton(tm.get("next_page"))
    self.btn_next_page.setObjectName("navBtn")
    self.btn_next_page.setFixedSize(80, 30)
    self.btn_next_page.clicked.connect(self._next_preview_page)
    nav_layout.addWidget(self.btn_next_page)

    self.btn_print_preview = QPushButton(tm.get("btn_print_preview"))
    self.btn_print_preview.setObjectName("secondaryBtn")
    self.btn_print_preview.setFixedSize(70, 30)
    self.btn_print_preview.setToolTip(tm.get("tooltip_print_preview"))
    self.btn_print_preview.clicked.connect(self._print_current_preview)
    nav_layout.addWidget(self.btn_print_preview)

    layout.addLayout(nav_layout)
    self._set_preview_navigation_enabled(False)
    return panel

def _set_preview_navigation_enabled(self, enabled: bool):
    self.btn_prev_page.setEnabled(enabled)
    self.btn_next_page.setEnabled(enabled)
    self.btn_print_preview.setEnabled(enabled)
    if not enabled:
        self.page_counter.setText("0 / 0")
