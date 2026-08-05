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


def build_shapes(self, layout) -> None:
    """v4.5: 도형 그리기"""
    # v4.5: 도형 그리기
    grp_shapes = QGroupBox(tm.get("grp_draw_shapes"))
    l_shapes = QVBoxLayout(grp_shapes)
    self.sel_shape = FileSelectorWidget()
    self.sel_shape.pathChanged.connect(self._update_preview)
    l_shapes.addWidget(self.sel_shape)
    shape_opts1 = QHBoxLayout()
    shape_opts1.addWidget(QLabel(tm.get("lbl_shape_type")))
    self.cmb_shape_type = QComboBox()
    shape_types = [
        (tm.get("shape_rect"), "rect"),
        (tm.get("shape_circle"), "circle"),
        (tm.get("shape_line"), "line"),
    ]
    for label, value in shape_types:
        self.cmb_shape_type.addItem(label, value)
    shape_opts1.addWidget(self.cmb_shape_type)
    shape_opts1.addWidget(QLabel(tm.get("tab_page") + ":"))
    self.spn_shape_page = QSpinBox()
    self.spn_shape_page.setRange(1, 9999)
    self.spn_shape_page.setValue(1)
    shape_opts1.addWidget(self.spn_shape_page)
    shape_opts1.addStretch()
    l_shapes.addLayout(shape_opts1)
    shape_opts2 = QHBoxLayout()
    shape_opts2.addWidget(QLabel(tm.get("lbl_shape_x")))
    self.spn_shape_x = QSpinBox()
    self.spn_shape_x.setRange(0, 9999)
    self.spn_shape_x.setValue(100)
    shape_opts2.addWidget(self.spn_shape_x)
    shape_opts2.addWidget(QLabel(tm.get("lbl_shape_y")))
    self.spn_shape_y = QSpinBox()
    self.spn_shape_y.setRange(0, 9999)
    self.spn_shape_y.setValue(700)
    shape_opts2.addWidget(self.spn_shape_y)
    shape_opts2.addWidget(QLabel(tm.get("lbl_shape_width")))
    self.spn_shape_w = QSpinBox()
    self.spn_shape_w.setRange(10, 999)
    self.spn_shape_w.setValue(100)
    shape_opts2.addWidget(self.spn_shape_w)
    shape_opts2.addWidget(QLabel(tm.get("lbl_shape_height")))
    self.spn_shape_h = QSpinBox()
    self.spn_shape_h.setRange(10, 999)
    self.spn_shape_h.setValue(50)
    shape_opts2.addWidget(self.spn_shape_h)
    shape_opts2.addStretch()
    l_shapes.addLayout(shape_opts2)
    shape_opts3 = QHBoxLayout()
    shape_opts3.addWidget(QLabel(tm.get("lbl_line_color")))
    self.cmb_shape_line_color = QComboBox()
    shape_line_colors = [
        (tm.get("color_blue"), (0, 0, 1)),
        (tm.get("color_red"), (1, 0, 0)),
        (tm.get("color_black"), (0, 0, 0)),
    ]
    for label, value in shape_line_colors:
        self.cmb_shape_line_color.addItem(label, value)
    shape_opts3.addWidget(self.cmb_shape_line_color)
    shape_opts3.addWidget(QLabel(tm.get("lbl_fill_color")))
    self.cmb_shape_fill_color = QComboBox()
    shape_fill_colors = [
        ("None", None),
        (tm.get("color_light_yellow"), (1, 1, 0.8)),
        (tm.get("color_light_blue"), (0.9, 0.95, 1)),
    ]
    for label, value in shape_fill_colors:
        self.cmb_shape_fill_color.addItem(label, value)
    shape_opts3.addWidget(self.cmb_shape_fill_color)
    shape_opts3.addStretch()
    l_shapes.addLayout(shape_opts3)
    b_shape = QPushButton(tm.get("btn_draw_shape"))
    b_shape.setObjectName("actionBtn")
    b_shape.clicked.connect(self.action_draw_shape)
    l_shapes.addWidget(b_shape)
    layout.addWidget(grp_shapes)

