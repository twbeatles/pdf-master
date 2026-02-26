from PyQt6.QtWidgets import QFileDialog, QMessageBox

from ...core.i18n import tm


def action_highlight_text(self):
    """텍스트 하이라이트"""
    path = self.sel_search.get_path()
    term = self.inp_search.text().strip()

    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    if not term:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_enter_keyword"))

    s, _ = QFileDialog.getSaveFileName(self, tm.get("save"), "highlighted.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("highlight_text", file_path=path, output_path=s, search_term=term)

def action_list_annotations(self):
    """주석 목록 추출"""
    path = self.sel_annot.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    s, _ = QFileDialog.getSaveFileName(self, tm.get("save"), "annotations.txt", "Text (*.txt)")
    if s:
        self.run_worker("list_annotations", file_path=path, output_path=s)

def action_remove_annotations(self):
    """모든 주석 삭제"""
    path = self.sel_annot.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))

    reply = QMessageBox.question(self, tm.get("confirm"), 
                                tm.get("msg_confirm_remove_annotations"),
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    if reply != QMessageBox.StandardButton.Yes:
        return

    s, _ = QFileDialog.getSaveFileName(self, tm.get("save"), "no_annotations.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("remove_annotations", file_path=path, output_path=s)

def action_redact_text(self):
    """텍스트 교정 (영구 삭제)"""
    path = self.sel_redact.get_path()
    term = self.inp_redact.text().strip()

    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    if not term:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_enter_redact_text"))

    reply = QMessageBox.warning(self, tm.get("warning"), 
                               tm.get("msg_confirm_redact").format(term),
                               QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    if reply != QMessageBox.StandardButton.Yes:
        return

    s, _ = QFileDialog.getSaveFileName(self, tm.get("save"), "redacted.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("redact_text", file_path=path, output_path=s, search_term=term)

def action_add_text_markup(self):
    """텍스트 마크업 추가"""
    path = self.sel_markup.get_path()
    term = self.inp_markup.text().strip()

    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    if not term:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_enter_markup_text"))

    markup_type = self.cmb_markup.currentData() or "underline"

    s, _ = QFileDialog.getSaveFileName(self, tm.get("save"), "marked_up.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("add_text_markup", file_path=path, output_path=s, 
                      search_term=term, markup_type=markup_type)

def action_add_background(self):
    """배경색 추가"""
    path = self.sel_bg.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))

    color = self.cmb_bg_color.currentData() or [1, 1, 0.9]

    s, _ = QFileDialog.getSaveFileName(self, tm.get("save"), "with_background.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("add_background", file_path=path, output_path=s, color=color)

def action_add_sticky_note(self):
    """스티키 노트 추가"""
    path = self.sel_sticky.get_path()
    content = self.txt_sticky_content.text().strip()

    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    if not content:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_enter_note_content"))

    x = self.spn_sticky_x.value()
    y = self.spn_sticky_y.value()
    page_num = self.spn_sticky_page.value() - 1
    icon = self.cmb_sticky_icon.currentText()

    s, _ = QFileDialog.getSaveFileName(self, tm.get("save"), "with_note.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("add_sticky_note", file_path=path, output_path=s,
                      page_num=page_num, x=x, y=y, content=content, icon=icon)

def action_add_ink_annotation(self):
    """프리핸드 드로잉 추가"""
    path = self.sel_ink.get_path()
    points_text = self.txt_ink_points.text().strip()

    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    if not points_text:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_enter_coords"))

    # 좌표 파싱
    try:
        points = []
        for pt in points_text.split(";"):
            coords = pt.strip().split(",")
            if len(coords) >= 2:
                points.append([float(coords[0]), float(coords[1])])

        if len(points) < 2:
            return QMessageBox.warning(self, tm.get("info"), tm.get("msg_min_two_points"))
    except Exception as e:
        return QMessageBox.warning(self, tm.get("error"), tm.get("msg_coord_format_error", str(e)))

    page_num = self.spn_ink_page.value() - 1
    width = self.spn_ink_width.value()

    color = self.cmb_ink_color.currentData() or (0, 0, 1)

    s, _ = QFileDialog.getSaveFileName(self, tm.get("save"), "with_drawing.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("add_ink_annotation", file_path=path, output_path=s,
                      page_num=page_num, points=points, color=color, width=width)

def action_draw_shape(self):
    """도형 그리기"""
    path = self.sel_shape.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))

    shape_type = self.cmb_shape_type.currentData() or "rect"

    page_num = self.spn_shape_page.value() - 1
    x = self.spn_shape_x.value()
    y = self.spn_shape_y.value()
    w = self.spn_shape_w.value()
    h = self.spn_shape_h.value()

    line_color = self.cmb_shape_line_color.currentData() or (0, 0, 1)

    fill_color = self.cmb_shape_fill_color.currentData()

    s, _ = QFileDialog.getSaveFileName(self, tm.get("save"), "with_shape.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("draw_shapes", file_path=path, output_path=s,
                      page_num=page_num, shape_type=shape_type,
                      x=x, y=y, width=w, height=h,
                      line_color=line_color, fill_color=fill_color)

def action_add_hyperlink(self):
    """하이퍼링크 추가"""
    path = self.sel_link.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))

    link_mode = self.cmb_link_type.currentData() or "url"
    is_url = link_mode == "url"
    page_num = self.spn_link_page.value() - 1

    if is_url:
        url = self.txt_link_url.text().strip()
        if not url:
            return QMessageBox.warning(self, tm.get("info"), tm.get("msg_enter_url"))
        target = url
        link_type = "url"
    else:
        # v4.5.3: Worker goto target은 0-based만 수용하므로 UI에서 정규화
        target_page = self.spn_link_target.value() - 1
        target = target_page
        link_type = "page"

    area_text = self.txt_link_area.text().strip()
    if not area_text:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_enter_link_area"))

    try:
        coords = [float(x.strip()) for x in area_text.split(",")]
        if len(coords) != 4:
            raise ValueError(tm.get("msg_need_four_coords"))
        rect = coords
    except Exception as e:
        return QMessageBox.warning(self, tm.get("error"), tm.get("msg_coord_format_error", str(e)))

    s, _ = QFileDialog.getSaveFileName(self, tm.get("save"), "with_link.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("add_link", file_path=path, output_path=s,
                      page_num=page_num, link_type=link_type,
                      target=target, rect=rect)

