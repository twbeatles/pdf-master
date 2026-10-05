import logging
import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from ..fluent_widgets import PrimaryButton, PushButton, QCheckBox, QComboBox, QDoubleSpinBox, QLineEdit, QSpinBox
from ..tab_shell import add_tab

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
    b_add = PushButton(tm.get("btn_add_files"))
    b_add.setObjectName("secondaryBtn")
    b_add.clicked.connect(self._batch_add_files)
    b_folder = PushButton(tm.get("btn_add_folder"))
    b_folder.setObjectName("secondaryBtn")
    b_folder.clicked.connect(self._batch_add_folder)
    b_clr = PushButton(tm.get("btn_clear_list"))
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
        self.cmb_batch_op.addItem(label, userData=value)
    opt_layout.addWidget(self.cmb_batch_op)
    opt_layout.addStretch()
    content_layout.addLayout(opt_layout)

    # 선택한 작업에 필요한 옵션만 보여 준다 (_sync_batch_option_rows).
    self._batch_hint = QLabel("")
    self._batch_hint.setObjectName("desc")
    self._batch_hint.setWordWrap(True)
    content_layout.addWidget(self._batch_hint)

    # 워터마크 문구 / 비밀번호 (작업에 따라 라벨·입력 방식이 바뀜)
    self._batch_text_row = QWidget()
    opt_layout2 = QHBoxLayout(self._batch_text_row)
    opt_layout2.setContentsMargins(0, 0, 0, 0)
    self._lbl_batch_opt = QLabel(tm.get("lbl_batch_watermark_text"))
    opt_layout2.addWidget(self._lbl_batch_opt)
    self.inp_batch_opt = QLineEdit()
    opt_layout2.addWidget(self.inp_batch_opt)
    content_layout.addWidget(self._batch_text_row)

    # 워터마크 글자 크기·투명도
    self._batch_wm_row = QWidget()
    wm_row = QHBoxLayout(self._batch_wm_row)
    wm_row.setContentsMargins(0, 0, 0, 0)
    wm_row.addWidget(QLabel(tm.get("lbl_batch_wm_fontsize")))
    self.spn_batch_wm_fontsize = QSpinBox()
    self.spn_batch_wm_fontsize.setRange(8, 120)
    self.spn_batch_wm_fontsize.setValue(40)
    wm_row.addWidget(self.spn_batch_wm_fontsize)
    wm_row.addWidget(QLabel(tm.get("lbl_batch_wm_opacity")))
    self.spn_batch_wm_opacity = QDoubleSpinBox()
    self.spn_batch_wm_opacity.setRange(0.05, 1.0)
    self.spn_batch_wm_opacity.setSingleStep(0.05)
    self.spn_batch_wm_opacity.setValue(0.3)
    wm_row.addWidget(self.spn_batch_wm_opacity)
    wm_row.addStretch()
    content_layout.addWidget(self._batch_wm_row)

    # 암호 설정 시 허용할 동작 (보안 탭의 단일 암호 설정과 같은 항목)
    self._batch_perm_box = QWidget()
    perm_layout = QVBoxLayout(self._batch_perm_box)
    perm_layout.setContentsMargins(0, 0, 0, 0)
    perm_row = QHBoxLayout()
    perm_row2 = QHBoxLayout()
    self.chk_batch_perm_print = QCheckBox(tm.get("chk_perm_print"))
    self.chk_batch_perm_print.setChecked(True)
    self.chk_batch_perm_copy = QCheckBox(tm.get("chk_perm_copy"))
    self.chk_batch_perm_copy.setChecked(True)
    self.chk_batch_perm_modify = QCheckBox(tm.get("chk_perm_modify"))
    self.chk_batch_perm_modify.setChecked(False)
    self.chk_batch_perm_annotate = QCheckBox(tm.get("chk_perm_annotate"))
    self.chk_batch_perm_annotate.setChecked(False)
    self.chk_batch_perm_form = QCheckBox(tm.get("chk_perm_form"))
    self.chk_batch_perm_form.setChecked(False)
    self.chk_batch_perm_assemble = QCheckBox(tm.get("chk_perm_assemble"))
    self.chk_batch_perm_assemble.setChecked(False)
    for index, chk in enumerate(
        (
            self.chk_batch_perm_print,
            self.chk_batch_perm_copy,
            self.chk_batch_perm_modify,
            self.chk_batch_perm_annotate,
            self.chk_batch_perm_form,
            self.chk_batch_perm_assemble,
        )
    ):
        (perm_row if index < 3 else perm_row2).addWidget(chk)
    perm_row.addStretch()
    perm_row2.addStretch()
    perm_layout.addLayout(perm_row)
    perm_layout.addLayout(perm_row2)
    content_layout.addWidget(self._batch_perm_box)

    self.cmb_batch_op.currentIndexChanged.connect(lambda _i: _sync_batch_option_rows(self))
    _sync_batch_option_rows(self)

    step3 = QLabel(tm.get("step_batch_3"))
    step3.setObjectName("stepLabel")
    content_layout.addWidget(step3)

    b_run = PrimaryButton(tm.get("btn_run_batch"))
    b_run.setObjectName("actionBtn")
    b_run.clicked.connect(self.action_batch)
    content_layout.addWidget(b_run)

    content_layout.addStretch()
    scroll.setWidget(content)
    layout.addWidget(scroll)
    add_tab(self.tabs, tab, tm.get('tab_batch'), icon="LIBRARY")

