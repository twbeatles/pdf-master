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


def build_split(self, layout) -> None:
    """PDF 분할"""
    # PDF 분할
    grp_split = QGroupBox(tm.get("grp_split_pdf"))
    l_split = QVBoxLayout(grp_split)
    self.sel_split_adv = FileSelectorWidget()
    self.sel_split_adv.pathChanged.connect(self._update_preview)
    l_split.addWidget(self.sel_split_adv)
    opt_split = QHBoxLayout()
    opt_split.addWidget(QLabel(tm.get("lbl_split_mode")))
    self.cmb_split_mode = QComboBox()
    split_modes = [
        (tm.get("mode_split_page"), "each"),
        (tm.get("mode_split_range"), "range"),
        (tm.get("mode_split_bookmark"), "bookmarks"),
    ]
    for label, value in split_modes:
        self.cmb_split_mode.addItem(label, value)
    opt_split.addWidget(self.cmb_split_mode)
    self.inp_split_range = QLineEdit()
    self.inp_split_range.setPlaceholderText(tm.get("ph_split_range"))
    opt_split.addWidget(self.inp_split_range)
    l_split.addLayout(opt_split)
    b_split = QPushButton(tm.get("btn_split_pdf"))
    b_split.setToolTip(tm.get("tooltip_split_pdf"))
    b_split.clicked.connect(self.action_split_adv)
    l_split.addWidget(b_split)
    layout.addWidget(grp_split)

