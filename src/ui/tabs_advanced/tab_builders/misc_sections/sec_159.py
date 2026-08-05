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


def build_sec_159(self, layout) -> None:
    """첨부 파일 관리"""
    # 첨부 파일 관리
    grp_attach = QGroupBox(tm.get("grp_attach"))
    l_attach = QVBoxLayout(grp_attach)
    self.sel_attach = FileSelectorWidget()
    self.sel_attach.pathChanged.connect(self._update_preview)
    l_attach.addWidget(self.sel_attach)
    attach_btns = QHBoxLayout()
    b_list_attach = QPushButton(tm.get("btn_list_attach"))
    b_list_attach.clicked.connect(self.action_list_attachments)
    attach_btns.addWidget(b_list_attach)
    b_add_attach = QPushButton(tm.get("btn_add_attach"))
    b_add_attach.clicked.connect(self.action_add_attachment)
    attach_btns.addWidget(b_add_attach)
    b_extract_attach = QPushButton(tm.get("btn_extract_attach"))
    b_extract_attach.clicked.connect(self.action_extract_attachments)
    attach_btns.addWidget(b_extract_attach)
    l_attach.addLayout(attach_btns)
    layout.addWidget(grp_attach)

