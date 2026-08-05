from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
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


def build_duplicate(self, layout) -> None:
    """페이지 복제"""
    # 페이지 복제
    grp_dup = QGroupBox(tm.get("grp_duplicate"))
    l_dup = QVBoxLayout(grp_dup)
    self.sel_dup = FileSelectorWidget()
    self.sel_dup.pathChanged.connect(self._update_preview)
    l_dup.addWidget(self.sel_dup)
    dup_opts = QHBoxLayout()
    dup_opts.addWidget(QLabel(tm.get("tab_page") + ":")) # Reuse tab_page key for "Page"
    self.spn_dup_page = QSpinBox()
    self.spn_dup_page.setRange(1, 9999)
    dup_opts.addWidget(self.spn_dup_page)
    dup_opts.addWidget(QLabel(tm.get("lbl_dup_count")))
    self.spn_dup_count = QSpinBox()
    self.spn_dup_count.setRange(1, 100)
    self.spn_dup_count.setValue(1)
    dup_opts.addWidget(self.spn_dup_count)
    dup_opts.addStretch()
    l_dup.addLayout(dup_opts)
    b_dup = QPushButton(tm.get("btn_duplicate"))
    b_dup.clicked.connect(self.action_duplicate_page)
    l_dup.addWidget(b_dup)
    layout.addWidget(grp_dup)

