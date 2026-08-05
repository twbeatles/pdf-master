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


def build_sec_100(self, layout) -> None:
    """프리핸드 서명"""
    # 프리핸드 서명
    grp_freehand = QGroupBox(tm.get("grp_freehand_sig"))
    l_freehand = QVBoxLayout(grp_freehand)
    self.sel_freehand_pdf = FileSelectorWidget()
    self.sel_freehand_pdf.pathChanged.connect(self._update_preview)
    l_freehand.addWidget(self.sel_freehand_pdf)
    freehand_opts = QHBoxLayout()
    freehand_opts.addWidget(QLabel(tm.get("tab_page") + ":"))
    self.spn_freehand_page = QSpinBox()
    self.spn_freehand_page.setRange(0, 9999)
    self.spn_freehand_page.setValue(0)
    self.spn_freehand_page.setSpecialValueText(tm.get("label_last_page"))
    freehand_opts.addWidget(self.spn_freehand_page)
    freehand_opts.addWidget(QLabel(tm.get("lbl_line_width")))
    self.spn_freehand_width = QSpinBox()
    self.spn_freehand_width.setRange(1, 20)
    self.spn_freehand_width.setValue(2)
    freehand_opts.addWidget(self.spn_freehand_width)
    freehand_opts.addWidget(QLabel(tm.get("lbl_color")))
    self.cmb_freehand_color = QComboBox()
    freehand_colors = [
        (tm.get("color_black"), (0, 0, 0)),
        (tm.get("color_blue"), (0, 0, 1)),
        (tm.get("color_red"), (1, 0, 0)),
    ]
    for label, value in freehand_colors:
        self.cmb_freehand_color.addItem(label, value)
    freehand_opts.addWidget(self.cmb_freehand_color)
    freehand_opts.addStretch()
    l_freehand.addLayout(freehand_opts)
    l_freehand.addWidget(QLabel(tm.get("lbl_freehand_guide")))
    self.txt_freehand_strokes = QLineEdit()
    self.txt_freehand_strokes.setPlaceholderText(tm.get("ph_freehand_strokes"))
    l_freehand.addWidget(self.txt_freehand_strokes)
    b_freehand = QPushButton(tm.get("btn_add_freehand_sig"))
    b_freehand.setObjectName("actionBtn")
    b_freehand.clicked.connect(self.action_add_freehand_signature)
    l_freehand.addWidget(b_freehand)
    layout.addWidget(grp_freehand)