def _sync_batch_option_rows(self):
    """선택한 일괄 작업에 맞는 옵션만 보이게 하고, 비밀번호는 가려서 입력받는다."""
    op = self.cmb_batch_op.currentData() or "compress"
    is_watermark = op == "watermark"
    is_encrypt = op == "encrypt"
    self._batch_text_row.setVisible(is_watermark or is_encrypt)
    self._batch_wm_row.setVisible(is_watermark)
    self._batch_perm_box.setVisible(is_encrypt)
    self._batch_hint.setText(tm.get(f"hint_batch_{op}"))
    # 워터마크 문구와 비밀번호가 같은 입력란을 쓰므로 작업을 바꾸면 비운다.
    if getattr(self, "_batch_opt_for", op) != op:
        self.inp_batch_opt.clear()
    self._batch_opt_for = op
    if is_encrypt:
        self._lbl_batch_opt.setText(tm.get("lbl_batch_password"))
        self.inp_batch_opt.setPlaceholderText(tm.get("ph_password"))
        self.inp_batch_opt.setEchoMode(QLineEdit.EchoMode.Password)
    else:
        self._lbl_batch_opt.setText(tm.get("lbl_batch_watermark_text"))
        self.inp_batch_opt.setPlaceholderText(tm.get("ph_watermark_text"))
        self.inp_batch_opt.setEchoMode(QLineEdit.EchoMode.Normal)


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
    out_dir = self._choose_output_directory(tm.get("dlg_select_output_dir"))
    if not out_dir:
        return
    op = self.cmb_batch_op.currentData() or self.cmb_batch_op.currentText()
    opt = self.inp_batch_opt.text()
    if op in ("watermark", "encrypt") and not opt.strip():
        message_key = "msg_enter_password" if op == "encrypt" else "msg_enter_text"
        self.inp_batch_opt.setFocus()
        return QMessageBox.warning(self, tm.get("info"), tm.get(message_key))
    kwargs = {
        "files": files,
        "output_dir": out_dir,
        "operation": op,
        "option": opt,
    }
    if op == "encrypt":
        permissions: list[str] = ["accessibility"]
        if getattr(self, "chk_batch_perm_print", None) is not None and self.chk_batch_perm_print.isChecked():
            permissions.append("print")
        if getattr(self, "chk_batch_perm_copy", None) is not None and self.chk_batch_perm_copy.isChecked():
            permissions.append("copy")
        if getattr(self, "chk_batch_perm_modify", None) is not None and self.chk_batch_perm_modify.isChecked():
            permissions.append("modify")
        if getattr(self, "chk_batch_perm_annotate", None) is not None and self.chk_batch_perm_annotate.isChecked():
            permissions.append("annotate")
        if getattr(self, "chk_batch_perm_form", None) is not None and self.chk_batch_perm_form.isChecked():
            permissions.append("form")
        if getattr(self, "chk_batch_perm_assemble", None) is not None and self.chk_batch_perm_assemble.isChecked():
            permissions.append("assemble")
        kwargs["permissions"] = permissions
    if op == "watermark":
        if getattr(self, "spn_batch_wm_fontsize", None) is not None:
            kwargs["fontsize"] = int(self.spn_batch_wm_fontsize.value())
        if getattr(self, "spn_batch_wm_opacity", None) is not None:
            kwargs["opacity"] = float(self.spn_batch_wm_opacity.value())
    self.run_worker("batch", **kwargs)
