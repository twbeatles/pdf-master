import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGroupBox, QLabel, QVBoxLayout

from ...core.i18n import tm
from ..zoomable_preview import ZoomablePreviewWidget

logger = logging.getLogger(__name__)


def _create_preview_panel(self):
    panel = QGroupBox(tm.get("preview_title"))
    layout = QVBoxLayout(panel)
    layout.setSpacing(10)

    self.preview_label = QLabel(tm.get("preview_default"))
    self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.preview_label.setStyleSheet("color: #666; padding: 10px; font-size: 12px;")
    self.preview_label.setWordWrap(True)
    self.preview_label.setMaximumHeight(120)
    layout.addWidget(self.preview_label)

    self.preview_image = ZoomablePreviewWidget()
    self.preview_image.setMinimumSize(250, 350)
    self.preview_image.pageChanged.connect(self._on_preview_page_requested)
    self.preview_image.printRequested.connect(self._print_current_preview)
    self.preview_image.pageSetupRequested.connect(self._open_page_setup)
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
    self.btn_print_preview = self.preview_image.btn_print

    self._set_preview_navigation_enabled(False)
    return panel


def _set_preview_navigation_enabled(self, enabled: bool):
    self.preview_image.set_navigation_enabled(enabled)
    self.preview_image.btn_print.setEnabled(enabled)
    self.preview_image.btn_page_setup.setEnabled(enabled)
    if not enabled:
        self.preview_image.set_page_state(0, 0)
