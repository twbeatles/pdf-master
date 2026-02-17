import logging
import os

import fitz
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.i18n import tm
from .widgets import FileSelectorWidget, ToastWidget

logger = logging.getLogger(__name__)


class MainWindowTabsAdvancedMixin:

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
        b_split.setToolTip("PDF를 여러 파일로 분할합니다")
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
        sides = ["left", "top", "right", "bottom"]
        labels = [tm.get("lbl_left"), tm.get("lbl_top"), tm.get("lbl_right"), tm.get("lbl_bottom")]
        py_sides = ["좌", "상", "우", "하"] # Keep py names as is for attribute access unless refactored
        for i, side_name in enumerate(py_sides):
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
        b_rev.setToolTip("페이지 순서를 뒤집습니다")
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
        b_links.setToolTip("PDF에 포함된 모든 URL 추출")
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
        b_extract.setToolTip("PDF에 포함된 모든 이미지 추출")
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
        b_table.setToolTip("PDF의 표 데이터를 CSV로 추출")
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
        b_bm.setToolTip("PDF의 목차/북마크 구조 추출")
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
        b_info.setToolTip("페이지 수, 글자 수, 폰트 등 상세 정보")
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
        b_md.setToolTip("PDF 텍스트를 Markdown 형식으로 저장")
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
        self.spn_sig_page.setRange(-1, 9999)
        self.spn_sig_page.setValue(-1)
        self.spn_sig_page.setToolTip(tm.get("tooltip_sig_pos"))
        sig_opts.addWidget(self.spn_sig_page)
        sig_opts.addStretch()
        l_sig.addLayout(sig_opts)
        b_sig = QPushButton(tm.get("btn_insert_sig"))
        b_sig.clicked.connect(self.action_insert_signature)
        l_sig.addWidget(b_sig)
        layout.addWidget(grp_sig)
        
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
        
        layout.addStretch()
        scroll.setWidget(content)
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)
        return widget

    def action_split_adv(self):
        path = self.sel_split_adv.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        out_dir = QFileDialog.getExistingDirectory(self, "저장 폴더 선택")
        if out_dir:
            mode = self.cmb_split_mode.currentData() or "each"
            if mode == "range" and not self.inp_split_range.text().strip():
                return QMessageBox.warning(self, "알림", "페이지 범위를 입력하세요.")
            self.run_worker("split_by_pages", file_path=path, output_dir=out_dir, 
                          split_mode=mode, ranges=self.inp_split_range.text())

    def action_stamp(self):
        path = self.sel_stamp.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "stamped.pdf", "PDF (*.pdf)")
        if s:
            pos = self.cmb_stamp_pos.currentData() or "top-right"
            self.run_worker("add_stamp", file_path=path, output_path=s,
                          stamp_text=self.cmb_stamp.currentText(), position=pos)

    def action_crop(self):
        path = self.sel_crop.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "cropped.pdf", "PDF (*.pdf)")
        if s:
            margins = {
                'left': self.spn_crop_좌.value(),
                'top': self.spn_crop_상.value(),
                'right': self.spn_crop_우.value(),
                'bottom': self.spn_crop_하.value()
            }
            self.run_worker("crop_pdf", file_path=path, output_path=s, margins=margins)

    def action_blank_page(self):
        path = self.sel_blank.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "with_blank.pdf", "PDF (*.pdf)")
        if s:
            pos = self.spn_blank_pos.value() - 1  # 0-indexed
            self.run_worker("insert_blank_page", file_path=path, output_path=s, position=pos)

    # ===================== 신규 기능 액션 =====================

    def action_extract_links(self):
        """PDF 링크 추출"""
        path = self.sel_links.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "links.txt", "텍스트 (*.txt)")
        if s:
            self.run_worker("extract_links", file_path=path, output_path=s)

    def action_detect_fields(self):
        """PDF 양식 필드 감지"""
        path = self.sel_form.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        
        doc = None
        try:
            import fitz
            doc = fitz.open(path)
            self.form_fields_list.clear()
            self._form_field_data = {}  # 필드 데이터 저장
            
            for page_num, page in enumerate(doc):
                widgets = page.widgets()
                if widgets:
                    for widget in widgets:
                        name = widget.field_name or f"field_{self.form_fields_list.count()}"
                        value = widget.field_value or ""
                        item = QListWidgetItem(f"📋 {name}: {value}")
                        item.setData(Qt.ItemDataRole.UserRole, name)
                        item.setToolTip(f"타입: {widget.field_type_string}, 페이지: {page_num + 1}")
                        self.form_fields_list.addItem(item)
                        self._form_field_data[name] = value
            
            count = self.form_fields_list.count()
            if count == 0:
                QMessageBox.information(self, "양식", "양식 필드가 없습니다.")
            else:
                toast = ToastWidget(f"{count}개 필드 감지됨", toast_type='success', duration=2000)
                toast.show_toast(self)
        except Exception as e:
            QMessageBox.warning(self, "오류", f"필드 감지 실패: {e}")
        finally:
            if doc:
                doc.close()

    def _edit_form_field(self, item):
        """양식 필드 값 수정"""
        name = item.data(Qt.ItemDataRole.UserRole)
        current_value = self._form_field_data.get(name, "")
        
        new_value, ok = QInputDialog.getText(self, "필드 수정", f"'{name}' 값:", 
                                             QLineEdit.EchoMode.Normal, current_value)
        if ok:
            self._form_field_data[name] = new_value
            item.setText(f"📋 {name}: {new_value}")

    def action_fill_form(self):
        """양식 작성 저장"""
        path = self.sel_form.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        if not hasattr(self, '_form_field_data') or not self._form_field_data:
            return QMessageBox.warning(self, "알림", "먼저 필드를 감지하세요.")
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "filled_form.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("fill_form", file_path=path, output_path=s, 
                          field_values=self._form_field_data)

    def action_compare_pdfs(self):
        """PDF 비교"""
        path1 = self.sel_compare1.get_path()
        path2 = self.sel_compare2.get_path()
        
        if not path1 or not path2:
            return QMessageBox.warning(self, "알림", "두 개의 PDF 파일을 모두 선택하세요.")
        
        s, _ = QFileDialog.getSaveFileName(self, "비교 결과 저장", "comparison.txt", "텍스트 (*.txt)")
        if s:
            self.run_worker("compare_pdfs", file_path1=path1, file_path2=path2, output_path=s)

    # ===================== v2.8 신규 기능 액션 =====================

    def action_pdf_info(self):
        """PDF 정보 추출"""
        path = self.sel_info.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "pdf_info.txt", "텍스트 (*.txt)")
        if s:
            self.run_worker("get_pdf_info", file_path=path, output_path=s)

    def action_duplicate_page(self):
        """페이지 복제"""
        path = self.sel_dup.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "duplicated.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("duplicate_page", file_path=path, output_path=s,
                          page_num=self.spn_dup_page.value() - 1,  # 0-indexed
                          count=self.spn_dup_count.value())

    def action_reverse_pages(self):
        """페이지 역순 정렬"""
        path = self.sel_rev.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "reversed.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("reverse_pages", file_path=path, output_path=s)

    def action_resize_pages(self):
        """페이지 크기 변경"""
        path = self.sel_resize.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "resized.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("resize_pages", file_path=path, output_path=s,
                          target_size=self.cmb_resize.currentData() or self.cmb_resize.currentText())

    def action_extract_images(self):
        """이미지 추출"""
        path = self.sel_extract.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        out_dir = QFileDialog.getExistingDirectory(self, "저장 폴더 선택")
        if out_dir:
            self.run_worker("extract_images", file_path=path, output_dir=out_dir)

    def action_insert_signature(self):
        """전자 서명 삽입"""
        pdf_path = self.sel_sig_pdf.get_path()
        sig_path = self.sel_sig_img.get_path()
        
        if not pdf_path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        if not sig_path:
            return QMessageBox.warning(self, "알림", "서명 이미지를 선택하세요.")
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "signed.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("insert_signature", file_path=pdf_path, output_path=s,
                          signature_path=sig_path,
                          page_num=self.spn_sig_page.value(),
                          position=self.cmb_sig_pos.currentData() or "bottom_right")

    # ===================== v2.9 신규 기능 액션 =====================

    def action_get_bookmarks(self):
        """북마크 추출"""
        path = self.sel_bm.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "bookmarks.txt", "텍스트 (*.txt)")
        if s:
            self.run_worker("get_bookmarks", file_path=path, output_path=s)

    def action_search_text(self):
        """텍스트 검색"""
        path = self.sel_search.get_path()
        term = self.inp_search.text().strip()
        
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        if not term:
            return QMessageBox.warning(self, "알림", "검색어를 입력하세요.")
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "search_results.txt", "텍스트 (*.txt)")
        if s:
            self.run_worker("search_text", file_path=path, output_path=s, search_term=term)

    def action_highlight_text(self):
        """텍스트 하이라이트"""
        path = self.sel_search.get_path()
        term = self.inp_search.text().strip()
        
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        if not term:
            return QMessageBox.warning(self, "알림", "검색어를 입력하세요.")
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "highlighted.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("highlight_text", file_path=path, output_path=s, search_term=term)

    # ===================== v3.0 신규 기능 액션 =====================

    def action_extract_tables(self):
        """테이블 추출"""
        path = self.sel_table.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "tables.csv", "CSV (*.csv)")
        if s:
            self.run_worker("extract_tables", file_path=path, output_path=s)

    def action_decrypt_pdf(self):
        """PDF 복호화"""
        path = self.sel_decrypt.get_path()
        password = self.inp_decrypt_pw.text()
        
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        if not password:
            return QMessageBox.warning(self, "알림", "비밀번호를 입력하세요.")
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "decrypted.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("decrypt_pdf", file_path=path, output_path=s, password=password)

    def action_list_annotations(self):
        """주석 목록 추출"""
        path = self.sel_annot.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "annotations.txt", "텍스트 (*.txt)")
        if s:
            self.run_worker("list_annotations", file_path=path, output_path=s)

    def action_remove_annotations(self):
        """모든 주석 삭제"""
        path = self.sel_annot.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        
        reply = QMessageBox.question(self, "확인", 
                                    "모든 주석을 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "no_annotations.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("remove_annotations", file_path=path, output_path=s)

    def action_list_attachments(self):
        """첨부 파일 목록"""
        path = self.sel_attach.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        
        doc = None
        try:
            import fitz
            doc = fitz.open(path)
            count = doc.embfile_count()
            
            if count == 0:
                QMessageBox.information(self, "첨부 파일", "첨부 파일이 없습니다.")
            else:
                attachments = []
                for i in range(count):
                    info = doc.embfile_info(i)
                    attachments.append(f"• {info.get('name', 'Unknown')} ({info.get('size', 0)} bytes)")
                
                QMessageBox.information(self, "첨부 파일 목록", 
                                       f"{count}개 첨부 파일:\n\n" + "\n".join(attachments))
        except Exception as e:
            QMessageBox.warning(self, "오류", f"첨부 파일 목록 오류: {e}")
        finally:
            if doc:
                doc.close()

    def action_add_attachment(self):
        """파일 첨부"""
        pdf_path = self.sel_attach.get_path()
        if not pdf_path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        
        attach_path, _ = QFileDialog.getOpenFileName(self, "첨부할 파일 선택", "", "모든 파일 (*.*)")
        if not attach_path:
            return
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "with_attachment.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("add_attachment", file_path=pdf_path, output_path=s, attach_path=attach_path)

    def action_extract_attachments(self):
        """첨부 파일 추출"""
        path = self.sel_attach.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        
        out_dir = QFileDialog.getExistingDirectory(self, "첨부 파일 저장 폴더 선택")
        if out_dir:
            self.run_worker("extract_attachments", file_path=path, output_dir=out_dir)

    def action_redact_text(self):
        """텍스트 교정 (영구 삭제)"""
        path = self.sel_redact.get_path()
        term = self.inp_redact.text().strip()
        
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        if not term:
            return QMessageBox.warning(self, "알림", "삭제할 텍스트를 입력하세요.")
        
        reply = QMessageBox.warning(self, "경고", 
                                   f"'{term}' 텍스트가 영구적으로 삭제됩니다.\n이 작업은 되돌릴 수 없습니다.\n\n계속하시겠습니까?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "redacted.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("redact_text", file_path=path, output_path=s, search_term=term)

    def action_extract_markdown(self):
        """Markdown 추출"""
        path = self.sel_md.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "output.md", "Markdown (*.md)")
        if s:
            self.run_worker("extract_markdown", file_path=path, output_path=s)

    def action_add_text_markup(self):
        """텍스트 마크업 추가"""
        path = self.sel_markup.get_path()
        term = self.inp_markup.text().strip()
        
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        if not term:
            return QMessageBox.warning(self, "알림", "마크업할 텍스트를 입력하세요.")
        
        markup_type = self.cmb_markup.currentData() or "underline"
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "marked_up.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("add_text_markup", file_path=path, output_path=s, 
                          search_term=term, markup_type=markup_type)

    def action_add_background(self):
        """배경색 추가"""
        path = self.sel_bg.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        
        color = self.cmb_bg_color.currentData() or [1, 1, 0.9]
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "with_background.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("add_background", file_path=path, output_path=s, color=color)

    # ===================== v3.2 신규 기능 액션 =====================

    def action_add_sticky_note(self):
        """스티키 노트 추가"""
        path = self.sel_sticky.get_path()
        content = self.txt_sticky_content.text().strip()
        
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        if not content:
            return QMessageBox.warning(self, "알림", "메모 내용을 입력하세요.")
        
        x = self.spn_sticky_x.value()
        y = self.spn_sticky_y.value()
        page_num = self.spn_sticky_page.value() - 1
        icon = self.cmb_sticky_icon.currentText()
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "with_note.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("add_sticky_note", file_path=path, output_path=s,
                          page_num=page_num, x=x, y=y, content=content, icon=icon)

    def action_add_ink_annotation(self):
        """프리핸드 드로잉 추가"""
        path = self.sel_ink.get_path()
        points_text = self.txt_ink_points.text().strip()
        
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        if not points_text:
            return QMessageBox.warning(self, "알림", "좌표를 입력하세요. 형식: x1,y1;x2,y2;x3,y3")
        
        # 좌표 파싱
        try:
            points = []
            for pt in points_text.split(";"):
                coords = pt.strip().split(",")
                if len(coords) >= 2:
                    points.append([float(coords[0]), float(coords[1])])
            
            if len(points) < 2:
                return QMessageBox.warning(self, "알림", "최소 2개 이상의 좌표가 필요합니다.")
        except Exception as e:
            return QMessageBox.warning(self, "오류", f"좌표 형식 오류: {e}")
        
        page_num = self.spn_ink_page.value() - 1
        width = self.spn_ink_width.value()
        
        color = self.cmb_ink_color.currentData() or (0, 0, 1)
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "with_drawing.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("add_ink_annotation", file_path=path, output_path=s,
                          page_num=page_num, points=points, color=color, width=width)
    
    # ===================== v4.5 신규 기능 액션 =====================

    def action_draw_shape(self):
        """도형 그리기"""
        path = self.sel_shape.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        
        shape_type = self.cmb_shape_type.currentData() or "rect"
        
        page_num = self.spn_shape_page.value() - 1
        x = self.spn_shape_x.value()
        y = self.spn_shape_y.value()
        w = self.spn_shape_w.value()
        h = self.spn_shape_h.value()
        
        line_color = self.cmb_shape_line_color.currentData() or (0, 0, 1)
        
        fill_color = self.cmb_shape_fill_color.currentData()
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "with_shape.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("draw_shapes", file_path=path, output_path=s,
                          page_num=page_num, shape_type=shape_type,
                          x=x, y=y, width=w, height=h,
                          line_color=line_color, fill_color=fill_color)

    def action_add_hyperlink(self):
        """하이퍼링크 추가"""
        path = self.sel_link.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        
        link_mode = self.cmb_link_type.currentData() or "url"
        is_url = link_mode == "url"
        page_num = self.spn_link_page.value() - 1
        
        if is_url:
            url = self.txt_link_url.text().strip()
            if not url:
                return QMessageBox.warning(self, "알림", "URL을 입력하세요.")
            target = url
            link_type = "url"
        else:
            target_page = self.spn_link_target.value() - 1
            target = target_page
            link_type = "page"
        
        area_text = self.txt_link_area.text().strip()
        if not area_text:
            return QMessageBox.warning(self, "알림", "링크 영역을 입력하세요 (x1,y1,x2,y2)")
        
        try:
            coords = [float(x.strip()) for x in area_text.split(",")]
            if len(coords) != 4:
                raise ValueError("4개 좌표 필요")
            rect = coords
        except Exception as e:
            return QMessageBox.warning(self, "오류", f"좌표 형식 오류: {e}")
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "with_link.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("add_link", file_path=path, output_path=s,
                          page_num=page_num, link_type=link_type,
                          target=target, rect=rect)

    def action_insert_textbox(self):
        """텍스트 상자 삽입"""
        path = self.sel_textbox.get_path()
        text = self.txt_textbox_content.text().strip()
        
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        if not text:
            return QMessageBox.warning(self, "알림", "텍스트를 입력하세요.")
        
        page_num = self.spn_tb_page.value() - 1
        x = self.spn_tb_x.value()
        y = self.spn_tb_y.value()
        fontsize = self.spn_tb_fontsize.value()
        
        color = self.cmb_tb_color.currentData() or (0, 0, 0)
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "with_textbox.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("insert_textbox", file_path=path, output_path=s,
                          page_num=page_num, x=x, y=y, text=text,
                          fontsize=fontsize, color=color)

    def action_copy_pages(self):
        """다른 PDF에서 페이지 복사"""
        target_path = self.sel_copy_target.get_path()
        source_path = self.sel_copy_source.get_path()
        page_range = self.txt_copy_pages.text().strip()
        
        if not target_path:
            return QMessageBox.warning(self, "알림", "대상 PDF 파일을 선택하세요.")
        if not source_path:
            return QMessageBox.warning(self, "알림", "소스 PDF 파일을 선택하세요.")
        if not page_range:
            return QMessageBox.warning(self, "알림", "복사할 페이지를 입력하세요.")
        
        insert_pos = self.spn_copy_insert.value()
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "merged.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("copy_page_between_docs", file_path=target_path, output_path=s,
                          source_path=source_path, page_range=page_range, insert_at=insert_pos)

    def action_image_watermark(self):
        """이미지 워터마크 적용"""
        pdf_path = self.sel_img_wm_pdf.get_path()
        img_path = self.sel_img_wm_img.get_path()
        
        if not pdf_path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        if not img_path:
            return QMessageBox.warning(self, "알림", "이미지 파일을 선택하세요.")
        
        position = self.cmb_img_wm_pos.currentData() or "center"
        scale = self.spn_img_wm_scale.value() / 100.0
        opacity = self.spn_img_wm_opacity.value() / 100.0
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "with_image_watermark.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("image_watermark", file_path=pdf_path, output_path=s,
                          image_path=img_path, position=position,
                          scale=scale, opacity=opacity)
    
    # ===================== Tab 8: AI 요약 (v4.0) =====================
