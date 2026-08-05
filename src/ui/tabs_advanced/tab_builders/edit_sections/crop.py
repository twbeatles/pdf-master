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


def build_crop(self, layout) -> None:
    """여백 자르기"""
    # 여백 자르기
    grp_crop = QGroupBox(tm.get("grp_crop"))
    l_crop = QVBoxLayout(grp_crop)
    self.sel_crop = FileSelectorWidget()
    self.sel_crop.pathChanged.connect(self._update_preview)
    l_crop.addWidget(self.sel_crop)
    opt_crop = QHBoxLayout()
    labels = [tm.get("lbl_left"), tm.get("lbl_top"), tm.get("lbl_right"), tm.get("lbl_bottom")]
    attr_sides = ["left", "top", "right", "bottom"]
    for i, side_name in enumerate(attr_sides):
        opt_crop.addWidget(QLabel(labels[i]))
        spn = QSpinBox()
        spn.setRange(0, 200)
        spn.setValue(20)
        spn.setToolTip(tm.get("tooltip_crop"))
        setattr(self, f"spn_crop_{side_name}", spn)
        opt_crop.addWidget(spn)
    l_crop.addLayout(opt_crop)
    self.chk_crop_content = QCheckBox(tm.get("chk_crop_content"))
    self.chk_crop_content.setChecked(False)
    l_crop.addWidget(self.chk_crop_content)
    b_crop = QPushButton(tm.get("btn_crop"))
    b_crop.clicked.connect(self.action_crop)
    l_crop.addWidget(b_crop)
    layout.addWidget(grp_crop)

