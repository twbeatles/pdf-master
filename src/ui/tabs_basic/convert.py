import logging
import os

import fitz
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFormLayout,
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
    QVBoxLayout,
    QWidget,
)

from ...core.constants import SUPPORTED_IMAGE_FORMATS
from ...core.i18n import tm
from ...core.settings import save_settings
from ..widgets import FileListWidget, FileSelectorWidget, ImageListWidget, ToastWidget

logger = logging.getLogger(__name__)

def setup_convert_tab(self):
    tab = QWidget()
    layout = QVBoxLayout(tab)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    content = QWidget()
    content_layout = QVBoxLayout(content)

    # PDF → 이미지
    grp_img = QGroupBox(tm.get("grp_pdf_to_img"))
    l_img = QVBoxLayout(grp_img)
    step = QLabel(tm.get("step_pdf_to_img"))
    step.setObjectName("stepLabel")
    l_img.addWidget(step)
    self.img_conv_list = FileListWidget()
    self.img_conv_list.setMaximumHeight(100)
    l_img.addWidget(self.img_conv_list)
    self.img_conv_list.itemClicked.connect(self._on_list_item_clicked)
    self.img_conv_list.fileAdded.connect(self._update_preview)

    # 버튼 레이아웃
    btn_layout_img = QHBoxLayout()
    btn_add_pdf = QPushButton(tm.get("btn_add_pdf"))
    btn_add_pdf.clicked.connect(self._add_pdf_for_img)

    btn_clear_img = QPushButton(tm.get("btn_clear_all"))
    btn_clear_img.setToolTip(tm.get("tooltip_clear_list"))
    btn_clear_img.setStyleSheet("""
        QPushButton { background-color: #3e272b; color: #ff6b6b; border: 1px solid #5c3a3a; padding: 10px; }
        QPushButton:hover { background-color: #5c3a3a; color: #ff8787; }
    """)
    btn_clear_img.clicked.connect(self.img_conv_list.clear)

    btn_layout_img.addWidget(btn_add_pdf)
    btn_layout_img.addWidget(btn_clear_img)
    l_img.addLayout(btn_layout_img)

    opt = QHBoxLayout()
    opt.addWidget(QLabel(tm.get("lbl_format")))
    self.cmb_fmt = QComboBox()
    # 문서 정합 기준 포맷: png/jpg/webp/bmp/tiff
    preferred_output_formats = ["png", "jpg", "webp", "bmp", "tiff"]
    supported = set(SUPPORTED_IMAGE_FORMATS)
    self.cmb_fmt.addItems([fmt for fmt in preferred_output_formats if fmt in supported])
    opt.addWidget(self.cmb_fmt)
    opt.addWidget(QLabel(tm.get("lbl_dpi")))
    self.spn_dpi = QSpinBox()
    self.spn_dpi.setRange(72, 600)
    self.spn_dpi.setValue(150)
    opt.addWidget(self.spn_dpi)

    # 프리셋 버튼
    btn_save_preset = QPushButton("💾")
    btn_save_preset.setToolTip(tm.get("tooltip_save_preset"))
    btn_save_preset.setFixedWidth(36)
    btn_save_preset.clicked.connect(self._save_convert_preset)
    opt.addWidget(btn_save_preset)

    btn_load_preset = QPushButton("📂")
    btn_load_preset.setToolTip(tm.get("tooltip_load_preset"))
    btn_load_preset.setFixedWidth(36)
    btn_load_preset.clicked.connect(self._load_convert_preset)
    opt.addWidget(btn_load_preset)

    opt.addStretch()
    l_img.addLayout(opt)

    b_img = QPushButton(tm.get("btn_convert_to_img"))
    b_img.clicked.connect(self.action_img)
    l_img.addWidget(b_img)
    content_layout.addWidget(grp_img)

    # 이미지 → PDF
    grp_img2pdf = QGroupBox(tm.get("grp_img_to_pdf"))
    l_i2p = QVBoxLayout(grp_img2pdf)
    step2 = QLabel(tm.get("step_img_to_pdf"))
    step2.setObjectName("stepLabel")
    l_i2p.addWidget(step2)
    self.img_list = ImageListWidget()
    l_i2p.addWidget(self.img_list)

    btn_i2p = QHBoxLayout()
    b_add_img = QPushButton(tm.get("btn_add_img"))
    b_add_img.setObjectName("secondaryBtn")
    b_add_img.clicked.connect(self._add_images)
    b_clr_img = QPushButton(tm.get("btn_clear_img"))
    b_clr_img.setObjectName("secondaryBtn")
    b_clr_img.clicked.connect(self.img_list.clear)
    btn_i2p.addWidget(b_add_img)
    btn_i2p.addWidget(b_clr_img)
    btn_i2p.addStretch()
    l_i2p.addLayout(btn_i2p)

    b_i2p = QPushButton(tm.get("btn_convert_to_pdf"))
    b_i2p.clicked.connect(self.action_img_to_pdf)
    l_i2p.addWidget(b_i2p)
    content_layout.addWidget(grp_img2pdf)

    # 텍스트 추출
    grp_txt = QGroupBox(tm.get("grp_extract_text"))
    l_txt = QVBoxLayout(grp_txt)
    step_txt = QLabel(tm.get("lbl_extract_drag"))
    step_txt.setObjectName("stepLabel")
    l_txt.addWidget(step_txt)
    self.txt_conv_list = FileListWidget()
    self.txt_conv_list.setMaximumHeight(100)
    l_txt.addWidget(self.txt_conv_list)
    self.txt_conv_list.itemClicked.connect(self._on_list_item_clicked)
    self.txt_conv_list.fileAdded.connect(self._update_preview)

    # 버튼 레이아웃
    btn_layout_txt = QHBoxLayout()
    btn_add_txt = QPushButton(tm.get("btn_add_pdf"))
    btn_add_txt.clicked.connect(self._add_pdf_for_txt)

    btn_clear_txt = QPushButton(tm.get("btn_clear_all"))
    btn_clear_txt.setToolTip(tm.get("tooltip_clear_list"))
    btn_clear_txt.setStyleSheet("""
        QPushButton { background-color: #3e272b; color: #ff6b6b; border: 1px solid #5c3a3a; padding: 10px; }
        QPushButton:hover { background-color: #5c3a3a; color: #ff8787; }
    """)
    btn_clear_txt.clicked.connect(self.txt_conv_list.clear)

    btn_layout_txt.addWidget(btn_add_txt)
    btn_layout_txt.addWidget(btn_clear_txt)
    l_txt.addLayout(btn_layout_txt)
    b_txt = QPushButton(tm.get("btn_save_text"))
    b_txt.clicked.connect(self.action_txt)
    l_txt.addWidget(b_txt)
    content_layout.addWidget(grp_txt)


    # PDF → Word 변환 기능 제거됨 (v4.2)

    content_layout.addStretch()
    scroll.setWidget(content)
    layout.addWidget(scroll)
    self.tabs.addTab(tab, f"🔄 {tm.get('tab_convert')}")

