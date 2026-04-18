import logging
import os

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

from ...core.optional_deps import fitz
from ...core.constants import SUPPORTED_IMAGE_FORMATS
from ...core.i18n import tm
from ...core.worker_runtime.save_profiles import DEFAULT_COMPRESSION_SAVE_PROFILE, SAVE_PROFILE_CHOICES
from ...core.settings import save_settings
from ..widgets import FileListWidget, FileSelectorWidget, ImageListWidget, ToastWidget

logger = logging.getLogger(__name__)

def setup_edit_sec_tab(self):
    tab = QWidget()
    layout = QVBoxLayout(tab)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    content = QWidget()
    content_layout = QVBoxLayout(content)

    # 메타데이터
    # 메타데이터
    grp_meta = QGroupBox(tm.get("grp_metadata"))
    l_m = QVBoxLayout(grp_meta)
    self.sel_meta = FileSelectorWidget()
    self.sel_meta.pathChanged.connect(self._load_metadata)
    l_m.addWidget(self.sel_meta)
    self.sel_meta.pathChanged.connect(self._update_preview)
    form = QFormLayout()
    self.inp_title = QLineEdit()
    self.inp_author = QLineEdit()
    self.inp_subj = QLineEdit()
    form.addRow(tm.get("lbl_title"), self.inp_title)
    form.addRow(tm.get("lbl_author"), self.inp_author)
    form.addRow(tm.get("lbl_subject"), self.inp_subj)
    l_m.addLayout(form)
    b_m = QPushButton(tm.get("btn_save_metadata"))
    b_m.clicked.connect(self.action_metadata)
    l_m.addWidget(b_m)
    content_layout.addWidget(grp_meta)

    # 워터마크
    grp_wm = QGroupBox(tm.get("grp_watermark"))
    l_w = QVBoxLayout(grp_wm)
    self.sel_wm = FileSelectorWidget()
    l_w.addWidget(self.sel_wm)
    self.sel_wm.pathChanged.connect(self._update_preview)
    h_w = QHBoxLayout()
    self.inp_wm = QLineEdit()
    self.inp_wm.setPlaceholderText(tm.get("ph_watermark_text"))
    h_w.addWidget(self.inp_wm)
    self.cmb_wm_color = QComboBox()
    wm_colors = [
        (tm.get("color_gray"), (0.5, 0.5, 0.5)),
        (tm.get("color_black"), (0, 0, 0)),
        (tm.get("color_red"), (1, 0, 0)),
        (tm.get("color_blue"), (0, 0, 1)),
    ]
    for label, value in wm_colors:
        self.cmb_wm_color.addItem(label, value)
    h_w.addWidget(self.cmb_wm_color)
    l_w.addLayout(h_w)
    b_w = QPushButton(tm.get("btn_apply_watermark"))
    b_w.clicked.connect(self.action_watermark)
    l_w.addWidget(b_w)
    content_layout.addWidget(grp_wm)

    # v4.5: 이미지 워터마크
    grp_img_wm = QGroupBox(tm.get("grp_img_watermark"))
    l_img_wm = QVBoxLayout(grp_img_wm)
    l_img_wm.addWidget(QLabel(tm.get("lbl_target_pdf")))
    self.sel_img_wm_pdf = FileSelectorWidget()
    self.sel_img_wm_pdf.pathChanged.connect(self._update_preview)
    l_img_wm.addWidget(self.sel_img_wm_pdf)
    l_img_wm.addWidget(QLabel(tm.get("lbl_wm_image")))
    self.sel_img_wm_img = FileSelectorWidget("", ['.png', '.jpg', '.jpeg'])
    l_img_wm.addWidget(self.sel_img_wm_img)
    wm_opts1 = QHBoxLayout()
    wm_opts1.addWidget(QLabel(tm.get("lbl_wm_position")))
    self.cmb_img_wm_pos = QComboBox()
    img_wm_positions = [
        (tm.get("pos_center"), "center"),
        (tm.get("pos_top_center"), "top-center"),
        (tm.get("pos_bottom_center"), "bottom-center"),
        (tm.get("pos_top_left"), "top-left"),
        (tm.get("pos_top_right"), "top-right"),
        (tm.get("pos_bottom_left"), "bottom-left"),
        (tm.get("pos_bottom_right"), "bottom-right"),
    ]
    for label, value in img_wm_positions:
        self.cmb_img_wm_pos.addItem(label, value)
    wm_opts1.addWidget(self.cmb_img_wm_pos)
    wm_opts1.addStretch()
    l_img_wm.addLayout(wm_opts1)
    wm_opts2 = QHBoxLayout()
    wm_opts2.addWidget(QLabel(tm.get("lbl_wm_scale")))
    self.spn_img_wm_scale = QSpinBox()
    self.spn_img_wm_scale.setRange(10, 200)
    self.spn_img_wm_scale.setValue(100)
    self.spn_img_wm_scale.setSuffix("%")
    wm_opts2.addWidget(self.spn_img_wm_scale)
    wm_opts2.addWidget(QLabel(tm.get("lbl_wm_opacity")))
    self.spn_img_wm_opacity = QSpinBox()
    self.spn_img_wm_opacity.setRange(10, 100)
    self.spn_img_wm_opacity.setValue(50)
    self.spn_img_wm_opacity.setSuffix("%")
    wm_opts2.addWidget(self.spn_img_wm_opacity)
    wm_opts2.addStretch()
    l_img_wm.addLayout(wm_opts2)
    b_img_wm = QPushButton(tm.get("btn_apply_img_watermark"))
    b_img_wm.setObjectName("actionBtn")
    b_img_wm.clicked.connect(self.action_image_watermark)
    l_img_wm.addWidget(b_img_wm)
    content_layout.addWidget(grp_img_wm)

    # 보안
    grp_sec = QGroupBox(tm.get("grp_security"))
    l_sec = QVBoxLayout(grp_sec)
    self.sel_sec = FileSelectorWidget()
    l_sec.addWidget(self.sel_sec)
    self.sel_sec.pathChanged.connect(self._update_preview)
    h_sec = QHBoxLayout()
    self.inp_pw = QLineEdit()
    self.inp_pw.setPlaceholderText(tm.get("ph_password"))
    self.inp_pw.setEchoMode(QLineEdit.EchoMode.Password)
    h_sec.addWidget(self.inp_pw)
    self.cmb_compress_profile = QComboBox()
    for profile_name in SAVE_PROFILE_CHOICES:
        self.cmb_compress_profile.addItem(tm.get(f"save_profile_{profile_name}"), profile_name)
    default_index = self.cmb_compress_profile.findData(DEFAULT_COMPRESSION_SAVE_PROFILE)
    if default_index >= 0:
        self.cmb_compress_profile.setCurrentIndex(default_index)
    self.cmb_compress_profile.setToolTip(tm.get("tooltip_compress_profile"))
    h_sec.addWidget(self.cmb_compress_profile)
    b_enc = QPushButton(tm.get("btn_encrypt"))
    b_enc.clicked.connect(self.action_protect)
    h_sec.addWidget(b_enc)
    b_dec = QPushButton(tm.get("btn_decrypt"))
    b_dec.setToolTip(tm.get("tooltip_decrypt"))
    b_dec.clicked.connect(self.action_unlock)
    h_sec.addWidget(b_dec)
    b_comp = QPushButton(tm.get("btn_compress"))
    b_comp.clicked.connect(self.action_compress)
    h_sec.addWidget(b_comp)
    l_sec.addLayout(h_sec)
    content_layout.addWidget(grp_sec)

    content_layout.addStretch()
    scroll.setWidget(content)
    layout.addWidget(scroll)
    self.tabs.addTab(tab, f"🔒 {tm.get('tab_edit')}")

