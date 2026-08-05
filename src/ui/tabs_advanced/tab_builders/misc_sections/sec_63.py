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


def build_sec_63(self, layout) -> None:
    """전자 서명"""
    # 전자 서명
    grp_sig = QGroupBox(tm.get("grp_sig"))
    l_sig = QVBoxLayout(grp_sig)
    l_sig.addWidget(QLabel(tm.get("lbl_target_pdf")))
    self.sel_sig_pdf = FileSelectorWidget()
    self.sel_sig_pdf.pathChanged.connect(self._update_preview)
    l_sig.addWidget(self.sel_sig_pdf)
    l_sig.addWidget(QLabel(tm.get("lbl_sig_img")))
    self.sel_sig_img = FileSelectorWidget()
    self.sel_sig_img.drop_zone.accept_extensions = ['.png', '.jpg', '.jpeg']
    l_sig.addWidget(self.sel_sig_img)
    sig_opts = QHBoxLayout()
    sig_opts.addWidget(QLabel(tm.get("lbl_position")))
    self.cmb_sig_pos = QComboBox()
    sig_positions = [
        (tm.get("pos_bottom_right"), "bottom_right"),
        (tm.get("pos_bottom_left"), "bottom_left"),
        (tm.get("pos_top_right"), "top_right"),
        (tm.get("pos_top_left"), "top_left"),
    ]
    for label, value in sig_positions:
        self.cmb_sig_pos.addItem(label, value)
    sig_opts.addWidget(self.cmb_sig_pos)
    sig_opts.addWidget(QLabel(tm.get("tab_page") + ":"))
    self.spn_sig_page = QSpinBox()
    self.spn_sig_page.setRange(0, 9999)
    self.spn_sig_page.setValue(0)
    self.spn_sig_page.setSpecialValueText(tm.get("label_last_page"))
    self.spn_sig_page.setToolTip(tm.get("tooltip_sig_pos"))
    sig_opts.addWidget(self.spn_sig_page)
    sig_opts.addStretch()
    l_sig.addLayout(sig_opts)
    b_sig = QPushButton(tm.get("btn_insert_sig"))
    b_sig.clicked.connect(self.action_insert_signature)
    l_sig.addWidget(b_sig)
    layout.addWidget(grp_sig)

