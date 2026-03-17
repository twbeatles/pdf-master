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

from ...core.constants import SUPPORTED_IMAGE_FORMATS
from ...core.i18n import tm
from ...core.settings import save_settings
from ..widgets import FileListWidget, FileSelectorWidget, ImageListWidget, ToastWidget

logger = logging.getLogger(__name__)

def setup_batch_tab(self):
    tab = QWidget()
    layout = QVBoxLayout(tab)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    content = QWidget()
    content_layout = QVBoxLayout(content)

    guide = QLabel(tm.get("guide_batch"))
    guide.setObjectName("desc")
    content_layout.addWidget(guide)

    step1 = QLabel(tm.get("step_batch_1"))
    step1.setObjectName("stepLabel")
    content_layout.addWidget(step1)

    self.batch_list = FileListWidget()
    self.batch_list.itemClicked.connect(self._on_list_item_clicked)
    content_layout.addWidget(self.batch_list)

    btn_box = QHBoxLayout()
    b_add = QPushButton(tm.get("btn_add_files"))
    b_add.setObjectName("secondaryBtn")
    b_add.clicked.connect(self._batch_add_files)
    b_folder = QPushButton(tm.get("btn_add_folder"))
    b_folder.setObjectName("secondaryBtn")
    b_folder.clicked.connect(self._batch_add_folder)
    b_clr = QPushButton(tm.get("btn_clear_list"))
    b_clr.setObjectName("secondaryBtn")
    b_clr.clicked.connect(self.batch_list.clear)
    btn_box.addWidget(b_add)
    btn_box.addWidget(b_folder)
    btn_box.addWidget(b_clr)
    btn_box.addStretch()
    content_layout.addLayout(btn_box)

    step2 = QLabel(tm.get("step_batch_2"))
    step2.setObjectName("stepLabel")
    content_layout.addWidget(step2)

    # 작업 선택
    opt_layout = QHBoxLayout()
    opt_layout.addWidget(QLabel(tm.get("lbl_operation")))
    self.cmb_batch_op = QComboBox()
    batch_ops = [
        (tm.get("op_compress"), "compress"),
        (tm.get("op_watermark"), "watermark"),
        (tm.get("op_encrypt"), "encrypt"),
        (tm.get("op_rotate"), "rotate"),
    ]
    for label, value in batch_ops:
        self.cmb_batch_op.addItem(label, value)
    opt_layout.addWidget(self.cmb_batch_op)
    opt_layout.addStretch()
    content_layout.addLayout(opt_layout)

    # 워터마크/암호 옵션
    opt_layout2 = QHBoxLayout()
    opt_layout2.addWidget(QLabel(tm.get("lbl_batch_option")))
    self.inp_batch_opt = QLineEdit()
    self.inp_batch_opt.setPlaceholderText(tm.get("ph_batch_option"))
    opt_layout2.addWidget(self.inp_batch_opt)
    content_layout.addLayout(opt_layout2)

    step3 = QLabel(tm.get("step_batch_3"))
    step3.setObjectName("stepLabel")
    content_layout.addWidget(step3)

    b_run = QPushButton(tm.get("btn_run_batch"))
    b_run.setObjectName("actionBtn")
    b_run.clicked.connect(self.action_batch)
    content_layout.addWidget(b_run)

    content_layout.addStretch()
    scroll.setWidget(content)
    layout.addWidget(scroll)
    self.tabs.addTab(tab, f"📦 {tm.get('tab_batch')}")

def _batch_add_files(self):
    files, _ = QFileDialog.getOpenFileNames(self, tm.get("dlg_title_pdf"), "", "PDF (*.pdf)")
    for f in files:
        item = QListWidgetItem(f"📄 {os.path.basename(f)}")
        item.setData(Qt.ItemDataRole.UserRole, f)
        item.setToolTip(f)
        self.batch_list.addItem(item)

def _batch_add_folder(self):
    folder = QFileDialog.getExistingDirectory(self, tm.get("dlg_select_folder"))
    if folder:
        for f in os.listdir(folder):
            if f.lower().endswith('.pdf'):
                path = os.path.join(folder, f)
                item = QListWidgetItem(f"📄 {f}")
                item.setData(Qt.ItemDataRole.UserRole, path)
                item.setToolTip(path)
                self.batch_list.addItem(item)

def action_batch(self):
    files = self.batch_list.get_all_paths()
    if not files:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_add_pdf_files"))
    out_dir = QFileDialog.getExistingDirectory(self, tm.get("dlg_select_output_dir"))
    if not out_dir:
        return
    op = self.cmb_batch_op.currentData() or self.cmb_batch_op.currentText()
    opt = self.inp_batch_opt.text()
    if op in ("watermark", "encrypt") and not opt:
        return QMessageBox.warning(self, tm.get("info"), tm.get("ph_batch_option"))
    self.run_worker("batch", files=files, output_dir=out_dir, operation=op, option=opt)
