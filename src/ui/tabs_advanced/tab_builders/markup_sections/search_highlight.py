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


def build_search_highlight(self, layout) -> None:
    """텍스트 검색 & 하이라이트"""
    # 텍스트 검색 & 하이라이트
    grp_search = QGroupBox(tm.get("grp_search_hi"))
    l_search = QVBoxLayout(grp_search)
    self.sel_search = FileSelectorWidget()
    self.sel_search.pathChanged.connect(self._update_preview)
    l_search.addWidget(self.sel_search)
    search_opts = QHBoxLayout()
    search_opts.addWidget(QLabel(tm.get("lbl_keyword")))
    self.inp_search = QLineEdit()
    self.inp_search.setPlaceholderText(tm.get("ph_search"))
    search_opts.addWidget(self.inp_search)
    l_search.addLayout(search_opts)
    search_btns = QHBoxLayout()
    b_search = QPushButton(tm.get("btn_search_text"))
    b_search.setToolTip(tm.get("tooltip_search_text"))
    b_search.clicked.connect(self.action_search_text)
    search_btns.addWidget(b_search)
    b_highlight = QPushButton(tm.get("btn_highlight"))
    b_highlight.setToolTip(tm.get("tooltip_highlight"))
    b_highlight.clicked.connect(self.action_highlight_text)
    search_btns.addWidget(b_highlight)
    l_search.addLayout(search_btns)
    layout.addWidget(grp_search)

