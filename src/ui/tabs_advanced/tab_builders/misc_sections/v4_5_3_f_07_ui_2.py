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


def build_v4_5_3_f_07_ui_2(self, layout) -> None:
    """v4.5.3: 북마크 설정 (F-07 UI 노출)"""
    # v4.5.3: 북마크 설정 (F-07 UI 노출)
    grp_set_bookmarks = QGroupBox(tm.get("grp_set_bookmarks"))
    l_set_bookmarks = QVBoxLayout(grp_set_bookmarks)
    self.sel_set_bookmarks = FileSelectorWidget()
    self.sel_set_bookmarks.pathChanged.connect(self._update_preview)
    l_set_bookmarks.addWidget(self.sel_set_bookmarks)
    l_set_bookmarks.addWidget(QLabel(tm.get("lbl_set_bookmarks_guide")))
    self.txt_set_bookmarks = QTextEdit()
    self.txt_set_bookmarks.setPlaceholderText(tm.get("ph_set_bookmarks"))
    self.txt_set_bookmarks.setMinimumHeight(90)
    l_set_bookmarks.addWidget(self.txt_set_bookmarks)
    b_set_bookmarks = QPushButton(tm.get("btn_set_bookmarks"))
    b_set_bookmarks.setObjectName("actionBtn")
    b_set_bookmarks.clicked.connect(self.action_set_bookmarks)
    l_set_bookmarks.addWidget(b_set_bookmarks)
    layout.addWidget(grp_set_bookmarks)

