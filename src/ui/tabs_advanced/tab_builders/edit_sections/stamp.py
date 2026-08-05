from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
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


def build_stamp(self, layout) -> None:
    """스탬프"""
    # 스탬프
    grp_stamp = QGroupBox(tm.get("grp_stamp"))
    l_stamp = QVBoxLayout(grp_stamp)
    self.sel_stamp = FileSelectorWidget()
    self.sel_stamp.pathChanged.connect(self._update_preview)
    l_stamp.addWidget(self.sel_stamp)
    opt_stamp = QHBoxLayout()
    opt_stamp.addWidget(QLabel(tm.get("lbl_stamp_text")))
    self.cmb_stamp = QComboBox()
    self.cmb_stamp.addItems([tm.get("stamp_confidential"), tm.get("stamp_approved"), tm.get("stamp_draft"), tm.get("stamp_final"), tm.get("stamp_no_copy")])
    self.cmb_stamp.setEditable(True)
    opt_stamp.addWidget(self.cmb_stamp)
    opt_stamp.addWidget(QLabel(tm.get("lbl_stamp_pos")))
    self.cmb_stamp_pos = QComboBox()
    stamp_positions = [
        (tm.get("pos_top_right"), "top-right"),
        (tm.get("pos_top_left"), "top-left"),
        (tm.get("pos_bottom_right"), "bottom-right"),
        (tm.get("pos_bottom_left"), "bottom-left"),
    ]
    for label, value in stamp_positions:
        self.cmb_stamp_pos.addItem(label, value)
    opt_stamp.addWidget(self.cmb_stamp_pos)
    l_stamp.addLayout(opt_stamp)
    b_stamp = QPushButton(tm.get("btn_add_stamp"))
    b_stamp.clicked.connect(self.action_stamp)
    l_stamp.addWidget(b_stamp)
    layout.addWidget(grp_stamp)

