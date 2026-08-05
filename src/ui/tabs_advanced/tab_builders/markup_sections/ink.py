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


def build_ink(self, layout) -> None:
    """v3.2: 프리핸드 드로잉"""
    # v3.2: 프리핸드 드로잉
    grp_ink = QGroupBox(tm.get("grp_ink"))
    l_ink = QVBoxLayout(grp_ink)
    self.sel_ink = FileSelectorWidget()
    self.sel_ink.pathChanged.connect(self._update_preview)
    l_ink.addWidget(self.sel_ink)
    ink_opts1 = QHBoxLayout()
    ink_opts1.addWidget(QLabel(tm.get("tab_page") + ":"))
    self.spn_ink_page = QSpinBox()
    self.spn_ink_page.setRange(1, 9999)
    self.spn_ink_page.setValue(1)
    ink_opts1.addWidget(self.spn_ink_page)
    ink_opts1.addWidget(QLabel(tm.get("lbl_line_width")))
    self.spn_ink_width = QSpinBox()
    self.spn_ink_width.setRange(1, 10)
    self.spn_ink_width.setValue(2)
    ink_opts1.addWidget(self.spn_ink_width)
    ink_opts1.addWidget(QLabel(tm.get("lbl_color")))
    self.cmb_ink_color = QComboBox()
    ink_colors = [
        (tm.get("color_blue_ink"), (0, 0, 1)),
        (tm.get("color_red_ink"), (1, 0, 0)),
        (tm.get("color_black_ink"), (0, 0, 0)),
        (tm.get("color_green_ink"), (0, 0.5, 0)),
    ]
    for label, value in ink_colors:
        self.cmb_ink_color.addItem(label, value)
    ink_opts1.addWidget(self.cmb_ink_color)
    ink_opts1.addStretch()
    l_ink.addLayout(ink_opts1)
    ink_guide = QLabel(tm.get("lbl_ink_guide"))
    ink_guide.setObjectName("desc")
    l_ink.addWidget(ink_guide)
    self.txt_ink_points = QLineEdit()
    self.txt_ink_points.setPlaceholderText(tm.get("ph_ink"))
    l_ink.addWidget(self.txt_ink_points)
    b_ink = QPushButton(tm.get("btn_add_ink"))
    b_ink.clicked.connect(self.action_add_ink_annotation)
    l_ink.addWidget(b_ink)
    layout.addWidget(grp_ink)

