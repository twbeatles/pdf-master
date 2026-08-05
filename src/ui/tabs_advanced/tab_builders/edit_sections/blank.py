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


def build_blank(self, layout) -> None:
    """빈 페이지 삽입"""
    # 빈 페이지 삽입
    grp_blank = QGroupBox(tm.get("grp_blank_page"))
    l_blank = QVBoxLayout(grp_blank)
    self.sel_blank = FileSelectorWidget()
    self.sel_blank.pathChanged.connect(self._update_preview)
    l_blank.addWidget(self.sel_blank)
    opt_blank = QHBoxLayout()
    opt_blank.addWidget(QLabel(tm.get("lbl_blank_pos")))
    self.spn_blank_pos = QSpinBox()
    self.spn_blank_pos.setRange(1, 999)
    self.spn_blank_pos.setValue(1)
    opt_blank.addWidget(self.spn_blank_pos)
    opt_blank.addStretch()
    l_blank.addLayout(opt_blank)
    b_blank = QPushButton(tm.get("btn_insert_blank"))
    b_blank.clicked.connect(self.action_blank_page)
    l_blank.addWidget(b_blank)
    layout.addWidget(grp_blank)

