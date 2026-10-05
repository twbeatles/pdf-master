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
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from ....fluent_widgets import PrimaryButton, QSpinBox

from .....core.i18n import tm
from ....widgets import FileSelectorWidget
from ....form_rows import pair_grid


def build_v4_5_3_f_07_ui(self, layout) -> None:
    """v4.5.3: 페이지 교체 (F-07 UI 노출)"""
    # v4.5.3: 페이지 교체 (F-07 UI 노출)
    grp_replace = QGroupBox(tm.get("grp_replace_page"))
    l_replace = QVBoxLayout(grp_replace)
    l_replace.addWidget(QLabel(tm.get("lbl_target_pdf")))
    self.sel_replace_target = FileSelectorWidget()
    self.sel_replace_target.pathChanged.connect(self._update_preview)
    l_replace.addWidget(self.sel_replace_target)
    l_replace.addWidget(QLabel(tm.get("lbl_source_pdf")))
    self.sel_replace_source = FileSelectorWidget()
    l_replace.addWidget(self.sel_replace_source)
    self.spn_replace_target_page = QSpinBox()
    self.spn_replace_target_page.setRange(1, 9999)
    self.spn_replace_target_page.setValue(1)
    self.spn_replace_source_page = QSpinBox()
    self.spn_replace_source_page.setRange(1, 9999)
    self.spn_replace_source_page.setValue(1)
    l_replace.addLayout(
        pair_grid(
            [
                (tm.get("lbl_replace_target_page"), self.spn_replace_target_page),
                (tm.get("lbl_replace_source_page"), self.spn_replace_source_page),
            ],
            columns=1,
        )
    )
    b_replace = PrimaryButton(tm.get("btn_replace_page"))
    b_replace.setObjectName("actionBtn")
    b_replace.clicked.connect(self.action_replace_page)
    l_replace.addWidget(b_replace)
    layout.addWidget(grp_replace)

