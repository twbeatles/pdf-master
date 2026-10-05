from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from ....fluent_widgets import PrimaryButton, QComboBox, QLineEdit, QSpinBox

from .....core.i18n import tm
from ....widgets import FileSelectorWidget
from ....form_rows import pair_grid


def build_sec_100(self, layout) -> None:
    """프리핸드 서명"""
    # 프리핸드 서명
    grp_freehand = QGroupBox(tm.get("grp_freehand_sig"))
    l_freehand = QVBoxLayout(grp_freehand)
    self.sel_freehand_pdf = FileSelectorWidget()
    self.sel_freehand_pdf.pathChanged.connect(self._update_preview)
    l_freehand.addWidget(self.sel_freehand_pdf)
    self.spn_freehand_page = QSpinBox()
    self.spn_freehand_page.setRange(0, 9999)
    self.spn_freehand_page.setValue(0)
    self.spn_freehand_page.setSpecialValueText(tm.get("label_last_page"))
    self.spn_freehand_width = QSpinBox()
    self.spn_freehand_width.setRange(1, 20)
    self.spn_freehand_width.setValue(2)
    self.cmb_freehand_color = QComboBox()
    freehand_colors = [
        (tm.get("color_black"), (0, 0, 0)),
        (tm.get("color_blue"), (0, 0, 1)),
        (tm.get("color_red"), (1, 0, 0)),
    ]
    for label, value in freehand_colors:
        self.cmb_freehand_color.addItem(label, userData=value)
    l_freehand.addLayout(
        pair_grid(
            [
                (tm.get("lbl_page"), self.spn_freehand_page),
                (tm.get("lbl_line_width"), self.spn_freehand_width),
                (tm.get("lbl_color"), self.cmb_freehand_color),
            ]
        )
    )
    freehand_guide = QLabel(tm.get("lbl_freehand_guide"))
    freehand_guide.setObjectName("desc")
    freehand_guide.setWordWrap(True)
    l_freehand.addWidget(freehand_guide)
    self.txt_freehand_strokes = QLineEdit()
    self.txt_freehand_strokes.setPlaceholderText(tm.get("ph_freehand_strokes"))
    l_freehand.addWidget(self.txt_freehand_strokes)
    b_freehand = PrimaryButton(tm.get("btn_add_freehand_sig"))
    b_freehand.setObjectName("actionBtn")
    b_freehand.clicked.connect(self.action_add_freehand_signature)
    l_freehand.addWidget(b_freehand)
    layout.addWidget(grp_freehand)

