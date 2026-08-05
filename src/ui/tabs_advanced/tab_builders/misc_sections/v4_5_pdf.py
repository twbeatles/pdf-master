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


def build_v4_5_pdf(self, layout) -> None:
    """v4.5: 다른 PDF에서 페이지 복사"""
    # v4.5: 다른 PDF에서 페이지 복사
    grp_copy_page = QGroupBox(tm.get("grp_copy_page"))
    l_copy = QVBoxLayout(grp_copy_page)
    l_copy.addWidget(QLabel(tm.get("lbl_target_pdf")))
    self.sel_copy_target = FileSelectorWidget()
    self.sel_copy_target.pathChanged.connect(self._update_preview)
    l_copy.addWidget(self.sel_copy_target)
    l_copy.addWidget(QLabel(tm.get("lbl_source_pdf")))
    self.sel_copy_source = FileSelectorWidget()
    l_copy.addWidget(self.sel_copy_source)
    copy_opts = QHBoxLayout()
    copy_opts.addWidget(QLabel(tm.get("lbl_copy_pages")))
    self.txt_copy_pages = QLineEdit()
    self.txt_copy_pages.setPlaceholderText(tm.get("ph_copy_pages"))
    copy_opts.addWidget(self.txt_copy_pages)
    copy_opts.addWidget(QLabel(tm.get("lbl_insert_pos")))
    self.spn_copy_insert = QSpinBox()
    self.spn_copy_insert.setRange(-1, 9999)
    self.spn_copy_insert.setValue(-1)
    self.spn_copy_insert.setToolTip(tm.get("tooltip_insert_pos"))
    copy_opts.addWidget(self.spn_copy_insert)
    copy_opts.addStretch()
    l_copy.addLayout(copy_opts)
    b_copy_pages = QPushButton(tm.get("btn_copy_pages"))
    b_copy_pages.setObjectName("actionBtn")
    b_copy_pages.clicked.connect(self.action_copy_pages)
    l_copy.addWidget(b_copy_pages)
    layout.addWidget(grp_copy_page)

