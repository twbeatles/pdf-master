from PyQt6.QtWidgets import QFileDialog, QMessageBox

from ...core.i18n import tm


def action_split_adv(self):
    path = self.sel_split_adv.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    out_dir = self._choose_output_directory(tm.get("dlg_select_output_dir"))
    if out_dir:
        mode = self.cmb_split_mode.currentData() or "each"
        if mode == "range" and not self.inp_split_range.text().strip():
            return QMessageBox.warning(self, tm.get("info"), tm.get("msg_enter_page_range"))
        self.run_worker("split_by_pages", file_path=path, output_dir=out_dir, 
                      split_mode=mode, ranges=self.inp_split_range.text())

def action_stamp(self):
    path = self.sel_stamp.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    s, _ = self._choose_save_file(tm.get("save"), "stamped.pdf", "PDF (*.pdf)")
    if s:
        pos = self.cmb_stamp_pos.currentData() or "top-right"
        self.run_worker("add_stamp", file_path=path, output_path=s,
                      stamp_text=self.cmb_stamp.currentText(), position=pos)

def action_crop(self):
    path = self.sel_crop.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    s, _ = self._choose_save_file(tm.get("save"), "cropped.pdf", "PDF (*.pdf)")
    if s:
        margins = {
            'left': self.spn_crop_left.value(),
            'top': self.spn_crop_top.value(),
            'right': self.spn_crop_right.value(),
            'bottom': self.spn_crop_bottom.value()
        }
        self.run_worker("crop_pdf", file_path=path, output_path=s, margins=margins)

def action_blank_page(self):
    path = self.sel_blank.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    s, _ = self._choose_save_file(tm.get("save"), "with_blank.pdf", "PDF (*.pdf)")
    if s:
        pos = self.spn_blank_pos.value() - 1  # 0-indexed
        self.run_worker("insert_blank_page", file_path=path, output_path=s, position=pos)

def action_pdf_info(self):
    """PDF 정보 추출"""
    path = self.sel_info.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    s, _ = self._choose_save_file(tm.get("save"), "pdf_info.txt", "Text (*.txt)")
    if s:
        self.run_worker("get_pdf_info", file_path=path, output_path=s)

def action_duplicate_page(self):
    """페이지 복제"""
    path = self.sel_dup.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    s, _ = self._choose_save_file(tm.get("save"), "duplicated.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("duplicate_page", file_path=path, output_path=s,
                      page_num=self.spn_dup_page.value() - 1,  # 0-indexed
                      count=self.spn_dup_count.value())

def action_reverse_pages(self):
    """페이지 역순 정렬"""
    path = self.sel_rev.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    s, _ = self._choose_save_file(tm.get("save"), "reversed.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("reverse_pages", file_path=path, output_path=s)

def action_resize_pages(self):
    """페이지 크기 변경"""
    path = self.sel_resize.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    s, _ = self._choose_save_file(tm.get("save"), "resized.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("resize_pages", file_path=path, output_path=s,
                      target_size=self.cmb_resize.currentData() or self.cmb_resize.currentText())

def action_insert_signature(self):
    """전자 서명 삽입"""
    pdf_path = self.sel_sig_pdf.get_path()
    sig_path = self.sel_sig_img.get_path()

    if not pdf_path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    if not sig_path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_signature_image"))

    s, _ = self._choose_save_file(tm.get("save"), "signed.pdf", "PDF (*.pdf)")
    if s:
        raw_page = self.spn_sig_page.value()
        page_num = self._normalize_page_input(raw_page, last_page_value=0)
        self.run_worker("insert_signature", file_path=pdf_path, output_path=s,
                      signature_path=sig_path,
                      page_num=page_num,
                      position=self.cmb_sig_pos.currentData() or "bottom_right")

def action_add_freehand_signature(self):
    """프리핸드 서명 삽입"""
    path = self.sel_freehand_pdf.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))

    try:
        strokes = self._parse_freehand_strokes(self.txt_freehand_strokes.text())
    except ValueError as exc:
        return QMessageBox.warning(self, tm.get("warning"), str(exc))

    raw_page = self.spn_freehand_page.value()
    page_num = self._normalize_page_input(raw_page, last_page_value=0)
    width = self.spn_freehand_width.value()
    color = self.cmb_freehand_color.currentData() or (0, 0, 0)

    s, _ = self._choose_save_file(tm.get("save"), "with_freehand_signature.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker(
            "add_freehand_signature",
            file_path=path,
            output_path=s,
            page_num=page_num,
            strokes=strokes,
            color=color,
            width=width,
        )
