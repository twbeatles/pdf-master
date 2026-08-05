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


def build_sticky(self, layout) -> None:
    """v3.2: 스티키 노트 주석"""
    # v3.2: 스티키 노트 주석
    grp_sticky = QGroupBox(tm.get("grp_sticky"))
    l_sticky = QVBoxLayout(grp_sticky)
    self.sel_sticky = FileSelectorWidget()
    self.sel_sticky.pathChanged.connect(self._update_preview)
    l_sticky.addWidget(self.sel_sticky)
    sticky_opts1 = QHBoxLayout()
    sticky_opts1.addWidget(QLabel(tm.get("lbl_pos_x")))
    self.spn_sticky_x = QSpinBox()
    self.spn_sticky_x.setRange(0, 999)
    self.spn_sticky_x.setValue(100)
    sticky_opts1.addWidget(self.spn_sticky_x)
    sticky_opts1.addWidget(QLabel(tm.get("lbl_pos_y")))
    self.spn_sticky_y = QSpinBox()
    self.spn_sticky_y.setRange(0, 999)
    self.spn_sticky_y.setValue(100)
    sticky_opts1.addWidget(self.spn_sticky_y)
    sticky_opts1.addWidget(QLabel(tm.get("tab_page") + ":"))
    self.spn_sticky_page = QSpinBox()
    self.spn_sticky_page.setRange(1, 9999)
    self.spn_sticky_page.setValue(1)
    sticky_opts1.addWidget(self.spn_sticky_page)
    sticky_opts1.addStretch()
    l_sticky.addLayout(sticky_opts1)
    sticky_opts2 = QHBoxLayout()
    sticky_opts2.addWidget(QLabel(tm.get("lbl_icon")))
    self.cmb_sticky_icon = QComboBox()
    self.cmb_sticky_icon.addItems(["Note", "Comment", "Key", "Help", "Insert", "Paragraph"])
    sticky_opts2.addWidget(self.cmb_sticky_icon)
    sticky_opts2.addStretch()
    l_sticky.addLayout(sticky_opts2)
    l_sticky.addWidget(QLabel(tm.get("lbl_content")))
    self.txt_sticky_content = QLineEdit()
    self.txt_sticky_content.setPlaceholderText(tm.get("ph_sticky"))
    l_sticky.addWidget(self.txt_sticky_content)
    b_sticky = QPushButton(tm.get("btn_add_sticky"))
    b_sticky.clicked.connect(self.action_add_sticky_note)
    l_sticky.addWidget(b_sticky)
    layout.addWidget(grp_sticky)

