from . import deps

def action_draw_shape(self):
    """도형 그리기"""
    path = self.sel_shape.get_path()
    if not path:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("msg_select_pdf"))

    shape_type = self.cmb_shape_type.currentData() or "rect"

    page_num = self.spn_shape_page.value() - 1
    x = self.spn_shape_x.value()
    y = self.spn_shape_y.value()
    w = self.spn_shape_w.value()
    h = self.spn_shape_h.value()

    line_color = self.cmb_shape_line_color.currentData() or (0, 0, 1)

    fill_color = self.cmb_shape_fill_color.currentData()

    s, _ = self._choose_save_file(deps.tm.get("save"), "with_shape.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("draw_shapes", file_path=path, output_path=s,
                      page_num=page_num, shape_type=shape_type,
                      x=x, y=y, width=w, height=h,
                      line_color=line_color, fill_color=fill_color)

def action_add_hyperlink(self):
    """하이퍼링크 추가"""
    path = self.sel_link.get_path()
    if not path:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("msg_select_pdf"))

    link_mode = self.cmb_link_type.currentData() or "url"
    is_url = link_mode == "url"
    page_num = self.spn_link_page.value() - 1

    if is_url:
        url = self.txt_link_url.text().strip()
        if not url:
            return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("msg_enter_url"))
        target = url
        link_type = "url"
    else:
        # v4.5.3: Worker goto target은 0-based만 수용하므로 UI에서 정규화
        target_page = self.spn_link_target.value() - 1
        target = target_page
        link_type = "page"

    area_text = self.txt_link_area.text().strip()
    if not area_text:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("msg_enter_link_area"))

    try:
        coords = [float(x.strip()) for x in area_text.split(",")]
        if len(coords) != 4:
            raise ValueError(deps.tm.get("msg_need_four_coords"))
        rect = coords
    except Exception as e:
        return deps.QMessageBox.warning(self, deps.tm.get("error"), deps.tm.get("msg_coord_format_error", str(e)))

    s, _ = self._choose_save_file(deps.tm.get("save"), "with_link.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("add_link", file_path=path, output_path=s,
                      page_num=page_num, link_type=link_type,
                      target=target, rect=rect)