def action_insert_textbox(self):
    """텍스트 상자 삽입"""
    path = self.sel_textbox.get_path()
    text = self.txt_textbox_content.text().strip()

    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    if not text:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_enter_text"))

    page_num = self.spn_tb_page.value() - 1
    x = self.spn_tb_x.value()
    y = self.spn_tb_y.value()
    fontsize = self.spn_tb_fontsize.value()

    color = self.cmb_tb_color.currentData() or (0, 0, 0)

    s, _ = QFileDialog.getSaveFileName(self, tm.get("save"), "with_textbox.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("insert_textbox", file_path=path, output_path=s,
                      page_num=page_num, x=x, y=y, text=text,
                      fontsize=fontsize, color=color)

def action_add_annotation_basic(self):
    """기본 주석 추가(text/freetext)"""
    path = self.sel_add_annot.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))

    text = self.txt_add_annot_text.text().strip()
    if not text:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_enter_note_content"))

    annot_type = self.cmb_add_annot_type.currentData() or "text"
    page_num = self.spn_add_annot_page.value() - 1
    point = [100, 100]
    rect = [100, 100, 300, 150]

    try:
        if annot_type == "text":
            point_tokens = [p.strip() for p in self.txt_add_annot_point.text().strip().split(",") if p.strip()]
            if len(point_tokens) != 2:
                raise ValueError(tm.get("msg_need_two_coords"))
            point = [float(point_tokens[0]), float(point_tokens[1])]
        else:
            rect_tokens = [p.strip() for p in self.txt_add_annot_rect.text().strip().split(",") if p.strip()]
            if len(rect_tokens) != 4:
                raise ValueError(tm.get("msg_need_four_coords"))
            rect = [float(rect_tokens[0]), float(rect_tokens[1]), float(rect_tokens[2]), float(rect_tokens[3])]
    except ValueError as exc:
        return QMessageBox.warning(self, tm.get("error"), tm.get("msg_coord_format_error", str(exc)))

    s, _ = QFileDialog.getSaveFileName(self, tm.get("save"), "with_annotation.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker(
            "add_annotation",
            file_path=path,
            output_path=s,
            page_num=page_num,
            annot_type=annot_type,
            text=text,
            point=point,
            rect=rect,
        )
