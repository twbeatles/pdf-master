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

from ....core.i18n import tm
from ...widgets import FileSelectorWidget


def _create_edit_subtab(self):
    """편집 서브탭: 분할, 페이지 번호, 스탬프, 크롭, 빈 페이지, 크기 변경, 복제, 역순"""
    widget = QWidget()
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setSpacing(12)

    # PDF 분할
    grp_split = QGroupBox(tm.get("grp_split_pdf"))
    l_split = QVBoxLayout(grp_split)
    self.sel_split_adv = FileSelectorWidget()
    self.sel_split_adv.pathChanged.connect(self._update_preview)
    l_split.addWidget(self.sel_split_adv)
    opt_split = QHBoxLayout()
    opt_split.addWidget(QLabel(tm.get("lbl_split_mode")))
    self.cmb_split_mode = QComboBox()
    split_modes = [
        (tm.get("mode_split_page"), "each"),
        (tm.get("mode_split_range"), "range"),
    ]
    for label, value in split_modes:
        self.cmb_split_mode.addItem(label, value)
    opt_split.addWidget(self.cmb_split_mode)
    self.inp_split_range = QLineEdit()
    self.inp_split_range.setPlaceholderText(tm.get("ph_split_range"))
    opt_split.addWidget(self.inp_split_range)
    l_split.addLayout(opt_split)
    b_split = QPushButton(tm.get("btn_split_pdf"))
    b_split.setToolTip(tm.get("tooltip_split_pdf"))
    b_split.clicked.connect(self.action_split_adv)
    l_split.addWidget(b_split)
    layout.addWidget(grp_split)

    # 스탬프
    grp_stamp = QGroupBox(tm.get("grp_stamp"))
    l_stamp = QVBoxLayout(grp_stamp)
    self.sel_stamp = FileSelectorWidget()
    self.sel_stamp.pathChanged.connect(self._update_preview)
    l_stamp.addWidget(self.sel_stamp)
    opt_stamp = QHBoxLayout()
    opt_stamp.addWidget(QLabel(tm.get("lbl_stamp_text")))
    self.cmb_stamp = QComboBox()
    self.cmb_stamp.addItems([tm.get("stamp_confidential"), tm.get("stamp_approved"), tm.get("stamp_draft"), tm.get("stamp_final"), tm.get("stamp_no_copy")])
    self.cmb_stamp.setEditable(True)
    opt_stamp.addWidget(self.cmb_stamp)
    opt_stamp.addWidget(QLabel(tm.get("lbl_stamp_pos")))
    self.cmb_stamp_pos = QComboBox()
    stamp_positions = [
        (tm.get("pos_top_right"), "top-right"),
        (tm.get("pos_top_left"), "top-left"),
        (tm.get("pos_bottom_right"), "bottom-right"),
        (tm.get("pos_bottom_left"), "bottom-left"),
    ]
    for label, value in stamp_positions:
        self.cmb_stamp_pos.addItem(label, value)
    opt_stamp.addWidget(self.cmb_stamp_pos)
    l_stamp.addLayout(opt_stamp)
    b_stamp = QPushButton(tm.get("btn_add_stamp"))
    b_stamp.clicked.connect(self.action_stamp)
    l_stamp.addWidget(b_stamp)
    layout.addWidget(grp_stamp)

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
    b_crop = QPushButton(tm.get("btn_crop"))
    b_crop.clicked.connect(self.action_crop)
    l_crop.addWidget(b_crop)
    layout.addWidget(grp_crop)

    # 빈 페이지 삽입
    grp_blank = QGroupBox(tm.get("grp_blank_page"))
    l_blank = QVBoxLayout(grp_blank)
    self.sel_blank = FileSelectorWidget()
    self.sel_blank.pathChanged.connect(self._update_preview)
    l_blank.addWidget(self.sel_blank)
    opt_blank = QHBoxLayout()
    opt_blank.addWidget(QLabel(tm.get("lbl_blank_pos")))
    self.spn_blank_pos = QSpinBox()
    self.spn_blank_pos.setRange(1, 999)
    self.spn_blank_pos.setValue(1)
    opt_blank.addWidget(self.spn_blank_pos)
    opt_blank.addStretch()
    l_blank.addLayout(opt_blank)
    b_blank = QPushButton(tm.get("btn_insert_blank"))
    b_blank.clicked.connect(self.action_blank_page)
    l_blank.addWidget(b_blank)
    layout.addWidget(grp_blank)

    # 페이지 크기 변경
    grp_resize = QGroupBox(tm.get("grp_resize_page"))
    l_resize = QVBoxLayout(grp_resize)
    self.sel_resize = FileSelectorWidget()
    self.sel_resize.pathChanged.connect(self._update_preview)
    l_resize.addWidget(self.sel_resize)
    resize_opts = QHBoxLayout()
    resize_opts.addWidget(QLabel(tm.get("lbl_size")))
    self.cmb_resize = QComboBox()
    for size in ["A4", "A3", "Letter", "Legal"]:
        self.cmb_resize.addItem(size, size)
    resize_opts.addWidget(self.cmb_resize)
    resize_opts.addStretch()
    l_resize.addLayout(resize_opts)
    b_resize = QPushButton(tm.get("btn_resize"))
    b_resize.clicked.connect(self.action_resize_pages)
    l_resize.addWidget(b_resize)
    layout.addWidget(grp_resize)

    # 페이지 복제
    grp_dup = QGroupBox(tm.get("grp_duplicate"))
    l_dup = QVBoxLayout(grp_dup)
    self.sel_dup = FileSelectorWidget()
    self.sel_dup.pathChanged.connect(self._update_preview)
    l_dup.addWidget(self.sel_dup)
    dup_opts = QHBoxLayout()
    dup_opts.addWidget(QLabel(tm.get("tab_page") + ":")) # Reuse tab_page key for "Page"
    self.spn_dup_page = QSpinBox()
    self.spn_dup_page.setRange(1, 9999)
    dup_opts.addWidget(self.spn_dup_page)
    dup_opts.addWidget(QLabel(tm.get("lbl_dup_count")))
    self.spn_dup_count = QSpinBox()
    self.spn_dup_count.setRange(1, 100)
    self.spn_dup_count.setValue(1)
    dup_opts.addWidget(self.spn_dup_count)
    dup_opts.addStretch()
    l_dup.addLayout(dup_opts)
    b_dup = QPushButton(tm.get("btn_duplicate"))
    b_dup.clicked.connect(self.action_duplicate_page)
    l_dup.addWidget(b_dup)
    layout.addWidget(grp_dup)

    # 역순 정렬
    grp_rev = QGroupBox(tm.get("grp_reverse_page"))
    l_rev = QVBoxLayout(grp_rev)
    self.sel_rev = FileSelectorWidget()
    self.sel_rev.pathChanged.connect(self._update_preview)
    l_rev.addWidget(self.sel_rev)
    b_rev = QPushButton(tm.get("btn_reverse_page"))
    b_rev.setToolTip(tm.get("tooltip_reverse_pages"))
    b_rev.clicked.connect(self.action_reverse_pages)
    l_rev.addWidget(b_rev)
    layout.addWidget(grp_rev)

    # v4.5: 텍스트 상자 삽입
    grp_textbox = QGroupBox(tm.get("grp_insert_textbox"))
    l_textbox = QVBoxLayout(grp_textbox)
    self.sel_textbox = FileSelectorWidget()
    self.sel_textbox.pathChanged.connect(self._update_preview)
    l_textbox.addWidget(self.sel_textbox)
    tb_opts1 = QHBoxLayout()
    tb_opts1.addWidget(QLabel(tm.get("tab_page") + ":"))
    self.spn_tb_page = QSpinBox()
    self.spn_tb_page.setRange(1, 9999)
    self.spn_tb_page.setValue(1)
    tb_opts1.addWidget(self.spn_tb_page)
    tb_opts1.addWidget(QLabel(tm.get("lbl_textbox_x")))
    self.spn_tb_x = QSpinBox()
    self.spn_tb_x.setRange(0, 9999)
    self.spn_tb_x.setValue(100)
    tb_opts1.addWidget(self.spn_tb_x)
    tb_opts1.addWidget(QLabel(tm.get("lbl_textbox_y")))
    self.spn_tb_y = QSpinBox()
    self.spn_tb_y.setRange(0, 9999)
    self.spn_tb_y.setValue(700)
    tb_opts1.addWidget(self.spn_tb_y)
    tb_opts1.addStretch()
    l_textbox.addLayout(tb_opts1)
    tb_opts2 = QHBoxLayout()
    tb_opts2.addWidget(QLabel(tm.get("lbl_textbox_fontsize")))
    self.spn_tb_fontsize = QSpinBox()
    self.spn_tb_fontsize.setRange(6, 72)
    self.spn_tb_fontsize.setValue(12)
    tb_opts2.addWidget(self.spn_tb_fontsize)
    tb_opts2.addWidget(QLabel(tm.get("lbl_textbox_color")))
    self.cmb_tb_color = QComboBox()
    tb_colors = [
        (tm.get("color_black"), (0, 0, 0)),
        (tm.get("color_blue"), (0, 0, 1)),
        (tm.get("color_red"), (1, 0, 0)),
    ]
    for label, value in tb_colors:
        self.cmb_tb_color.addItem(label, value)
    tb_opts2.addWidget(self.cmb_tb_color)
    tb_opts2.addStretch()
    l_textbox.addLayout(tb_opts2)
    l_textbox.addWidget(QLabel(tm.get("lbl_textbox_content")))
    self.txt_textbox_content = QLineEdit()
    self.txt_textbox_content.setPlaceholderText(tm.get("ph_textbox_content"))
    l_textbox.addWidget(self.txt_textbox_content)
    b_textbox = QPushButton(tm.get("btn_insert_textbox"))
    b_textbox.setObjectName("actionBtn")
    b_textbox.clicked.connect(self.action_insert_textbox)
    l_textbox.addWidget(b_textbox)
    layout.addWidget(grp_textbox)

    layout.addStretch()
    scroll.setWidget(content)
    main_layout = QVBoxLayout(widget)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.addWidget(scroll)
    return widget
