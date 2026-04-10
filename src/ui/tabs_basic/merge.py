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

def setup_merge_tab(self):
    tab = QWidget()
    layout = QVBoxLayout(tab)

    # Guide
    guide = QLabel(tm.get("guide_merge"))
    guide.setObjectName("desc")
    layout.addWidget(guide)

    step1 = QLabel(tm.get("step_merge_1"))
    step1.setObjectName("stepLabel")
    layout.addWidget(step1)

    self.merge_list = FileListWidget()
    self.merge_list.itemClicked.connect(self._on_list_item_clicked)
    layout.addWidget(self.merge_list)

    # v2.7: 파일 개수 표시
    merge_info_layout = QHBoxLayout()
    self.merge_count_label = QLabel(tm.get("lbl_merge_count").format(0))
    self.merge_count_label.setStyleSheet("color: #888; font-size: 12px;")
    merge_info_layout.addWidget(self.merge_count_label)
    merge_info_layout.addStretch()
    layout.addLayout(merge_info_layout)

    # 파일 추가/삭제 시 카운트 업데이트
    model = self.merge_list.model()
    if model is not None:
        model.rowsInserted.connect(self._update_merge_count)
        model.rowsRemoved.connect(self._update_merge_count)

    btn_box = QHBoxLayout()
    b_add = QPushButton(tm.get("btn_add_files_merge"))
    b_add.setObjectName("secondaryBtn")
    b_add.clicked.connect(self._merge_add_files)

    b_del = QPushButton(tm.get("btn_remove_sel"))
    b_del.setObjectName("secondaryBtn")
    b_del.clicked.connect(lambda: [self.merge_list.takeItem(self.merge_list.row(i)) for i in self.merge_list.selectedItems()])

    b_clr = QPushButton(tm.get("btn_clear_merge"))
    b_clr.setObjectName("secondaryBtn")
    b_clr.clicked.connect(self._confirm_clear_merge)  # v2.7: 확인 다이얼로그

    btn_box.addWidget(b_add)
    btn_box.addWidget(b_del)
    btn_box.addWidget(b_clr)
    btn_box.addStretch()
    layout.addLayout(btn_box)

    step2 = QLabel(tm.get("step_merge_2"))
    step2.setObjectName("stepLabel")
    layout.addWidget(step2)

    b_run = QPushButton(tm.get("btn_run_merge"))
    b_run.setObjectName("actionBtn")
    b_run.clicked.connect(self.action_merge)
    layout.addWidget(b_run)

    self.tabs.addTab(tab, f"📎 {tm.get('tab_merge')}")

def _merge_add_files(self):
    files, _ = QFileDialog.getOpenFileNames(self, tm.get("dlg_title_pdf"), "", "PDF (*.pdf)")
    for f in files:
        item = QListWidgetItem(f"📄 {os.path.basename(f)}")
        item.setData(Qt.ItemDataRole.UserRole, f)
        item.setToolTip(f)
        self.merge_list.addItem(item)

def _update_merge_count(self):
    """병합 탭 파일 개수 업데이트"""
    count = self.merge_list.count()
    self.merge_count_label.setText(tm.get("lbl_merge_count").format(count))

def _confirm_clear_merge(self):
    """전체 삭제 확인 다이얼로그"""
    if self.merge_list.count() == 0:
        return
    reply = QMessageBox.question(self, tm.get("confirm"), 
                                tm.get("msg_confirm_clear").format(self.merge_list.count()),
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    if reply == QMessageBox.StandardButton.Yes:
        self.merge_list.clear()

def action_merge(self):
    files = self.merge_list.get_all_paths()
    if len(files) < 2:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_merge_count_error"))
    save, _ = self._choose_save_file(tm.get("save"), "merged.pdf", "PDF (*.pdf)")
    if save:
        self.run_worker("merge", files=files, output_path=save)
