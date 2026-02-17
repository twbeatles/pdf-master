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

from ..core.i18n import tm
from ..core.settings import save_settings
from .widgets import FileListWidget, FileSelectorWidget, ImageListWidget, ToastWidget

logger = logging.getLogger(__name__)


class MainWindowTabsBasicMixin:

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
        self.merge_list.model().rowsInserted.connect(self._update_merge_count)
        self.merge_list.model().rowsRemoved.connect(self._update_merge_count)
        
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
        save, _ = QFileDialog.getSaveFileName(self, tm.get("save"), "merged.pdf", "PDF (*.pdf)")
        if save:
            self.run_worker("merge", files=files, output_path=save)

    # ===================== Tab 2: 변환 =====================

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
        self.cmb_fmt.addItems(["png", "jpg"])
        opt.addWidget(self.cmb_fmt)
        opt.addWidget(QLabel(tm.get("lbl_dpi")))
        self.spn_dpi = QSpinBox()
        self.spn_dpi.setRange(72, 600)
        self.spn_dpi.setValue(150)
        opt.addWidget(self.spn_dpi)
        
        # 프리셋 버튼
        btn_save_preset = QPushButton("💾")
        btn_save_preset.setToolTip("현재 설정을 프리셋으로 저장")
        btn_save_preset.setFixedWidth(36)
        btn_save_preset.clicked.connect(self._save_convert_preset)
        opt.addWidget(btn_save_preset)
        
        btn_load_preset = QPushButton("📂")
        btn_load_preset.setToolTip("저장된 프리셋 불러오기")
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
        files, _ = QFileDialog.getOpenFileNames(self, tm.get("dlg_title_img"), "", "이미지 (*.png *.jpg *.jpeg *.bmp *.gif *.webp)")
        for f in files:
            item = QListWidgetItem(f"🖼️ {os.path.basename(f)}")
            item.setData(Qt.ItemDataRole.UserRole, f)
            item.setToolTip(f)
            self.img_list.addItem(item)

    def _add_pdf_for_img(self):
        """이미지 변환용 PDF 추가"""
        files, _ = QFileDialog.getOpenFileNames(self, "PDF 선택", "", "PDF (*.pdf)")
        for f in files:
            self.img_conv_list.add_file(f)

    def _add_pdf_for_txt(self):
        """텍스트 추출용 PDF 추가"""
        files, _ = QFileDialog.getOpenFileNames(self, "PDF 선택", "", "PDF (*.pdf)")
        for f in files:
            self.txt_conv_list.add_file(f)

    def _save_convert_preset(self):
        """변환 설정 프리셋 저장"""
        name, ok = QInputDialog.getText(self, "프리셋 저장", "프리셋 이름:")
        if ok and name:
            presets = self.settings.get("convert_presets", {})
            presets[name] = {
                "format": self.cmb_fmt.currentText(),
                "dpi": self.spn_dpi.value()
            }
            self.settings["convert_presets"] = presets
            save_settings(self.settings)
            toast = ToastWidget(f"프리셋 '{name}' 저장됨", toast_type='success', duration=2000)
            toast.show_toast(self)

    def _load_convert_preset(self):
        """변환 설정 프리셋 불러오기"""
        presets = self.settings.get("convert_presets", {})
        if not presets:
            QMessageBox.information(self, "프리셋", "저장된 프리셋이 없습니다.")
            return
        
        # 프리셋 선택 다이얼로그
        name, ok = QInputDialog.getItem(self, "프리셋 불러오기", "프리셋 선택:", 
                                        list(presets.keys()), 0, False)
        if ok and name:
            preset = presets[name]
            idx = self.cmb_fmt.findText(preset.get("format", "png"))
            if idx >= 0:
                self.cmb_fmt.setCurrentIndex(idx)
            self.spn_dpi.setValue(preset.get("dpi", 150))
            toast = ToastWidget(f"프리셋 '{name}' 적용됨", toast_type='info', duration=2000)
            toast.show_toast(self)

    def action_img(self):
        paths = self.img_conv_list.get_all_paths()
        if not paths:
            return QMessageBox.warning(self, "알림", "PDF 파일을 추가하세요.")
        d = QFileDialog.getExistingDirectory(self, "저장 폴더 선택")
        if d:
            self.run_worker("convert_to_img", file_paths=paths, output_dir=d, 
                          fmt=self.cmb_fmt.currentText(), dpi=self.spn_dpi.value())

    def action_img_to_pdf(self):
        files = self.img_list.get_all_paths()
        if not files:
            return QMessageBox.warning(self, "알림", "이미지 파일을 추가하세요.")
        save, _ = QFileDialog.getSaveFileName(self, "저장", "images.pdf", "PDF (*.pdf)")
        if save:
            self.run_worker("images_to_pdf", files=files, output_path=save)

    def action_txt(self):
        paths = self.txt_conv_list.get_all_paths()
        if not paths:
            return QMessageBox.warning(self, "알림", "PDF 파일을 추가하세요.")
        d = QFileDialog.getExistingDirectory(self, "저장 폴더 선택")
        if d:
            self.run_worker("extract_text", file_paths=paths, output_dir=d)

    # ===================== Tab 3: 페이지 =====================

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
        self.cmb_pn_pos.setToolTip("페이지 번호 위치 선택") 
        opt_pn.addWidget(self.cmb_pn_pos)
        opt_pn.addWidget(QLabel(tm.get("lbl_format")))
        self.cmb_pn_format = QComboBox()
        self.cmb_pn_format.addItems(["{n} / {total}", "Page {n} of {total}", "- {n} -", "{n}", "페이지 {n}"])
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
        self.sel_rot.pathChanged.connect(self._update_preview)
        l_r.addWidget(self.sel_rot)
        h3 = QHBoxLayout()
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
            return QMessageBox.warning(self, "알림", "파일과 페이지 범위를 입력하세요.")
        d = QFileDialog.getExistingDirectory(self, "저장 폴더")
        if d:
            self.run_worker("split", file_path=path, output_dir=d, page_range=rng)

    def action_delete_pages(self):
        path = self.sel_del.get_path()
        rng = self.inp_del_range.text()
        if not path or not rng:
            return QMessageBox.warning(self, "알림", "파일과 삭제할 페이지를 입력하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "deleted.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("delete_pages", file_path=path, output_path=s, page_range=rng)

    def action_rotate(self):
        path = self.sel_rot.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "파일을 선택하세요.")
        angle = self.cmb_rot.currentData()
        if angle is None:
            angle = 90
        s, _ = QFileDialog.getSaveFileName(self, "저장", "rotated.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("rotate", file_path=path, output_path=s, angle=angle)

    def action_page_numbers(self):
        """페이지 번호 삽입 실행"""
        path = self.sel_pn.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "PDF 파일을 선택하세요.")
        
        position = self.cmb_pn_pos.currentData() or "bottom"
        format_str = self.cmb_pn_format.currentText()
        
        s, _ = QFileDialog.getSaveFileName(self, "저장", "numbered.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("add_page_numbers", file_path=path, output_path=s,
                          position=position, format=format_str)

    # ===================== Tab 4: 편집/보안 =====================

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
            m = doc.metadata
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
            return QMessageBox.warning(self, "알림", "파일을 선택하세요.")
        meta = {'title': self.inp_title.text(), 'author': self.inp_author.text(), 'subject': self.inp_subj.text()}
        s, _ = QFileDialog.getSaveFileName(self, "저장", "metadata_updated.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("metadata_update", file_path=path, output_path=s, metadata=meta)

    def action_watermark(self):
        path = self.sel_wm.get_path()
        text = self.inp_wm.text()
        if not path or not text:
            return QMessageBox.warning(self, "알림", "파일과 텍스트를 입력하세요.")
        color = self.cmb_wm_color.currentData() or (0.5, 0.5, 0.5)
        s, _ = QFileDialog.getSaveFileName(self, "저장", "watermarked.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("watermark", file_path=path, output_path=s, text=text, color=color)

    def action_protect(self):
        path = self.sel_sec.get_path()
        pw = self.inp_pw.text()
        if not path or not pw:
            return QMessageBox.warning(self, "알림", "파일과 비밀번호를 입력하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "encrypted.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("protect", file_path=path, output_path=s, password=pw)

    def action_unlock(self):
        path = self.sel_sec.get_path()
        pw = self.inp_pw.text()
        
        if not path:
            return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
            
        if not pw:
             return QMessageBox.warning(self, tm.get("info"), tm.get("err_password_required"))
             
        s, _ = QFileDialog.getSaveFileName(self, tm.get("save"), "decrypted.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("decrypt_pdf", file_path=path, output_path=s, password=pw)

    def action_compress(self):
        path = self.sel_sec.get_path()
        if not path:
            return QMessageBox.warning(self, "알림", "파일을 선택하세요.")
        s, _ = QFileDialog.getSaveFileName(self, "저장", "compressed.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("compress", file_path=path, output_path=s)

    # ===================== Tab 5: 페이지 순서 변경 =====================

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
            QMessageBox.warning(self, "오류", f"페이지 로드 실패: {e}")
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
            return QMessageBox.warning(self, "알림", "PDF를 선택하고 페이지를 확인하세요.")
        page_order = [self.reorder_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.reorder_list.count())]
        s, _ = QFileDialog.getSaveFileName(self, "저장", "reordered.pdf", "PDF (*.pdf)")
        if s:
            self.run_worker("reorder", file_path=path, output_path=s, page_order=page_order)

    # ===================== Tab 6: 일괄 처리 =====================

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
        files, _ = QFileDialog.getOpenFileNames(self, "PDF 선택", "", "PDF (*.pdf)")
        for f in files:
            item = QListWidgetItem(f"📄 {os.path.basename(f)}")
            item.setData(Qt.ItemDataRole.UserRole, f)
            item.setToolTip(f)
            self.batch_list.addItem(item)

    def _batch_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "폴더 선택")
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
            return QMessageBox.warning(self, "알림", "PDF 파일을 추가하세요.")
        out_dir = QFileDialog.getExistingDirectory(self, "출력 폴더 선택")
        if not out_dir:
            return
        op = self.cmb_batch_op.currentData() or self.cmb_batch_op.currentText()
        opt = self.inp_batch_opt.text()
        if op in ("watermark", "encrypt") and not opt:
            return QMessageBox.warning(self, "알림", tm.get("ph_batch_option"))
        self.run_worker("batch", files=files, output_dir=out_dir, operation=op, option=opt)

    # ===================== Tab 7: 고급 기능 =====================
