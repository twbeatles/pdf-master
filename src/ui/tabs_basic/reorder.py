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
from ...core.settings import save_settings
from ..widgets import FileListWidget, FileSelectorWidget, ImageListWidget, ToastWidget

logger = logging.getLogger(__name__)

def setup_reorder_tab(self):
    tab = QWidget()
    layout = QVBoxLayout(tab)

    guide = QLabel(tm.get("guide_reorder"))
    guide.setObjectName("desc")
    layout.addWidget(guide)

    step1 = QLabel(tm.get("step_reorder_1"))
    step1.setObjectName("stepLabel")
    layout.addWidget(step1)

    self.sel_reorder = FileSelectorWidget()
    self.sel_reorder.pathChanged.connect(self._load_pages_for_reorder)
    layout.addWidget(self.sel_reorder)
    self.sel_reorder.pathChanged.connect(self._update_preview)

    step2 = QLabel(tm.get("step_reorder_2"))
    step2.setObjectName("stepLabel")
    layout.addWidget(step2)

    self.reorder_list = QListWidget()
    self.reorder_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
    self.reorder_list.setMinimumHeight(150)
    self.reorder_list.setToolTip(tm.get("tooltip_reorder_list"))
    layout.addWidget(self.reorder_list)

    btn_box = QHBoxLayout()
    b_reverse = QPushButton(tm.get("btn_reverse_order"))
    b_reverse.setObjectName("secondaryBtn")
    b_reverse.clicked.connect(self._reverse_pages)
    btn_box.addWidget(b_reverse)
    btn_box.addStretch()
    layout.addLayout(btn_box)

    b_run = QPushButton(tm.get("btn_save_order"))
    b_run.setObjectName("actionBtn")
    b_run.clicked.connect(self.action_reorder)
    layout.addWidget(b_run)

    self.tabs.addTab(tab, f"🔀 {tm.get('tab_reorder')}")

def _load_pages_for_reorder(self, path):
    """페이지 목록 로드"""
    self.reorder_list.clear()
    if not path or not os.path.exists(path):
        return
    doc = None
    try:
        doc = fitz.open(path)
        for i in range(len(doc)):
            item = QListWidgetItem(tm.get("msg_page_num", i+1))
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.reorder_list.addItem(item)
    except Exception as e:
        QMessageBox.warning(self, tm.get("error"), tm.get("msg_page_load_failed", str(e)))
    finally:
        if doc:
            doc.close()

def _reverse_pages(self):
    """페이지 역순 정렬"""
    items = []
    while self.reorder_list.count() > 0:
        items.append(self.reorder_list.takeItem(0))
    for item in reversed(items):
        self.reorder_list.addItem(item)

def action_reorder(self):
    path = self.sel_reorder.get_path()
    if not path or self.reorder_list.count() == 0:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf_and_check_pages"))
    page_order = [self.reorder_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.reorder_list.count())]
    s, _ = self._choose_save_file(tm.get("save"), "reordered.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("reorder", file_path=path, output_path=s, page_order=page_order)