def _add_images(self):
    files, _ = QFileDialog.getOpenFileNames(self, tm.get("dlg_title_img"), "", tm.get("file_filter_images"))
    for f in files:
        item = QListWidgetItem(f"🖼️ {os.path.basename(f)}")
        item.setData(Qt.ItemDataRole.UserRole, f)
        item.setToolTip(f)
        self.img_list.addItem(item)

def _add_pdf_for_img(self):
    """이미지 변환용 PDF 추가"""
    files, _ = QFileDialog.getOpenFileNames(self, tm.get("dlg_title_pdf"), "", "PDF (*.pdf)")
    for f in files:
        self.img_conv_list.add_file(f)

def _add_pdf_for_txt(self):
    """텍스트 추출용 PDF 추가"""
    files, _ = QFileDialog.getOpenFileNames(self, tm.get("dlg_title_pdf"), "", "PDF (*.pdf)")
    for f in files:
        self.txt_conv_list.add_file(f)

def action_img(self):
    paths = self.img_conv_list.get_all_paths()
    if not paths:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_add_pdf_files"))
    d = QFileDialog.getExistingDirectory(self, tm.get("dlg_select_output_dir"))
    if d:
        self.run_worker("convert_to_img", file_paths=paths, output_dir=d, 
                      fmt=self.cmb_fmt.currentText(), dpi=self.spn_dpi.value())

def action_img_to_pdf(self):
    files = self.img_list.get_all_paths()
    if not files:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_add_image_files"))
    save, _ = QFileDialog.getSaveFileName(self, tm.get("save"), "images.pdf", "PDF (*.pdf)")
    if save:
        self.run_worker("images_to_pdf", files=files, output_path=save)

def action_txt(self):
    paths = self.txt_conv_list.get_all_paths()
    if not paths:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_add_pdf_files"))
    d = QFileDialog.getExistingDirectory(self, tm.get("dlg_select_output_dir"))
    if d:
        self.run_worker("extract_text", file_paths=paths, output_dir=d)
