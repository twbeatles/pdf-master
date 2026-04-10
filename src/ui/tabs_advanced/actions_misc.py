from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QInputDialog, QLineEdit, QMessageBox

from ...core.i18n import tm


def action_detect_fields(self):
    """PDF 양식 필드 감지"""
    path = self.sel_form.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    self.form_fields_list.clear()
    self._form_field_data = {}
    self.run_worker("get_form_fields", file_path=path)

def _edit_form_field(self, item):
    """양식 필드 값 수정"""
    name = item.data(Qt.ItemDataRole.UserRole)
    current_value = self._form_field_data.get(name, "")

    new_value, ok = QInputDialog.getText(self, tm.get("dlg_edit_field"), tm.get("msg_edit_field_value", name),
                                         QLineEdit.EchoMode.Normal, current_value)
    if ok:
        self._form_field_data[name] = new_value
        item.setText(f"📋 {name}: {new_value}")

def action_fill_form(self):
    """양식 작성 저장"""
    path = self.sel_form.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    if not hasattr(self, '_form_field_data') or not self._form_field_data:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_detect_fields_first"))

    s, _ = self._choose_save_file(tm.get("save"), "filled_form.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("fill_form", file_path=path, output_path=s, 
                      field_values=self._form_field_data)

def action_compare_pdfs(self):
    """PDF 비교"""
    path1 = self.sel_compare1.get_path()
    path2 = self.sel_compare2.get_path()
    generate_visual_diff = self.chk_compare_visual.isChecked() if hasattr(self, "chk_compare_visual") else False

    if not path1 or not path2:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_two_pdf"))

    s, _ = self._choose_save_file(tm.get("dlg_save_compare"), "comparison.txt", "Text (*.txt)")
    if s:
        self.run_worker(
            "compare_pdfs",
            file_path1=path1,
            file_path2=path2,
            output_path=s,
            generate_visual_diff=generate_visual_diff,
        )

def action_decrypt_pdf(self):
    """PDF 복호화"""
    path = self.sel_decrypt.get_path()
    password = self.inp_decrypt_pw.text()

    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    if not password:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_enter_password"))

    s, _ = self._choose_save_file(tm.get("save"), "decrypted.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("decrypt_pdf", file_path=path, output_path=s, password=password)

def action_list_attachments(self):
    """첨부 파일 목록"""
    path = self.sel_attach.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    self.run_worker("list_attachments", file_path=path)

def action_add_attachment(self):
    """파일 첨부"""
    pdf_path = self.sel_attach.get_path()
    if not pdf_path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))

    attach_path, _ = QFileDialog.getOpenFileName(self, tm.get("dlg_select_attach_file"), "", tm.get("file_filter_all"))
    if not attach_path:
        return

    s, _ = self._choose_save_file(tm.get("save"), "with_attachment.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("add_attachment", file_path=pdf_path, output_path=s, attach_path=attach_path)

def action_extract_attachments(self):
    """첨부 파일 추출"""
    path = self.sel_attach.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))

    out_dir = self._choose_output_directory(tm.get("dlg_select_attachment_output_dir"))
    if out_dir:
        self.run_worker("extract_attachments", file_path=path, output_dir=out_dir)

def action_copy_pages(self):
    """다른 PDF에서 페이지 복사"""
    target_path = self.sel_copy_target.get_path()
    source_path = self.sel_copy_source.get_path()
    page_range = self.txt_copy_pages.text().strip()

    if not target_path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_target_pdf"))
    if not source_path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_source_pdf"))
    if not page_range:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_enter_copy_pages"))

    insert_pos = self.spn_copy_insert.value()

    s, _ = self._choose_save_file(tm.get("save"), "merged.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("copy_page_between_docs", file_path=target_path, output_path=s,
                      source_path=source_path, page_range=page_range, insert_at=insert_pos)

def action_replace_page(self):
    """대상 PDF 페이지를 소스 PDF 페이지로 교체"""
    target_path = self.sel_replace_target.get_path()
    source_path = self.sel_replace_source.get_path()

    if not target_path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_target_pdf"))
    if not source_path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_source_pdf"))

    target_page = self.spn_replace_target_page.value()
    source_page = self.spn_replace_source_page.value()
    s, _ = self._choose_save_file(tm.get("save"), "replaced_page.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker(
            "replace_page",
            file_path=target_path,
            replace_path=source_path,
            target_page=target_page,
            source_page=source_page,
            output_path=s,
        )

def action_set_bookmarks(self):
    """북마크(목차) 설정"""
    path = self.sel_set_bookmarks.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))

    try:
        bookmarks = self._parse_bookmark_lines(self.txt_set_bookmarks.toPlainText())
    except ValueError as exc:
        return QMessageBox.warning(self, tm.get("warning"), str(exc))

    s, _ = self._choose_save_file(tm.get("save"), "bookmarks_set.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker(
            "set_bookmarks",
            file_path=path,
            output_path=s,
            bookmarks=bookmarks,
        )

def action_image_watermark(self):
    """이미지 워터마크 적용"""
    pdf_path = self.sel_img_wm_pdf.get_path()
    img_path = self.sel_img_wm_img.get_path()

    if not pdf_path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    if not img_path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_image_file"))

    position = self.cmb_img_wm_pos.currentData() or "center"
    scale = self.spn_img_wm_scale.value() / 100.0
    opacity = self.spn_img_wm_opacity.value() / 100.0

    s, _ = self._choose_save_file(tm.get("save"), "with_image_watermark.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("image_watermark", file_path=pdf_path, output_path=s,
                      image_path=img_path, position=position,
                      scale=scale, opacity=opacity)
