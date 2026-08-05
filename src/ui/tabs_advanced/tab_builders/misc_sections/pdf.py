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


def build_pdf(self, layout) -> None:
    """PDF 비교"""
    # PDF 비교
    grp_compare = QGroupBox(tm.get("grp_compare"))
    l_compare = QVBoxLayout(grp_compare)
    l_compare.addWidget(QLabel(tm.get("lbl_file_1")))
    self.sel_compare1 = FileSelectorWidget()
    l_compare.addWidget(self.sel_compare1)
    l_compare.addWidget(QLabel(tm.get("lbl_file_2")))
    self.sel_compare2 = FileSelectorWidget()
    l_compare.addWidget(self.sel_compare2)
    compare_mode_row = QHBoxLayout()
    compare_mode_row.addWidget(QLabel(tm.get("lbl_compare_mode")))
    self.cmb_compare_mode = QComboBox()
    for label, value in (
        (tm.get("compare_mode_text"), "text"),
        (tm.get("compare_mode_visual"), "visual"),
        (tm.get("compare_mode_both"), "both"),
    ):
        self.cmb_compare_mode.addItem(label, value)
    compare_mode_row.addWidget(self.cmb_compare_mode)
    compare_mode_row.addStretch()
    l_compare.addLayout(compare_mode_row)
    self.chk_compare_visual = QCheckBox(tm.get("chk_compare_visual_diff"))
    self.chk_compare_visual.setChecked(False)
    l_compare.addWidget(self.chk_compare_visual)
    b_compare = QPushButton(tm.get("btn_compare_pdf"))
    b_compare.setToolTip(tm.get("tooltip_compare"))
    b_compare.clicked.connect(self.action_compare_pdfs)
    l_compare.addWidget(b_compare)
    layout.addWidget(grp_compare)

