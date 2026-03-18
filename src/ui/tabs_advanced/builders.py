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

from ...core.i18n import tm
from ..widgets import FileSelectorWidget


def setup_advanced_tab(self):
    """고급 기능 탭 - 4개 서브탭으로 구성"""
    tab = QWidget()
    layout = QVBoxLayout(tab)
    layout.setContentsMargins(5, 5, 5, 5)

    # 서브 탭 위젯
    sub_tabs = QTabWidget()
    sub_tabs.setDocumentMode(True)

    # 1. 편집 서브탭
    sub_tabs.addTab(self._create_edit_subtab(), f"✏️ {tm.get('subtab_edit')}")
    # 2. 추출 서브탭
    sub_tabs.addTab(self._create_extract_subtab(), f"📊 {tm.get('subtab_extract')}")
    # 3. 마크업 서브탭
    sub_tabs.addTab(self._create_markup_subtab(), f"📝 {tm.get('subtab_markup')}")
    # 4. 기타 서브탭
    sub_tabs.addTab(self._create_misc_subtab(), f"📎 {tm.get('subtab_misc')}")

    layout.addWidget(sub_tabs)
    self.tabs.addTab(tab, f"🔧 {tm.get('tab_advanced')}")

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

def _create_extract_subtab(self):
    """추출 서브탭: 링크, 이미지, 테이블, 북마크, 정보, Markdown"""
    widget = QWidget()
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setSpacing(12)

    # 링크 추출
    grp_links = QGroupBox(tm.get("grp_extract_link"))
    l_links = QVBoxLayout(grp_links)
    self.sel_links = FileSelectorWidget()
    self.sel_links.pathChanged.connect(self._update_preview)
    l_links.addWidget(self.sel_links)
    b_links = QPushButton(tm.get("btn_extract_link"))
    b_links.setToolTip(tm.get("tooltip_extract_links"))
    b_links.clicked.connect(self.action_extract_links)
    l_links.addWidget(b_links)
    layout.addWidget(grp_links)

    # 이미지 추출
    grp_extract = QGroupBox(tm.get("grp_extract_img"))
    l_extract = QVBoxLayout(grp_extract)
    self.sel_extract = FileSelectorWidget()
    self.sel_extract.pathChanged.connect(self._update_preview)
    l_extract.addWidget(self.sel_extract)
    b_extract = QPushButton(tm.get("btn_extract_img_adv"))
    b_extract.setToolTip(tm.get("tooltip_extract_images"))
    b_extract.clicked.connect(self.action_extract_images)
    l_extract.addWidget(b_extract)
    layout.addWidget(grp_extract)

    # 테이블 추출
    grp_table = QGroupBox(tm.get("grp_extract_table"))
    l_table = QVBoxLayout(grp_table)
    self.sel_table = FileSelectorWidget()
    self.sel_table.pathChanged.connect(self._update_preview)
    l_table.addWidget(self.sel_table)
    b_table = QPushButton(tm.get("btn_extract_table"))
    b_table.setToolTip(tm.get("tooltip_extract_tables"))
    b_table.clicked.connect(self.action_extract_tables)
    l_table.addWidget(b_table)
    layout.addWidget(grp_table)

    # 북마크 추출
    grp_bm = QGroupBox(tm.get("grp_extract_bookmark"))
    l_bm = QVBoxLayout(grp_bm)
    self.sel_bm = FileSelectorWidget()
    self.sel_bm.pathChanged.connect(self._update_preview)
    l_bm.addWidget(self.sel_bm)
    b_bm = QPushButton(tm.get("btn_extract_bookmark"))
    b_bm.setToolTip(tm.get("tooltip_extract_bookmarks"))
    b_bm.clicked.connect(self.action_get_bookmarks)
    l_bm.addWidget(b_bm)
    layout.addWidget(grp_bm)

    # PDF 정보
    grp_info = QGroupBox(tm.get("grp_pdf_info"))
    l_info = QVBoxLayout(grp_info)
    self.sel_info = FileSelectorWidget()
    self.sel_info.pathChanged.connect(self._update_preview)
    l_info.addWidget(self.sel_info)
    b_info = QPushButton(tm.get("btn_extract_info"))
    b_info.setToolTip(tm.get("tooltip_pdf_info"))
    b_info.clicked.connect(self.action_pdf_info)
    l_info.addWidget(b_info)
    layout.addWidget(grp_info)

    # Markdown 추출
    grp_md = QGroupBox(tm.get("grp_extract_md"))
    l_md = QVBoxLayout(grp_md)
    self.sel_md = FileSelectorWidget()
    self.sel_md.pathChanged.connect(self._update_preview)
    l_md.addWidget(self.sel_md)
    b_md = QPushButton(tm.get("btn_extract_md"))
    b_md.setToolTip(tm.get("tooltip_extract_markdown"))
    b_md.clicked.connect(self.action_extract_markdown)
    l_md.addWidget(b_md)
    layout.addWidget(grp_md)

    layout.addStretch()
    scroll.setWidget(content)
    main_layout = QVBoxLayout(widget)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.addWidget(scroll)
    return widget

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

