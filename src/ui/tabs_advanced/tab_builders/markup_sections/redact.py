from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .....core.i18n import tm
from ....widgets import FileSelectorWidget


def build_redact(self, layout) -> None:
    """텍스트 교정 (Redact)"""
    # 텍스트 교정 (Redact)
    grp_redact = QGroupBox(tm.get("grp_redact"))
    l_redact = QVBoxLayout(grp_redact)
    self.sel_redact = FileSelectorWidget()
    self.sel_redact.pathChanged.connect(self._update_preview)
    l_redact.addWidget(self.sel_redact)
    redact_opts = QHBoxLayout()
    redact_opts.addWidget(QLabel(tm.get("lbl_redact_text")))
    self.inp_redact = QLineEdit()
    self.inp_redact.setPlaceholderText(tm.get("ph_redact"))
    redact_opts.addWidget(self.inp_redact)
    l_redact.addLayout(redact_opts)
    b_redact = QPushButton(tm.get("btn_redact"))
    b_redact.setObjectName("dangerBtn")
    b_redact.setToolTip(tm.get("tooltip_redact"))
    b_redact.clicked.connect(self.action_redact_text)
    l_redact.addWidget(b_redact)
    area_row = QHBoxLayout()
    area_row.addWidget(QLabel(tm.get("lbl_redact_page")))
    self.spn_redact_page = QSpinBox()
    self.spn_redact_page.setRange(1, 9999)
    self.spn_redact_page.setValue(1)
    area_row.addWidget(self.spn_redact_page)
    area_row.addWidget(QLabel(tm.get("lbl_redact_rect")))
    self.inp_redact_rect = QLineEdit()
    self.inp_redact_rect.setPlaceholderText(tm.get("ph_redact_rect"))
    area_row.addWidget(self.inp_redact_rect)
    l_redact.addLayout(area_row)
    drag_row = QHBoxLayout()
    b_redact_drag = QPushButton(tm.get("btn_redact_drag_select"))
    b_redact_drag.setObjectName("secondaryBtn")
    b_redact_drag.setToolTip(tm.get("tooltip_redact_drag_select"))
    b_redact_drag.clicked.connect(self.action_start_redact_region_select)
    drag_row.addWidget(b_redact_drag)
    self.lbl_redact_drag_hint = QLabel(tm.get("hint_redact_drag_idle"))
    self.lbl_redact_drag_hint.setObjectName("desc")
    self.lbl_redact_drag_hint.setWordWrap(True)
    drag_row.addWidget(self.lbl_redact_drag_hint, 1)
    l_redact.addLayout(drag_row)
    b_redact_area = QPushButton(tm.get("btn_redact_area"))
    b_redact_area.setObjectName("dangerBtn")
    b_redact_area.clicked.connect(self.action_redact_area)
    l_redact.addWidget(b_redact_area)
    layout.addWidget(grp_redact)
    # 미리보기 드래그 선택 시그널 (한 번만 연결)
    if hasattr(self, "preview_image") and not getattr(self, "_redact_region_signal_connected", False):
        try:
            self.preview_image.regionSelected.connect(self._on_preview_region_selected_for_redact)
            self.preview_image.regionSelectModeChanged.connect(self._on_redact_region_mode_changed)
            self._redact_region_signal_connected = True
        except Exception:
            pass

