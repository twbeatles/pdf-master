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


def build_resize(self, layout) -> None:
    """페이지 크기 변경"""
    # 페이지 크기 변경
    grp_resize = QGroupBox(tm.get("grp_resize_page"))
    l_resize = QVBoxLayout(grp_resize)
    self.sel_resize = FileSelectorWidget()
    self.sel_resize.pathChanged.connect(self._update_preview)
    l_resize.addWidget(self.sel_resize)
    resize_opts = QHBoxLayout()
    resize_opts.addWidget(QLabel(tm.get("lbl_size")))
    self.cmb_resize = QComboBox()
    for size in ["A4", "A3", "Letter", "Legal"]:
        self.cmb_resize.addItem(size, size)
    resize_opts.addWidget(self.cmb_resize)
    resize_opts.addStretch()
    l_resize.addLayout(resize_opts)
    b_resize = QPushButton(tm.get("btn_resize"))
    b_resize.clicked.connect(self.action_resize_pages)
    l_resize.addWidget(b_resize)
    layout.addWidget(grp_resize)

