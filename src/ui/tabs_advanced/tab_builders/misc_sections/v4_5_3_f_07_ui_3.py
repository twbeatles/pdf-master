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


def build_v4_5_3_f_07_ui_3(self, layout) -> None:
    """v4.5.3: 기본 주석 추가 (F-07 UI 노출)"""
    # v4.5.3: 기본 주석 추가 (F-07 UI 노출)
    grp_add_annotation = QGroupBox(tm.get("grp_add_annotation_basic"))
    l_add_annotation = QVBoxLayout(grp_add_annotation)
    self.sel_add_annot = FileSelectorWidget()
    self.sel_add_annot.pathChanged.connect(self._update_preview)
    l_add_annotation.addWidget(self.sel_add_annot)
    annot_opts = QHBoxLayout()
    annot_opts.addWidget(QLabel(tm.get("tab_page") + ":"))
    self.spn_add_annot_page = QSpinBox()
    self.spn_add_annot_page.setRange(1, 9999)
    self.spn_add_annot_page.setValue(1)
    annot_opts.addWidget(self.spn_add_annot_page)
    annot_opts.addWidget(QLabel(tm.get("lbl_annotation_type")))
    self.cmb_add_annot_type = QComboBox()
    self.cmb_add_annot_type.addItem(tm.get("annot_type_text"), "text")
    self.cmb_add_annot_type.addItem(tm.get("annot_type_freetext"), "freetext")
    annot_opts.addWidget(self.cmb_add_annot_type)
    annot_opts.addStretch()
    l_add_annotation.addLayout(annot_opts)
    l_add_annotation.addWidget(QLabel(tm.get("lbl_annotation_text")))
    self.txt_add_annot_text = QLineEdit()
    self.txt_add_annot_text.setPlaceholderText(tm.get("ph_annotation_text"))
    l_add_annotation.addWidget(self.txt_add_annot_text)
    l_add_annotation.addWidget(QLabel(tm.get("lbl_annotation_point")))
    self.txt_add_annot_point = QLineEdit()
    self.txt_add_annot_point.setPlaceholderText(tm.get("ph_annotation_point"))
    l_add_annotation.addWidget(self.txt_add_annot_point)
    l_add_annotation.addWidget(QLabel(tm.get("lbl_annotation_rect")))
    self.txt_add_annot_rect = QLineEdit()
    self.txt_add_annot_rect.setPlaceholderText(tm.get("ph_annotation_rect"))
    l_add_annotation.addWidget(self.txt_add_annot_rect)
    b_add_annotation = QPushButton(tm.get("btn_add_annotation_basic"))
    b_add_annotation.setObjectName("actionBtn")
    b_add_annotation.clicked.connect(self.action_add_annotation_basic)
    l_add_annotation.addWidget(b_add_annotation)
    layout.addWidget(grp_add_annotation)

