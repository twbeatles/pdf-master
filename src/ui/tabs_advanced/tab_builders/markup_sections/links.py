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


def build_links(self, layout) -> None:
    """v4.5: 하이퍼링크 추가"""
    # v4.5: 하이퍼링크 추가
    grp_link = QGroupBox(tm.get("grp_add_link"))
    l_link = QVBoxLayout(grp_link)
    self.sel_link = FileSelectorWidget()
    self.sel_link.pathChanged.connect(self._update_preview)
    l_link.addWidget(self.sel_link)
    link_opts1 = QHBoxLayout()
    link_opts1.addWidget(QLabel(tm.get("lbl_link_type")))
    self.cmb_link_type = QComboBox()
    link_types = [
        (tm.get("link_url"), "url"),
        (tm.get("link_page"), "page"),
    ]
    for label, value in link_types:
        self.cmb_link_type.addItem(label, value)
    link_opts1.addWidget(self.cmb_link_type)
    link_opts1.addWidget(QLabel(tm.get("tab_page") + ":"))
    self.spn_link_page = QSpinBox()
    self.spn_link_page.setRange(1, 9999)
    self.spn_link_page.setValue(1)
    link_opts1.addWidget(self.spn_link_page)
    link_opts1.addStretch()
    l_link.addLayout(link_opts1)
    link_opts2 = QHBoxLayout()
    link_opts2.addWidget(QLabel(tm.get("lbl_link_url")))
    self.txt_link_url = QLineEdit()
    self.txt_link_url.setPlaceholderText(tm.get("ph_link_url"))
    link_opts2.addWidget(self.txt_link_url)
    l_link.addLayout(link_opts2)
    link_opts3 = QHBoxLayout()
    link_opts3.addWidget(QLabel(tm.get("lbl_target_page")))
    self.spn_link_target = QSpinBox()
    self.spn_link_target.setRange(1, 9999)
    self.spn_link_target.setValue(1)
    link_opts3.addWidget(self.spn_link_target)
    link_opts3.addWidget(QLabel(tm.get("lbl_link_area")))
    self.txt_link_area = QLineEdit()
    self.txt_link_area.setPlaceholderText(tm.get("ph_link_area"))
    link_opts3.addWidget(self.txt_link_area)
    link_opts3.addStretch()
    l_link.addLayout(link_opts3)
    b_link = QPushButton(tm.get("btn_add_link"))
    b_link.setObjectName("actionBtn")
    b_link.clicked.connect(self.action_add_hyperlink)
    l_link.addWidget(b_link)
    layout.addWidget(grp_link)

