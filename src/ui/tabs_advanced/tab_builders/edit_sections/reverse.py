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


def build_reverse(self, layout) -> None:
    """역순 정렬"""
    # 역순 정렬
    grp_rev = QGroupBox(tm.get("grp_reverse_page"))
    l_rev = QVBoxLayout(grp_rev)
    self.sel_rev = FileSelectorWidget()
    self.sel_rev.pathChanged.connect(self._update_preview)
    l_rev.addWidget(self.sel_rev)
    b_rev = QPushButton(tm.get("btn_reverse_page"))
    b_rev.setToolTip(tm.get("tooltip_reverse_pages"))
    b_rev.clicked.connect(self.action_reverse_pages)
    l_rev.addWidget(b_rev)
    layout.addWidget(grp_rev)

