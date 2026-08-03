import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ...core.i18n import tm
from ..zoomable_preview import ZoomablePreviewWidget

logger = logging.getLogger(__name__)


def _create_preview_panel(self):
    panel = QGroupBox(tm.get("preview_title"))
    self.preview_panel = panel
    layout = QVBoxLayout(panel)
    layout.setSpacing(10)

    # 헤더: 상태 라벨 + 포커스 토글
    header = QHBoxLayout()
    self.preview_label = QLabel(tm.get("preview_default"))
    self.preview_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    self.preview_label.setStyleSheet("color: #666; padding: 4px; font-size: 12px;")
    self.preview_label.setWordWrap(True)
    self.preview_label.setMaximumHeight(120)
    header.addWidget(self.preview_label, 1)

    self.btn_preview_focus = QPushButton(tm.get("btn_preview_focus_enter"))
    self.btn_preview_focus.setObjectName("toolbarSecondaryBtn")
    self.btn_preview_focus.setToolTip(tm.get("tooltip_preview_focus_enter"))
    self.btn_preview_focus.clicked.connect(self._toggle_preview_focus_mode)
    header.addWidget(self.btn_preview_focus)
    layout.addLayout(header)

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

    # 포커스 모드 전용 미니 툴바 (텍스트 상자 배치·적용)
    self.preview_focus_bar = QWidget()
    focus_bar_layout = QHBoxLayout(self.preview_focus_bar)
    focus_bar_layout.setContentsMargins(0, 0, 0, 0)
    focus_bar_layout.setSpacing(8)

    self.btn_focus_place_textbox = QPushButton(tm.get("btn_textbox_drag_select"))
    self.btn_focus_place_textbox.setObjectName("toolbarSecondaryBtn")
    self.btn_focus_place_textbox.setToolTip(tm.get("tooltip_textbox_drag_select"))
    self.btn_focus_place_textbox.clicked.connect(self.action_start_textbox_region_select)
    focus_bar_layout.addWidget(self.btn_focus_place_textbox)

    self.btn_focus_insert_textbox = QPushButton(tm.get("btn_insert_textbox"))
    self.btn_focus_insert_textbox.setObjectName("toolbarBtn")
    self.btn_focus_insert_textbox.clicked.connect(self.action_insert_textbox)
    focus_bar_layout.addWidget(self.btn_focus_insert_textbox)

    self.lbl_focus_hint = QLabel(tm.get("hint_preview_focus_bar"))
    self.lbl_focus_hint.setObjectName("desc")
    self.lbl_focus_hint.setWordWrap(True)
    focus_bar_layout.addWidget(self.lbl_focus_hint, 1)

    self.preview_focus_bar.setVisible(False)
    layout.addWidget(self.preview_focus_bar)

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
