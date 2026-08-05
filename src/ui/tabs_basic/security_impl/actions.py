import logging
import os
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
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
from ....core.optional_deps import fitz
from ....core.constants import SUPPORTED_IMAGE_FORMATS
from ....core.i18n import tm
from ....core.worker_runtime.save_profiles import DEFAULT_COMPRESSION_SAVE_PROFILE, SAVE_PROFILE_CHOICES
from ....core.settings import save_settings
from ...widgets import FileListWidget, FileSelectorWidget, ImageListWidget, ToastWidget
logger = logging.getLogger(__name__)

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
        permissions = ["accessibility"]
        if getattr(self, "chk_perm_print", None) and self.chk_perm_print.isChecked():
            permissions.append("print")
        if getattr(self, "chk_perm_copy", None) and self.chk_perm_copy.isChecked():
            permissions.append("copy")
        if getattr(self, "chk_perm_modify", None) and self.chk_perm_modify.isChecked():
            permissions.append("modify")
        if getattr(self, "chk_perm_annotate", None) and self.chk_perm_annotate.isChecked():
            permissions.append("annotate")
        if getattr(self, "chk_perm_form", None) and self.chk_perm_form.isChecked():
            permissions.append("form")
        if getattr(self, "chk_perm_assemble", None) and self.chk_perm_assemble.isChecked():
            permissions.append("assemble")
        self.run_worker(
            "protect",
            file_path=path,
            output_path=s,
            password=pw,
            permissions=permissions,
        )

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

