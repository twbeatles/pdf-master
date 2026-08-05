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


def build_background(self, layout) -> None:
    """배경색 추가"""
    # 배경색 추가
    grp_bg = QGroupBox(tm.get("grp_bg_color"))
    l_bg = QVBoxLayout(grp_bg)
    self.sel_bg = FileSelectorWidget()
    self.sel_bg.pathChanged.connect(self._update_preview)
    l_bg.addWidget(self.sel_bg)
    bg_opts = QHBoxLayout()
    bg_opts.addWidget(QLabel(tm.get("lbl_color")))
    self.cmb_bg_color = QComboBox()
    bg_colors = [
        (tm.get("color_cream"), [1, 1, 0.9]),
        (tm.get("color_light_yellow"), [1, 1, 0.8]),
        (tm.get("color_light_blue"), [0.9, 0.95, 1]),
        (tm.get("color_light_gray"), [0.95, 0.95, 0.95]),
        (tm.get("color_white"), [1, 1, 1]),
    ]
    for label, value in bg_colors:
        self.cmb_bg_color.addItem(label, value)
    bg_opts.addWidget(self.cmb_bg_color)
    bg_opts.addStretch()
    l_bg.addLayout(bg_opts)
    b_bg = QPushButton(tm.get("btn_add_bg"))
    b_bg.clicked.connect(self.action_add_background)
    l_bg.addWidget(b_bg)
    layout.addWidget(grp_bg)

