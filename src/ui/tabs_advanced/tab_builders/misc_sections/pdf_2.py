from __future__ import annotations

from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from .....core.i18n import tm
from ....fluent_widgets import PrimaryButton, PasswordLineEdit, PushButton
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
    self.inp_decrypt_pw = PasswordLineEdit()
    # (PasswordLineEdit presets Password echo + view button)
    self.inp_decrypt_pw.setPlaceholderText(tm.get("ph_decrypt_pw"))
    decrypt_opts.addWidget(self.inp_decrypt_pw)
    l_decrypt.addLayout(decrypt_opts)
    b_decrypt = PrimaryButton(tm.get("btn_decrypt"))
    b_decrypt.setObjectName("actionBtn")
    b_decrypt.setToolTip(tm.get("tooltip_decrypt"))
    b_decrypt.clicked.connect(self.action_decrypt_pdf)
    l_decrypt.addWidget(b_decrypt)
    layout.addWidget(grp_decrypt)

