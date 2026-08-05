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


def build_text_markup(self, layout) -> None:
    """텍스트 마크업"""
    # 텍스트 마크업
    grp_markup = QGroupBox(tm.get("grp_markup"))
    l_markup = QVBoxLayout(grp_markup)
    self.sel_markup = FileSelectorWidget()
    self.sel_markup.pathChanged.connect(self._update_preview)
    l_markup.addWidget(self.sel_markup)
    markup_opts = QHBoxLayout()
    markup_opts.addWidget(QLabel(tm.get("lbl_keyword"))) # Reuse keyword label
    self.inp_markup = QLineEdit()
    self.inp_markup.setPlaceholderText(tm.get("ph_markup"))
    markup_opts.addWidget(self.inp_markup)
    markup_opts.addWidget(QLabel(tm.get("lbl_markup_type")))
    self.cmb_markup = QComboBox()
    markup_types = [
        (tm.get("type_underline"), "underline"),
        (tm.get("type_strikeout"), "strikeout"),
        (tm.get("type_squiggly"), "squiggly"),
    ]
    for label, value in markup_types:
        self.cmb_markup.addItem(label, value)
    markup_opts.addWidget(self.cmb_markup)
    l_markup.addLayout(markup_opts)
    b_markup = QPushButton(tm.get("btn_add_markup"))
    b_markup.clicked.connect(self.action_add_text_markup)
    l_markup.addWidget(b_markup)
    layout.addWidget(grp_markup)

