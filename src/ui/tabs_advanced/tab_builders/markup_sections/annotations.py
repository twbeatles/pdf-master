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


def build_annotations(self, layout) -> None:
    """주석 관리"""
    # 주석 관리
    grp_annot = QGroupBox(tm.get("grp_annot"))
    l_annot = QVBoxLayout(grp_annot)
    self.sel_annot = FileSelectorWidget()
    self.sel_annot.pathChanged.connect(self._update_preview)
    l_annot.addWidget(self.sel_annot)
    annot_btns = QHBoxLayout()
    b_list_annot = QPushButton(tm.get("btn_list_annot"))
    b_list_annot.setToolTip(tm.get("tooltip_list_annot"))
    b_list_annot.clicked.connect(self.action_list_annotations)
    annot_btns.addWidget(b_list_annot)
    b_remove_annot = QPushButton(tm.get("btn_remove_annot"))
    b_remove_annot.setObjectName("dangerBtn")
    b_remove_annot.setToolTip(tm.get("tooltip_remove_annot"))
    b_remove_annot.clicked.connect(self.action_remove_annotations)
    annot_btns.addWidget(b_remove_annot)
    l_annot.addLayout(annot_btns)
    layout.addWidget(grp_annot)

