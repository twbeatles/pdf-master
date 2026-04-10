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
from ..thumbnail_grid import ThumbnailGridWidget
from ..widgets import FileListWidget, FileSelectorWidget, ImageListWidget, ToastWidget

logger = logging.getLogger(__name__)


def _ensure_preview_ready(self, path):
    ensure_preview_access = getattr(self, "_ensure_preview_access", None)
    if callable(ensure_preview_access):
        result = ensure_preview_access(path)
        if result is None:
            self._update_preview(path)
            return True, None
        if isinstance(result, tuple):
            return bool(result[0]), result[1] if len(result) > 1 else None
        return bool(result), None

    self._update_preview(path)
    return True, None

def setup_page_tab(self):
    tab = QWidget()
    layout = QVBoxLayout(tab)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    content = QWidget()
    content_layout = QVBoxLayout(content)

    # 🔢 페이지 번호 삽입 (최상단)
    grp_pn = QGroupBox(tm.get("grp_page_number"))
    l_pn = QVBoxLayout(grp_pn)
    self.sel_pn = FileSelectorWidget()
    self.sel_pn.pathChanged.connect(self._update_preview)
    l_pn.addWidget(self.sel_pn)
    guide_pn = QLabel(tm.get("guide_page_format"))
    guide_pn.setObjectName("desc")
    l_pn.addWidget(guide_pn)
    opt_pn = QHBoxLayout()
    opt_pn.addWidget(QLabel(tm.get("lbl_position")))
    self.cmb_pn_pos = QComboBox()
    pn_positions = [
        (tm.get("pos_bottom_center"), "bottom"),
        (tm.get("pos_top_center"), "top"),
        (tm.get("pos_bottom_left"), "bottom-left"),
        (tm.get("pos_bottom_right"), "bottom-right"),
        (tm.get("pos_top_left"), "top-left"),
        (tm.get("pos_top_right"), "top-right"),
    ]
    for label, value in pn_positions:
        self.cmb_pn_pos.addItem(label, value)
    self.cmb_pn_pos.setToolTip(tm.get("tooltip_page_number_pos"))
    opt_pn.addWidget(self.cmb_pn_pos)
    opt_pn.addWidget(QLabel(tm.get("lbl_format")))
    self.cmb_pn_format = QComboBox()
    self.cmb_pn_format.addItems(["{n} / {total}", "Page {n} of {total}", "- {n} -", "{n}", tm.get("format_page_local")])
    self.cmb_pn_format.setEditable(True)
    opt_pn.addWidget(self.cmb_pn_format)
    l_pn.addLayout(opt_pn)
    b_pn = QPushButton(tm.get("btn_insert_page_number"))
    b_pn.clicked.connect(self.action_page_numbers)
    l_pn.addWidget(b_pn)
    content_layout.addWidget(grp_pn)

    # 추출
    grp_split = QGroupBox(tm.get("grp_split_page"))
    l_s = QVBoxLayout(grp_split)
    self.sel_split = FileSelectorWidget()
    self.sel_split.pathChanged.connect(self._update_preview)
    l_s.addWidget(self.sel_split)
    h = QHBoxLayout()
    h.addWidget(QLabel(tm.get("lbl_split_range")))
    self.inp_range = QLineEdit()
    self.inp_range.setPlaceholderText("1, 3-5, 8")
    h.addWidget(self.inp_range)
    l_s.addLayout(h)
    b_s = QPushButton(tm.get("btn_split_run"))
    b_s.clicked.connect(self.action_split)
    l_s.addWidget(b_s)
    content_layout.addWidget(grp_split)

    # 삭제
    grp_del = QGroupBox(tm.get("grp_delete_page"))
    l_d = QVBoxLayout(grp_del)
    self.sel_del = FileSelectorWidget()
    self.sel_del.pathChanged.connect(self._update_preview)
    l_d.addWidget(self.sel_del)
    h2 = QHBoxLayout()
    h2.addWidget(QLabel(tm.get("lbl_delete_range")))
    self.inp_del_range = QLineEdit()
    self.inp_del_range.setPlaceholderText("2, 4-6")
    h2.addWidget(self.inp_del_range)
    l_d.addLayout(h2)
    b_d = QPushButton(tm.get("btn_delete_run"))
    b_d.clicked.connect(self.action_delete_pages)
    l_d.addWidget(b_d)
    content_layout.addWidget(grp_del)

    # 회전
    grp_rot = QGroupBox(tm.get("grp_rotate_page"))
    l_r = QVBoxLayout(grp_rot)
    self.sel_rot = FileSelectorWidget()
    self.sel_rot.pathChanged.connect(self._on_rotate_pdf_changed)
    l_r.addWidget(self.sel_rot)
    h3 = QHBoxLayout()
    h3.addWidget(QLabel(tm.get("lbl_rotate_target")))
    self.cmb_rot_target = QComboBox()
    self.cmb_rot_target.addItem(tm.get("rotate_target_all"), "all")
    self.cmb_rot_target.addItem(tm.get("rotate_target_selected"), "selected")
    h3.addWidget(self.cmb_rot_target)
    h3.addWidget(QLabel(tm.get("lbl_rotate_angle")))
    self.cmb_rot = QComboBox()
    rotate_options = [
        (tm.get("combo_rotate_90"), 90),
        (tm.get("combo_rotate_180"), 180),
        (tm.get("combo_rotate_270"), 270),
    ]
    for label, value in rotate_options:
        self.cmb_rot.addItem(label, value)
    h3.addWidget(self.cmb_rot)
    h3.addStretch()
    l_r.addLayout(h3)
    self.lbl_rot_selection_help = QLabel(tm.get("guide_rotate_selection"))
    self.lbl_rot_selection_help.setObjectName("desc")
    self.lbl_rot_selection_help.setWordWrap(True)
    l_r.addWidget(self.lbl_rot_selection_help)
    self.rot_thumb_grid = ThumbnailGridWidget(selection_mode="extended")
    self.rot_thumb_grid.setMinimumHeight(320)
    self.rot_thumb_grid.pageSelected.connect(self._on_rotate_thumbnail_page_selected)
    l_r.addWidget(self.rot_thumb_grid)
    b_r = QPushButton(tm.get("btn_rotate_run"))
    b_r.clicked.connect(self.action_rotate)
    l_r.addWidget(b_r)
    content_layout.addWidget(grp_rot)

    content_layout.addStretch()
    scroll.setWidget(content)
    layout.addWidget(scroll)
    self.tabs.addTab(tab, f"✂️ {tm.get('tab_page')}")

