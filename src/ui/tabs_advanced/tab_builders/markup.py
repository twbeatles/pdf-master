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


def _create_markup_subtab(self):
    """마크업 서브탭: 검색, 하이라이트, 주석, 텍스트 마크업, 배경색, 교정"""
    widget = QWidget()
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setSpacing(12)

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

    # 주석 관리
    grp_annot = QGroupBox(tm.get("grp_annot"))
    l_annot = QVBoxLayout(grp_annot)
    self.sel_annot = FileSelectorWidget()
    self.sel_annot.pathChanged.connect(self._update_preview)
    l_annot.addWidget(self.sel_annot)
    annot_btns = QHBoxLayout()
    b_list_annot = QPushButton(tm.get("btn_list_annot"))
    b_list_annot.setToolTip(tm.get("tooltip_list_annot"))
    b_list_annot.clicked.connect(self.action_list_annotations)
    annot_btns.addWidget(b_list_annot)
    b_remove_annot = QPushButton(tm.get("btn_remove_annot"))
    b_remove_annot.setObjectName("dangerBtn")
    b_remove_annot.setToolTip(tm.get("tooltip_remove_annot"))
    b_remove_annot.clicked.connect(self.action_remove_annotations)
    annot_btns.addWidget(b_remove_annot)
    l_annot.addLayout(annot_btns)
    layout.addWidget(grp_annot)

    # 텍스트 마크업
    grp_markup = QGroupBox(tm.get("grp_markup"))
    l_markup = QVBoxLayout(grp_markup)
    self.sel_markup = FileSelectorWidget()
    self.sel_markup.pathChanged.connect(self._update_preview)
    l_markup.addWidget(self.sel_markup)
    markup_opts = QHBoxLayout()
    markup_opts.addWidget(QLabel(tm.get("lbl_keyword"))) # Reuse keyword label
    self.inp_markup = QLineEdit()
    self.inp_markup.setPlaceholderText(tm.get("ph_markup"))
    markup_opts.addWidget(self.inp_markup)
    markup_opts.addWidget(QLabel(tm.get("lbl_markup_type")))
    self.cmb_markup = QComboBox()
    markup_types = [
        (tm.get("type_underline"), "underline"),
        (tm.get("type_strikeout"), "strikeout"),
        (tm.get("type_squiggly"), "squiggly"),
    ]
    for label, value in markup_types:
        self.cmb_markup.addItem(label, value)
    markup_opts.addWidget(self.cmb_markup)
    l_markup.addLayout(markup_opts)
    b_markup = QPushButton(tm.get("btn_add_markup"))
    b_markup.clicked.connect(self.action_add_text_markup)
    l_markup.addWidget(b_markup)
    layout.addWidget(grp_markup)

    # 배경색 추가
    grp_bg = QGroupBox(tm.get("grp_bg_color"))
    l_bg = QVBoxLayout(grp_bg)
    self.sel_bg = FileSelectorWidget()
    self.sel_bg.pathChanged.connect(self._update_preview)
    l_bg.addWidget(self.sel_bg)
    bg_opts = QHBoxLayout()
    bg_opts.addWidget(QLabel(tm.get("lbl_color")))
    self.cmb_bg_color = QComboBox()
    bg_colors = [
        (tm.get("color_cream"), [1, 1, 0.9]),
        (tm.get("color_light_yellow"), [1, 1, 0.8]),
        (tm.get("color_light_blue"), [0.9, 0.95, 1]),
        (tm.get("color_light_gray"), [0.95, 0.95, 0.95]),
        (tm.get("color_white"), [1, 1, 1]),
    ]
    for label, value in bg_colors:
        self.cmb_bg_color.addItem(label, value)
    bg_opts.addWidget(self.cmb_bg_color)
    bg_opts.addStretch()
    l_bg.addLayout(bg_opts)
    b_bg = QPushButton(tm.get("btn_add_bg"))
    b_bg.clicked.connect(self.action_add_background)
    l_bg.addWidget(b_bg)
    layout.addWidget(grp_bg)

    # 텍스트 교정 (Redact)
    grp_redact = QGroupBox(tm.get("grp_redact"))
    l_redact = QVBoxLayout(grp_redact)
    self.sel_redact = FileSelectorWidget()
    self.sel_redact.pathChanged.connect(self._update_preview)
    l_redact.addWidget(self.sel_redact)
    redact_opts = QHBoxLayout()
    redact_opts.addWidget(QLabel(tm.get("lbl_redact_text")))
    self.inp_redact = QLineEdit()
    self.inp_redact.setPlaceholderText(tm.get("ph_redact"))
    redact_opts.addWidget(self.inp_redact)
    l_redact.addLayout(redact_opts)
    b_redact = QPushButton(tm.get("btn_redact"))
    b_redact.setObjectName("dangerBtn")
    b_redact.setToolTip(tm.get("tooltip_redact"))
    b_redact.clicked.connect(self.action_redact_text)
    l_redact.addWidget(b_redact)
    area_row = QHBoxLayout()
    area_row.addWidget(QLabel(tm.get("lbl_redact_page")))
    self.spn_redact_page = QSpinBox()
    self.spn_redact_page.setRange(1, 9999)
    self.spn_redact_page.setValue(1)
    area_row.addWidget(self.spn_redact_page)
    area_row.addWidget(QLabel(tm.get("lbl_redact_rect")))
    self.inp_redact_rect = QLineEdit()
    self.inp_redact_rect.setPlaceholderText(tm.get("ph_redact_rect"))
    area_row.addWidget(self.inp_redact_rect)
    l_redact.addLayout(area_row)
    b_redact_area = QPushButton(tm.get("btn_redact_area"))
    b_redact_area.setObjectName("dangerBtn")
    b_redact_area.clicked.connect(self.action_redact_area)
    l_redact.addWidget(b_redact_area)
    layout.addWidget(grp_redact)

    # v3.2: 스티키 노트 주석
    grp_sticky = QGroupBox(tm.get("grp_sticky"))
    l_sticky = QVBoxLayout(grp_sticky)
    self.sel_sticky = FileSelectorWidget()
    self.sel_sticky.pathChanged.connect(self._update_preview)
    l_sticky.addWidget(self.sel_sticky)
    sticky_opts1 = QHBoxLayout()
    sticky_opts1.addWidget(QLabel(tm.get("lbl_pos_x")))
    self.spn_sticky_x = QSpinBox()
    self.spn_sticky_x.setRange(0, 999)
    self.spn_sticky_x.setValue(100)
    sticky_opts1.addWidget(self.spn_sticky_x)
    sticky_opts1.addWidget(QLabel(tm.get("lbl_pos_y")))
    self.spn_sticky_y = QSpinBox()
    self.spn_sticky_y.setRange(0, 999)
    self.spn_sticky_y.setValue(100)
    sticky_opts1.addWidget(self.spn_sticky_y)
    sticky_opts1.addWidget(QLabel(tm.get("tab_page") + ":"))
    self.spn_sticky_page = QSpinBox()
    self.spn_sticky_page.setRange(1, 9999)
    self.spn_sticky_page.setValue(1)
    sticky_opts1.addWidget(self.spn_sticky_page)
    sticky_opts1.addStretch()
    l_sticky.addLayout(sticky_opts1)
    sticky_opts2 = QHBoxLayout()
    sticky_opts2.addWidget(QLabel(tm.get("lbl_icon")))
    self.cmb_sticky_icon = QComboBox()
    self.cmb_sticky_icon.addItems(["Note", "Comment", "Key", "Help", "Insert", "Paragraph"])
    sticky_opts2.addWidget(self.cmb_sticky_icon)
    sticky_opts2.addStretch()
    l_sticky.addLayout(sticky_opts2)
    l_sticky.addWidget(QLabel(tm.get("lbl_content")))
    self.txt_sticky_content = QLineEdit()
    self.txt_sticky_content.setPlaceholderText(tm.get("ph_sticky"))
    l_sticky.addWidget(self.txt_sticky_content)
    b_sticky = QPushButton(tm.get("btn_add_sticky"))
    b_sticky.clicked.connect(self.action_add_sticky_note)
    l_sticky.addWidget(b_sticky)
    layout.addWidget(grp_sticky)

    # v3.2: 프리핸드 드로잉
    grp_ink = QGroupBox(tm.get("grp_ink"))
    l_ink = QVBoxLayout(grp_ink)
    self.sel_ink = FileSelectorWidget()
    self.sel_ink.pathChanged.connect(self._update_preview)
    l_ink.addWidget(self.sel_ink)
    ink_opts1 = QHBoxLayout()
    ink_opts1.addWidget(QLabel(tm.get("tab_page") + ":"))
    self.spn_ink_page = QSpinBox()
    self.spn_ink_page.setRange(1, 9999)
    self.spn_ink_page.setValue(1)
    ink_opts1.addWidget(self.spn_ink_page)
    ink_opts1.addWidget(QLabel(tm.get("lbl_line_width")))
    self.spn_ink_width = QSpinBox()
    self.spn_ink_width.setRange(1, 10)
    self.spn_ink_width.setValue(2)
    ink_opts1.addWidget(self.spn_ink_width)
    ink_opts1.addWidget(QLabel(tm.get("lbl_color")))
    self.cmb_ink_color = QComboBox()
    ink_colors = [
        (tm.get("color_blue_ink"), (0, 0, 1)),
        (tm.get("color_red_ink"), (1, 0, 0)),
        (tm.get("color_black_ink"), (0, 0, 0)),
        (tm.get("color_green_ink"), (0, 0.5, 0)),
    ]
    for label, value in ink_colors:
        self.cmb_ink_color.addItem(label, value)
    ink_opts1.addWidget(self.cmb_ink_color)
    ink_opts1.addStretch()
    l_ink.addLayout(ink_opts1)
    ink_guide = QLabel(tm.get("lbl_ink_guide"))
    ink_guide.setObjectName("desc")
    l_ink.addWidget(ink_guide)
    self.txt_ink_points = QLineEdit()
    self.txt_ink_points.setPlaceholderText(tm.get("ph_ink"))
    l_ink.addWidget(self.txt_ink_points)
    b_ink = QPushButton(tm.get("btn_add_ink"))
    b_ink.clicked.connect(self.action_add_ink_annotation)
    l_ink.addWidget(b_ink)
    layout.addWidget(grp_ink)

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

    # v4.5: 하이퍼링크 추가
    grp_link = QGroupBox(tm.get("grp_add_link"))
    l_link = QVBoxLayout(grp_link)
    self.sel_link = FileSelectorWidget()
    self.sel_link.pathChanged.connect(self._update_preview)
    l_link.addWidget(self.sel_link)
    link_opts1 = QHBoxLayout()
    link_opts1.addWidget(QLabel(tm.get("lbl_link_type")))
    self.cmb_link_type = QComboBox()
    link_types = [
        (tm.get("link_url"), "url"),
        (tm.get("link_page"), "page"),
    ]
    for label, value in link_types:
        self.cmb_link_type.addItem(label, value)
    link_opts1.addWidget(self.cmb_link_type)
    link_opts1.addWidget(QLabel(tm.get("tab_page") + ":"))
    self.spn_link_page = QSpinBox()
    self.spn_link_page.setRange(1, 9999)
    self.spn_link_page.setValue(1)
    link_opts1.addWidget(self.spn_link_page)
    link_opts1.addStretch()
    l_link.addLayout(link_opts1)
    link_opts2 = QHBoxLayout()
    link_opts2.addWidget(QLabel(tm.get("lbl_link_url")))
    self.txt_link_url = QLineEdit()
    self.txt_link_url.setPlaceholderText(tm.get("ph_link_url"))
    link_opts2.addWidget(self.txt_link_url)
    l_link.addLayout(link_opts2)
    link_opts3 = QHBoxLayout()
    link_opts3.addWidget(QLabel(tm.get("lbl_target_page")))
    self.spn_link_target = QSpinBox()
    self.spn_link_target.setRange(1, 9999)
    self.spn_link_target.setValue(1)
    link_opts3.addWidget(self.spn_link_target)
    link_opts3.addWidget(QLabel(tm.get("lbl_link_area")))
    self.txt_link_area = QLineEdit()
    self.txt_link_area.setPlaceholderText(tm.get("ph_link_area"))
    link_opts3.addWidget(self.txt_link_area)
    link_opts3.addStretch()
    l_link.addLayout(link_opts3)
    b_link = QPushButton(tm.get("btn_add_link"))
    b_link.setObjectName("actionBtn")
    b_link.clicked.connect(self.action_add_hyperlink)
    l_link.addWidget(b_link)
    layout.addWidget(grp_link)

    layout.addStretch()
    scroll.setWidget(content)
    main_layout = QVBoxLayout(widget)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.addWidget(scroll)
    return widget
