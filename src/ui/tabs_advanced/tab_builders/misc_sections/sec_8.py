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


def build_sec_8(self, layout) -> None:
    """양식 작성"""
    # 양식 작성
    grp_form = QGroupBox(tm.get("grp_form"))
    l_form = QVBoxLayout(grp_form)
    self.sel_form = FileSelectorWidget()
    self.sel_form.pathChanged.connect(self._update_preview)
    l_form.addWidget(self.sel_form)
    self.form_fields_list = QListWidget()
    self.form_fields_list.setMaximumHeight(80)
    self.form_fields_list.setToolTip(tm.get("tooltip_form_list"))
    self.form_fields_list.itemDoubleClicked.connect(self._edit_form_field)
    l_form.addWidget(self.form_fields_list)
    btn_form_layout = QHBoxLayout()
    b_detect = QPushButton(tm.get("btn_detect_fields"))
    b_detect.clicked.connect(self.action_detect_fields)
    btn_form_layout.addWidget(b_detect)
    b_fill = QPushButton(tm.get("btn_save_form"))
    b_fill.setObjectName("actionBtn")
    b_fill.clicked.connect(self.action_fill_form)
    btn_form_layout.addWidget(b_fill)
    b_flatten = QPushButton(tm.get("btn_flatten_form"))
    b_flatten.clicked.connect(self.action_flatten_form)
    btn_form_layout.addWidget(b_flatten)
    l_form.addLayout(btn_form_layout)
    layout.addWidget(grp_form)

