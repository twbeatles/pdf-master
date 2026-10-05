from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from ....fluent_widgets import PrimaryButton, PushButton, QComboBox, QLineEdit, QSpinBox

from .....core.i18n import tm
from ....widgets import FileSelectorWidget
from ....form_rows import pair_grid


def build_sticky(self, layout) -> None:
    """v3.2: 스티키 노트 주석"""
    # v3.2: 스티키 노트 주석
    grp_sticky = QGroupBox(tm.get("grp_sticky"))
    l_sticky = QVBoxLayout(grp_sticky)
    self.sel_sticky = FileSelectorWidget()
    self.sel_sticky.pathChanged.connect(self._update_preview)
    l_sticky.addWidget(self.sel_sticky)
    self.spn_sticky_x = QSpinBox()
    self.spn_sticky_x.setRange(0, 999)
    self.spn_sticky_x.setValue(100)
    self.spn_sticky_y = QSpinBox()
    self.spn_sticky_y.setRange(0, 999)
    self.spn_sticky_y.setValue(100)
    self.spn_sticky_page = QSpinBox()
    self.spn_sticky_page.setRange(1, 9999)
    self.spn_sticky_page.setValue(1)
    l_sticky.addLayout(
        pair_grid(
            [
                (tm.get("lbl_pos_x"), self.spn_sticky_x),
                (tm.get("lbl_pos_y"), self.spn_sticky_y),
                (tm.get("lbl_page"), self.spn_sticky_page),
            ]
        )
    )
    sticky_opts2 = QHBoxLayout()
    sticky_opts2.addWidget(QLabel(tm.get("lbl_icon")))
    self.cmb_sticky_icon = QComboBox()
    for icon_name in ("Note", "Comment", "Key", "Help", "Insert", "Paragraph"):
        self.cmb_sticky_icon.addItem(tm.get(f"sticky_icon_{icon_name.lower()}"), userData=icon_name)
    sticky_opts2.addWidget(self.cmb_sticky_icon)
    sticky_opts2.addStretch()
    l_sticky.addLayout(sticky_opts2)
    l_sticky.addWidget(QLabel(tm.get("lbl_content")))
    self.txt_sticky_content = QLineEdit()
    self.txt_sticky_content.setPlaceholderText(tm.get("ph_sticky"))
    l_sticky.addWidget(self.txt_sticky_content)
    b_sticky = PrimaryButton(tm.get("btn_add_sticky"))
    b_sticky.setObjectName("actionBtn")
    b_sticky.clicked.connect(self.action_add_sticky_note)
    l_sticky.addWidget(b_sticky)
    layout.addWidget(grp_sticky)

