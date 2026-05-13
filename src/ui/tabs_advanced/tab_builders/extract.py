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
    md_mode_row = QHBoxLayout()
    md_mode_row.addWidget(QLabel(tm.get("lbl_markdown_mode")))
    self.cmb_md_mode = QComboBox()
    markdown_modes = [
        (tm.get("markdown_mode_auto"), "auto"),
        (tm.get("markdown_mode_native"), "native"),
        (tm.get("markdown_mode_text"), "text"),
    ]
    for label, value in markdown_modes:
        self.cmb_md_mode.addItem(label, value)
    md_mode_row.addWidget(self.cmb_md_mode)
    md_mode_row.addStretch()
    l_md.addLayout(md_mode_row)
    self.chk_md_front_matter = QCheckBox(tm.get("chk_markdown_front_matter"))
    self.chk_md_front_matter.setChecked(False)
    l_md.addWidget(self.chk_md_front_matter)
    self.chk_md_page_markers = QCheckBox(tm.get("chk_markdown_page_markers"))
    self.chk_md_page_markers.setChecked(True)
    l_md.addWidget(self.chk_md_page_markers)
    self.chk_md_asset_placeholders = QCheckBox(tm.get("chk_markdown_asset_placeholders"))
    self.chk_md_asset_placeholders.setChecked(False)
    l_md.addWidget(self.chk_md_asset_placeholders)
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