def _create_misc_subtab(self):
    """기타 서브탭: 양식, 비교, 서명, 복호화, 첨부파일"""
    widget = QWidget()
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setSpacing(12)

    # 양식 작성
    grp_form = QGroupBox(tm.get("grp_form"))
    l_form = QVBoxLayout(grp_form)
    self.sel_form = FileSelectorWidget()
    self.sel_form.pathChanged.connect(self._update_preview)
    l_form.addWidget(self.sel_form)
    self.form_fields_list = QListWidget()
    self.form_fields_list.setMaximumHeight(80)
    self.form_fields_list.setToolTip(tm.get("tooltip_form_list"))
    self.form_fields_list.itemDoubleClicked.connect(self._edit_form_field)
    l_form.addWidget(self.form_fields_list)
    btn_form_layout = QHBoxLayout()
    b_detect = QPushButton(tm.get("btn_detect_fields"))
    b_detect.clicked.connect(self.action_detect_fields)
    btn_form_layout.addWidget(b_detect)
    b_fill = QPushButton(tm.get("btn_save_form"))
    b_fill.setObjectName("actionBtn")
    b_fill.clicked.connect(self.action_fill_form)
    btn_form_layout.addWidget(b_fill)
    l_form.addLayout(btn_form_layout)
    layout.addWidget(grp_form)

    # PDF 비교
    grp_compare = QGroupBox(tm.get("grp_compare"))
    l_compare = QVBoxLayout(grp_compare)
    l_compare.addWidget(QLabel(tm.get("lbl_file_1")))
    self.sel_compare1 = FileSelectorWidget()
    l_compare.addWidget(self.sel_compare1)
    l_compare.addWidget(QLabel(tm.get("lbl_file_2")))
    self.sel_compare2 = FileSelectorWidget()
    l_compare.addWidget(self.sel_compare2)
    self.chk_compare_visual = QCheckBox(tm.get("chk_compare_visual_diff"))
    self.chk_compare_visual.setChecked(False)
    l_compare.addWidget(self.chk_compare_visual)
    b_compare = QPushButton(tm.get("btn_compare_pdf"))
    b_compare.setToolTip(tm.get("tooltip_compare"))
    b_compare.clicked.connect(self.action_compare_pdfs)
    l_compare.addWidget(b_compare)
    layout.addWidget(grp_compare)

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

    # 첨부 파일 관리
    grp_attach = QGroupBox(tm.get("grp_attach"))
    l_attach = QVBoxLayout(grp_attach)
    self.sel_attach = FileSelectorWidget()
    self.sel_attach.pathChanged.connect(self._update_preview)
    l_attach.addWidget(self.sel_attach)
    attach_btns = QHBoxLayout()
    b_list_attach = QPushButton(tm.get("btn_list_attach"))
    b_list_attach.clicked.connect(self.action_list_attachments)
    attach_btns.addWidget(b_list_attach)
    b_add_attach = QPushButton(tm.get("btn_add_attach"))
    b_add_attach.clicked.connect(self.action_add_attachment)
    attach_btns.addWidget(b_add_attach)
    b_extract_attach = QPushButton(tm.get("btn_extract_attach"))
    b_extract_attach.clicked.connect(self.action_extract_attachments)
    attach_btns.addWidget(b_extract_attach)
    l_attach.addLayout(attach_btns)
    layout.addWidget(grp_attach)

    # v4.5: 다른 PDF에서 페이지 복사
    grp_copy_page = QGroupBox(tm.get("grp_copy_page"))
    l_copy = QVBoxLayout(grp_copy_page)
    l_copy.addWidget(QLabel(tm.get("lbl_target_pdf")))
    self.sel_copy_target = FileSelectorWidget()
    self.sel_copy_target.pathChanged.connect(self._update_preview)
    l_copy.addWidget(self.sel_copy_target)
    l_copy.addWidget(QLabel(tm.get("lbl_source_pdf")))
    self.sel_copy_source = FileSelectorWidget()
    l_copy.addWidget(self.sel_copy_source)
    copy_opts = QHBoxLayout()
    copy_opts.addWidget(QLabel(tm.get("lbl_copy_pages")))
    self.txt_copy_pages = QLineEdit()
    self.txt_copy_pages.setPlaceholderText(tm.get("ph_copy_pages"))
    copy_opts.addWidget(self.txt_copy_pages)
    copy_opts.addWidget(QLabel(tm.get("lbl_insert_pos")))
    self.spn_copy_insert = QSpinBox()
    self.spn_copy_insert.setRange(-1, 9999)
    self.spn_copy_insert.setValue(-1)
    self.spn_copy_insert.setToolTip(tm.get("tooltip_insert_pos"))
    copy_opts.addWidget(self.spn_copy_insert)
    copy_opts.addStretch()
    l_copy.addLayout(copy_opts)
    b_copy_pages = QPushButton(tm.get("btn_copy_pages"))
    b_copy_pages.setObjectName("actionBtn")
    b_copy_pages.clicked.connect(self.action_copy_pages)
    l_copy.addWidget(b_copy_pages)
    layout.addWidget(grp_copy_page)

    # v4.5.3: 페이지 교체 (F-07 UI 노출)
    grp_replace = QGroupBox(tm.get("grp_replace_page"))
    l_replace = QVBoxLayout(grp_replace)
    l_replace.addWidget(QLabel(tm.get("lbl_target_pdf")))
    self.sel_replace_target = FileSelectorWidget()
    self.sel_replace_target.pathChanged.connect(self._update_preview)
    l_replace.addWidget(self.sel_replace_target)
    l_replace.addWidget(QLabel(tm.get("lbl_source_pdf")))
    self.sel_replace_source = FileSelectorWidget()
    l_replace.addWidget(self.sel_replace_source)
    replace_opts = QHBoxLayout()
    replace_opts.addWidget(QLabel(tm.get("lbl_replace_target_page")))
    self.spn_replace_target_page = QSpinBox()
    self.spn_replace_target_page.setRange(1, 9999)
    self.spn_replace_target_page.setValue(1)
    replace_opts.addWidget(self.spn_replace_target_page)
    replace_opts.addWidget(QLabel(tm.get("lbl_replace_source_page")))
    self.spn_replace_source_page = QSpinBox()
    self.spn_replace_source_page.setRange(1, 9999)
    self.spn_replace_source_page.setValue(1)
    replace_opts.addWidget(self.spn_replace_source_page)
    replace_opts.addStretch()
    l_replace.addLayout(replace_opts)
    b_replace = QPushButton(tm.get("btn_replace_page"))
    b_replace.setObjectName("actionBtn")
    b_replace.clicked.connect(self.action_replace_page)
    l_replace.addWidget(b_replace)
    layout.addWidget(grp_replace)

    # v4.5.3: 북마크 설정 (F-07 UI 노출)
    grp_set_bookmarks = QGroupBox(tm.get("grp_set_bookmarks"))
    l_set_bookmarks = QVBoxLayout(grp_set_bookmarks)
    self.sel_set_bookmarks = FileSelectorWidget()
    self.sel_set_bookmarks.pathChanged.connect(self._update_preview)
    l_set_bookmarks.addWidget(self.sel_set_bookmarks)
    l_set_bookmarks.addWidget(QLabel(tm.get("lbl_set_bookmarks_guide")))
    self.txt_set_bookmarks = QTextEdit()
    self.txt_set_bookmarks.setPlaceholderText(tm.get("ph_set_bookmarks"))
    self.txt_set_bookmarks.setMinimumHeight(90)
    l_set_bookmarks.addWidget(self.txt_set_bookmarks)
    b_set_bookmarks = QPushButton(tm.get("btn_set_bookmarks"))
    b_set_bookmarks.setObjectName("actionBtn")
    b_set_bookmarks.clicked.connect(self.action_set_bookmarks)
    l_set_bookmarks.addWidget(b_set_bookmarks)
    layout.addWidget(grp_set_bookmarks)

    # v4.5.3: 기본 주석 추가 (F-07 UI 노출)
    grp_add_annotation = QGroupBox(tm.get("grp_add_annotation_basic"))
    l_add_annotation = QVBoxLayout(grp_add_annotation)
    self.sel_add_annot = FileSelectorWidget()
    self.sel_add_annot.pathChanged.connect(self._update_preview)
    l_add_annotation.addWidget(self.sel_add_annot)
    annot_opts = QHBoxLayout()
    annot_opts.addWidget(QLabel(tm.get("tab_page") + ":"))
    self.spn_add_annot_page = QSpinBox()
    self.spn_add_annot_page.setRange(1, 9999)
    self.spn_add_annot_page.setValue(1)
    annot_opts.addWidget(self.spn_add_annot_page)
    annot_opts.addWidget(QLabel(tm.get("lbl_annotation_type")))
    self.cmb_add_annot_type = QComboBox()
    self.cmb_add_annot_type.addItem(tm.get("annot_type_text"), "text")
    self.cmb_add_annot_type.addItem(tm.get("annot_type_freetext"), "freetext")
    annot_opts.addWidget(self.cmb_add_annot_type)
    annot_opts.addStretch()
    l_add_annotation.addLayout(annot_opts)
    l_add_annotation.addWidget(QLabel(tm.get("lbl_annotation_text")))
    self.txt_add_annot_text = QLineEdit()
    self.txt_add_annot_text.setPlaceholderText(tm.get("ph_annotation_text"))
    l_add_annotation.addWidget(self.txt_add_annot_text)
    l_add_annotation.addWidget(QLabel(tm.get("lbl_annotation_point")))
    self.txt_add_annot_point = QLineEdit()
    self.txt_add_annot_point.setPlaceholderText(tm.get("ph_annotation_point"))
    l_add_annotation.addWidget(self.txt_add_annot_point)
    l_add_annotation.addWidget(QLabel(tm.get("lbl_annotation_rect")))
    self.txt_add_annot_rect = QLineEdit()
    self.txt_add_annot_rect.setPlaceholderText(tm.get("ph_annotation_rect"))
    l_add_annotation.addWidget(self.txt_add_annot_rect)
    b_add_annotation = QPushButton(tm.get("btn_add_annotation_basic"))
    b_add_annotation.setObjectName("actionBtn")
    b_add_annotation.clicked.connect(self.action_add_annotation_basic)
    l_add_annotation.addWidget(b_add_annotation)
    layout.addWidget(grp_add_annotation)

    layout.addStretch()
    scroll.setWidget(content)
    main_layout = QVBoxLayout(widget)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.addWidget(scroll)
    return widget
