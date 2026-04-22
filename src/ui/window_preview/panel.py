import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from ...core.i18n import tm
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

    self.preview_image = ZoomablePreviewWidget()
    self.preview_image.setMinimumSize(250, 350)
    self.preview_image.set_controlled_mode(True)
    self.preview_image.pageChanged.connect(self._on_preview_page_requested)
    self.preview_image.renderRequested.connect(self._schedule_preview_rerender)
    self.preview_image.searchRequested.connect(self._search_preview_text)
    self.preview_image.searchStepRequested.connect(self._step_preview_search)
    self.preview_image.searchCleared.connect(self._clear_preview_search)
    self.preview_image.searchVisibilityChanged.connect(
        self._on_preview_search_visibility_changed
    )
    self.preview_image.set_search_panel_visible(
        bool(self.settings.get("preview_search_expanded", True))
    )
    layout.addWidget(self.preview_image, 1)

    self.btn_prev_page = self.preview_image.btn_prev
    self.page_counter = self.preview_image.page_label
    self.btn_next_page = self.preview_image.btn_next

    footer_layout = QHBoxLayout()
    footer_layout.addStretch()
    self.btn_print_preview = QPushButton(tm.get("btn_print_preview"))
    self.btn_print_preview.setObjectName("secondaryBtn")
    self.btn_print_preview.setMinimumHeight(30)
    self.btn_print_preview.setSizePolicy(
        QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
    )
    self.btn_print_preview.setToolTip(tm.get("tooltip_print_preview"))
    self.btn_print_preview.clicked.connect(self._print_current_preview)
    footer_layout.addWidget(self.btn_print_preview)

    layout.addLayout(footer_layout)
    self._set_preview_navigation_enabled(False)
    return panel

def _set_preview_navigation_enabled(self, enabled: bool):
    self.preview_image.set_navigation_enabled(enabled)
    self.preview_image.set_search_available(enabled)
    self.btn_print_preview.setEnabled(enabled)
    if not enabled:
        self.preview_image.set_page_state(0, 0)