def action_split(self):
    path = self.sel_split.get_path()
    rng = self.inp_range.text()
    if not path or not rng:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_file_and_range_required"))
    d = self._choose_output_directory(tm.get("dlg_select_output_dir"))
    if d:
        self.run_worker("split", file_path=path, output_dir=d, page_range=rng)

def action_delete_pages(self):
    path = self.sel_del.get_path()
    rng = self.inp_del_range.text()
    if not path or not rng:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_file_and_delete_range_required"))
    s, _ = self._choose_save_file(tm.get("save"), "deleted.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("delete_pages", file_path=path, output_path=s, page_range=rng)

def action_rotate(self):
    path = self.sel_rot.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_file"))
    angle = self.cmb_rot.currentData()
    if angle is None:
        angle = 90
    page_indices = None
    if getattr(self, "cmb_rot_target", None) is not None and self.cmb_rot_target.currentData() == "selected":
        page_indices = self.rot_thumb_grid.get_selected_pages() if hasattr(self, "rot_thumb_grid") else []
        if not page_indices:
            return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_rotate_pages"))
    s, _ = self._choose_save_file(tm.get("save"), "rotated.pdf", "PDF (*.pdf)")
    if s:
        kwargs = {
            "file_path": path,
            "output_path": s,
            "angle": angle,
        }
        if page_indices is not None:
            kwargs["page_indices"] = page_indices
        self.run_worker("rotate", **kwargs)

def _on_rotate_pdf_changed(self, path):
    if not hasattr(self, "rot_thumb_grid"):
        return
    if not path or not os.path.exists(path):
        self.rot_thumb_grid.clear()
        return
    ready, password = _ensure_preview_ready(self, path)
    if not ready:
        self.rot_thumb_grid.show_status_message(self.preview_label.text())
        return
    self.rot_thumb_grid.load_pdf(path, password=password)
    self.rot_thumb_grid.set_active_page(getattr(self, "_current_preview_page", 0), emit_signal=False)

def _on_rotate_thumbnail_page_selected(self, page_index: int):
    path = self.sel_rot.get_path() if hasattr(self, "sel_rot") else ""
    if not path or not os.path.exists(path):
        return
    ready, _password = _ensure_preview_ready(self, path)
    if not ready:
        return
    self._current_preview_page = page_index
    self._render_preview_page()
    if hasattr(self, "status_label"):
        self.status_label.setText(tm.get("status_page_sel").format(page_index + 1))

def _sync_rotate_thumbnail_with_preview(self):
    if not hasattr(self, "rot_thumb_grid") or not hasattr(self, "sel_rot"):
        return
    rotate_path = self.sel_rot.get_path()
    preview_path = getattr(self, "_current_preview_path", "")
    if not rotate_path or not preview_path:
        return
    if os.path.abspath(rotate_path) != os.path.abspath(preview_path):
        return
    self.rot_thumb_grid.set_active_page(getattr(self, "_current_preview_page", 0), emit_signal=False)

def action_page_numbers(self):
    """페이지 번호 삽입 실행"""
    path = self.sel_pn.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))

    position = self.cmb_pn_pos.currentData() or "bottom"
    format_str = self.cmb_pn_format.currentText()

    s, _ = self._choose_save_file(tm.get("save"), "numbered.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("add_page_numbers", file_path=path, output_path=s,
                      position=position, format=format_str)
