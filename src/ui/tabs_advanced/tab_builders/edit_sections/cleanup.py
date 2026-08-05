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


def build_cleanup(self, layout) -> None:
    """페이지 정리 (빈/중복 제거, 자동 목차, 위생, N-up)"""
    # 페이지 정리 (빈/중복 제거, 자동 목차, 위생, N-up)
    grp_cleanup = QGroupBox(tm.get("grp_page_cleanup"))
    l_cleanup = QVBoxLayout(grp_cleanup)
    self.sel_cleanup = FileSelectorWidget()
    self.sel_cleanup.pathChanged.connect(self._update_preview)
    l_cleanup.addWidget(self.sel_cleanup)
    cleanup_btns = QHBoxLayout()
    b_rm_blank = QPushButton(tm.get("btn_remove_blank_pages"))
    b_rm_blank.clicked.connect(self.action_remove_blank_pages)
    cleanup_btns.addWidget(b_rm_blank)
    b_dedupe = QPushButton(tm.get("btn_dedupe_pages"))
    b_dedupe.clicked.connect(self.action_dedupe_pages)
    cleanup_btns.addWidget(b_dedupe)
    l_cleanup.addLayout(cleanup_btns)
    cleanup_btns2 = QHBoxLayout()
    b_auto_bm = QPushButton(tm.get("btn_auto_bookmarks"))
    b_auto_bm.clicked.connect(self.action_auto_bookmarks)
    cleanup_btns2.addWidget(b_auto_bm)
    b_sanitize = QPushButton(tm.get("btn_sanitize_pdf"))
    b_sanitize.clicked.connect(self.action_sanitize_pdf)
    cleanup_btns2.addWidget(b_sanitize)
    l_cleanup.addLayout(cleanup_btns2)
    nup_row = QHBoxLayout()
    nup_row.addWidget(QLabel(tm.get("lbl_nup")))
    self.cmb_nup = QComboBox()
    self.cmb_nup.addItem(tm.get("nup_2"), 2)
    self.cmb_nup.addItem(tm.get("nup_4"), 4)
    nup_row.addWidget(self.cmb_nup)
    b_nup = QPushButton(tm.get("btn_impose_nup"))
    b_nup.clicked.connect(self.action_impose_nup)
    nup_row.addWidget(b_nup)
    nup_row.addStretch()
    l_cleanup.addLayout(nup_row)
    layout.addWidget(grp_cleanup)

