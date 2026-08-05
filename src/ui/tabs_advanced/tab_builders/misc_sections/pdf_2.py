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


def build_pdf_2(self, layout) -> None:
    """PDF 복호화"""
    # PDF 복호화
    grp_decrypt = QGroupBox(tm.get("grp_decrypt"))
    l_decrypt = QVBoxLayout(grp_decrypt)
    self.sel_decrypt = FileSelectorWidget()
    self.sel_decrypt.pathChanged.connect(self._update_preview)
    l_decrypt.addWidget(self.sel_decrypt)
    decrypt_opts = QHBoxLayout()
    decrypt_opts.addWidget(QLabel(tm.get("lbl_pw")))
    self.inp_decrypt_pw = QLineEdit()
    self.inp_decrypt_pw.setEchoMode(QLineEdit.EchoMode.Password)
    self.inp_decrypt_pw.setPlaceholderText(tm.get("ph_decrypt_pw"))
    decrypt_opts.addWidget(self.inp_decrypt_pw)
    l_decrypt.addLayout(decrypt_opts)
    b_decrypt = QPushButton(tm.get("btn_decrypt"))
    b_decrypt.setToolTip(tm.get("tooltip_decrypt"))
    b_decrypt.clicked.connect(self.action_decrypt_pdf)
    l_decrypt.addWidget(b_decrypt)
    layout.addWidget(grp_decrypt)