def _load_metadata(self, path):
    if not path or not os.path.exists(path):
        return
    doc = None
    try:
        doc = fitz.open(path)
        metadata = doc.metadata
        m = metadata if isinstance(metadata, dict) else {}
        self.inp_title.setText(m.get('title', '') or '')
        self.inp_author.setText(m.get('author', '') or '')
        self.inp_subj.setText(m.get('subject', '') or '')
    except Exception:
        pass
    finally:
        if doc:
            doc.close()

def action_metadata(self):
    path = self.sel_meta.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_file"))
    meta = {'title': self.inp_title.text(), 'author': self.inp_author.text(), 'subject': self.inp_subj.text()}
    s, _ = self._choose_save_file(tm.get("save"), "metadata_updated.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("metadata_update", file_path=path, output_path=s, metadata=meta)

def action_watermark(self):
    path = self.sel_wm.get_path()
    text = self.inp_wm.text()
    if not path or not text:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_file_and_text_required"))
    color = self.cmb_wm_color.currentData() or (0.5, 0.5, 0.5)
    s, _ = self._choose_save_file(tm.get("save"), "watermarked.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("watermark", file_path=path, output_path=s, text=text, color=color)

def action_protect(self):
    path = self.sel_sec.get_path()
    pw = self.inp_pw.text()
    if not path or not pw:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_file_and_password_required"))
    s, _ = self._choose_save_file(tm.get("save"), "encrypted.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("protect", file_path=path, output_path=s, password=pw)

def action_unlock(self):
    path = self.sel_sec.get_path()
    pw = self.inp_pw.text()

    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))

    if not pw:
         return QMessageBox.warning(self, tm.get("info"), tm.get("err_password_required"))

    s, _ = self._choose_save_file(tm.get("save"), "decrypted.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("decrypt_pdf", file_path=path, output_path=s, password=pw)

def action_compress(self):
    path = self.sel_sec.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_file"))
    s, _ = self._choose_save_file(tm.get("save"), "compressed.pdf", "PDF (*.pdf)")
    if s:
        save_profile = self.cmb_compress_profile.currentData() or DEFAULT_COMPRESSION_SAVE_PROFILE
        self.run_worker("compress", file_path=path, output_path=s, save_profile=save_profile)
