from PyQt6.QtWidgets import QFileDialog, QMessageBox

from ...core.i18n import tm
from ..widgets import ToastWidget


def action_highlight_text(self):
    """텍스트 하이라이트"""
    path = self.sel_search.get_path()
    term = self.inp_search.text().strip()

    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    if not term:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_enter_keyword"))

    s, _ = self._choose_save_file(tm.get("save"), "highlighted.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("highlight_text", file_path=path, output_path=s, search_term=term)

def action_list_annotations(self):
    """주석 목록 추출"""
    path = self.sel_annot.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    s, _ = self._choose_save_file(tm.get("save"), "annotations.txt", "Text (*.txt)")
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

    s, _ = self._choose_save_file(tm.get("save"), "no_annotations.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("remove_annotations", file_path=path, output_path=s)

def action_start_redact_region_select(self):
    """미리보기에서 드래그로 교정 영역을 선택한다."""
    path = self.sel_redact.get_path() if hasattr(self, "sel_redact") else ""
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))

    preview = getattr(self, "preview_image", None)
    if preview is None or not hasattr(preview, "set_region_select_mode"):
        return QMessageBox.warning(self, tm.get("warning"), tm.get("err_redact_drag_preview_unavailable"))

    # 미리보기를 교정 대상 PDF로 동기화
    ensure = getattr(self, "_ensure_preview_access", None)
    ready = False
    if callable(ensure):
        result = ensure(path)
        if isinstance(result, tuple) and len(result) >= 1:
            ready = bool(result[0])
        else:
            ready = bool(result)
        if not ready:
            update = getattr(self, "_update_preview", None)
            if callable(update):
                update(path)
            if getattr(self, "_current_preview_doc", None) is None:
                return QMessageBox.warning(
                    self, tm.get("warning"), tm.get("err_redact_drag_preview_unavailable")
                )
    else:
        update = getattr(self, "_update_preview", None)
        if callable(update):
            update(path)

    # 시그널 지연 연결 (탭 빌드 시 preview가 아직 없을 수 있음)
    if not getattr(self, "_redact_region_signal_connected", False):
        try:
            preview.regionSelected.connect(self._on_preview_region_selected_for_redact)
            preview.regionSelectModeChanged.connect(self._on_redact_region_mode_changed)
            self._redact_region_signal_connected = True
        except Exception:
            pass

    # 토글: 이미 선택 모드면 취소
    if preview.is_region_select_mode():
        preview.set_region_select_mode(False)
        self._region_select_target = None
        return None

    self._region_select_target = "redact"
    preview.set_region_select_mode(True)
    if hasattr(self, "lbl_redact_drag_hint"):
        self.lbl_redact_drag_hint.setText(tm.get("hint_redact_drag_active"))
    ToastWidget(tm.get("msg_redact_drag_started"), toast_type="info", duration=2500).show_toast(self)
    return None


def _on_preview_region_selected_for_redact(self, page: int, x0: float, y0: float, x1: float, y1: float):
    """미리보기 드래그 결과를 영역 교정 입력란에 채운다."""
    if getattr(self, "_region_select_target", None) != "redact":
        return
    if hasattr(self, "spn_redact_page"):
        self.spn_redact_page.setValue(max(1, int(page)))
    if hasattr(self, "inp_redact_rect"):
        self.inp_redact_rect.setText(f"{x0:.1f},{y0:.1f},{x1:.1f},{y1:.1f}")
    if hasattr(self, "lbl_redact_drag_hint"):
        self.lbl_redact_drag_hint.setText(
            tm.get("hint_redact_drag_done", page, f"{x0:.1f}", f"{y0:.1f}", f"{x1:.1f}", f"{y1:.1f}")
        )
    self._region_select_target = None
    ToastWidget(tm.get("msg_redact_drag_applied"), toast_type="success", duration=2000).show_toast(self)


def _on_redact_region_mode_changed(self, enabled: bool):
    if not hasattr(self, "lbl_redact_drag_hint"):
        return
    if enabled:
        self.lbl_redact_drag_hint.setText(tm.get("hint_redact_drag_active"))
    else:
        # 선택 완료 시 preview 가 mode off → regionSelected 순으로 방출하므로
        # 여기서 target 을 지우면 선택 콜백이 유실된다. target 은 적용/토글 취소에서만 정리.
        current = self.lbl_redact_drag_hint.text()
        if current == tm.get("hint_redact_drag_active"):
            self.lbl_redact_drag_hint.setText(tm.get("hint_redact_drag_idle"))


def action_redact_area(self):
    path = self.sel_redact.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    # 선택 모드 중이면 종료 (실행 시 혼선 방지)
    preview = getattr(self, "preview_image", None)
    if preview is not None and hasattr(preview, "is_region_select_mode") and preview.is_region_select_mode():
        preview.set_region_select_mode(False)

    raw = self.inp_redact_rect.text().strip() if hasattr(self, "inp_redact_rect") else ""
    if not raw:
        return QMessageBox.warning(self, tm.get("info"), tm.get("err_redact_area_required"))
    parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
    if len(parts) < 4:
        return QMessageBox.warning(self, tm.get("info"), tm.get("err_redact_area_invalid"))
    try:
        coords = [float(parts[i]) for i in range(4)]
    except ValueError:
        return QMessageBox.warning(self, tm.get("info"), tm.get("err_redact_area_invalid"))
    page = self.spn_redact_page.value() if hasattr(self, "spn_redact_page") else 1

    reply = QMessageBox.warning(
        self,
        tm.get("warning"),
        tm.get("msg_confirm_redact_area", page, *coords[:4]),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    if reply != QMessageBox.StandardButton.Yes:
        return

    s, _ = self._choose_save_file(tm.get("save"), "redacted_area.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker(
            "redact_area",
            file_path=path,
            output_path=s,
            rects=[{"page": page, "rect": coords}],
        )


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

    s, _ = self._choose_save_file(tm.get("save"), "redacted.pdf", "PDF (*.pdf)")
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

    s, _ = self._choose_save_file(tm.get("save"), "marked_up.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("add_text_markup", file_path=path, output_path=s, 
                      search_term=term, markup_type=markup_type)

def action_add_background(self):
    """배경색 추가"""
    path = self.sel_bg.get_path()
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))

    color = self.cmb_bg_color.currentData() or [1, 1, 0.9]

    s, _ = self._choose_save_file(tm.get("save"), "with_background.pdf", "PDF (*.pdf)")
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

    s, _ = self._choose_save_file(tm.get("save"), "with_note.pdf", "PDF (*.pdf)")
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

    s, _ = self._choose_save_file(tm.get("save"), "with_drawing.pdf", "PDF (*.pdf)")
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

    s, _ = self._choose_save_file(tm.get("save"), "with_shape.pdf", "PDF (*.pdf)")
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

    s, _ = self._choose_save_file(tm.get("save"), "with_link.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("add_link", file_path=path, output_path=s,
                      page_num=page_num, link_type=link_type,
                      target=target, rect=rect)

def _textbox_page_size_pts(self) -> tuple[float, float]:
    """현재 대상 PDF 페이지 크기(pt). 실패 시 A4."""
    from .textbox_presets import A4_HEIGHT_PT, A4_WIDTH_PT

    path = ""
    if hasattr(self, "sel_textbox"):
        try:
            path = self.sel_textbox.get_path() or ""
        except Exception:
            path = ""
    page_idx = 0
    if hasattr(self, "spn_tb_page"):
        try:
            page_idx = max(0, int(self.spn_tb_page.value()) - 1)
        except Exception:
            page_idx = 0
    if path:
        try:
            from ...core.optional_deps import fitz

            doc = fitz.open(path)
            try:
                if 0 <= page_idx < len(doc):
                    rect = doc[page_idx].rect
                    return float(rect.width), float(rect.height)
            finally:
                doc.close()
        except Exception:
            pass
    return A4_WIDTH_PT, A4_HEIGHT_PT


def _set_textbox_xywh(self, x: float, y: float, w: float | None = None, h: float | None = None) -> None:
    """좌표 스핀 설정 (시그널 루프 방지 + 프리셋 custom 전환은 호출측에서)."""
    blockers = []
    for name in ("spn_tb_x", "spn_tb_y", "spn_tb_w", "spn_tb_h"):
        wdg = getattr(self, name, None)
        if wdg is not None and hasattr(wdg, "blockSignals"):
            wdg.blockSignals(True)
            blockers.append(wdg)
    try:
        if hasattr(self, "spn_tb_x"):
            self.spn_tb_x.setValue(float(x))
        if hasattr(self, "spn_tb_y"):
            self.spn_tb_y.setValue(float(y))
        if w is not None and hasattr(self, "spn_tb_w"):
            self.spn_tb_w.setValue(float(w))
        if h is not None and hasattr(self, "spn_tb_h"):
            self.spn_tb_h.setValue(float(h))
    finally:
        for wdg in blockers:
            wdg.blockSignals(False)


def _mark_textbox_preset_custom(self) -> None:
    cmb = getattr(self, "cmb_tb_preset", None)
    if cmb is None:
        return
    # 이미 custom 이면 스킵
    if cmb.currentData() == "custom":
        return
    cmb.blockSignals(True)
    try:
        for i in range(cmb.count()):
            if cmb.itemData(i) == "custom":
                cmb.setCurrentIndex(i)
                break
    finally:
        cmb.blockSignals(False)


def action_apply_textbox_preset(self, *_args):
    """위치 프리셋 콤보 변경 시 X/Y 좌표 적용 (W/H 유지)."""
    from .textbox_presets import resolve_textbox_preset_xy

    cmb = getattr(self, "cmb_tb_preset", None)
    if cmb is None:
        return None
    preset = cmb.currentData() or "custom"
    if preset == "custom":
        return None

    w = float(self.spn_tb_w.value()) if hasattr(self, "spn_tb_w") else 220.0
    h = float(self.spn_tb_h.value()) if hasattr(self, "spn_tb_h") else 40.0
    # 폰트 최소 높이 보정
    _, _, fontsize, min_h = _textbox_current_style(self)
    if h < min_h:
        h = min_h
        if hasattr(self, "spn_tb_h"):
            self.spn_tb_h.blockSignals(True)
            self.spn_tb_h.setValue(h)
            self.spn_tb_h.blockSignals(False)

    page_w, page_h = _textbox_page_size_pts(self)
    xy = resolve_textbox_preset_xy(str(preset), page_w, page_h, w, h)
    if xy is None:
        return None
    x, y = xy
    _set_textbox_xywh(self, x, y, w, h)
    _sync_textbox_placement_overlay(self)

    if hasattr(self, "lbl_tb_drag_hint"):
        page = int(self.spn_tb_page.value()) if hasattr(self, "spn_tb_page") else 1
        self.lbl_tb_drag_hint.setText(
            tm.get("hint_textbox_preset_applied", cmb.currentText(), page, f"{x:.1f}", f"{y:.1f}")
        )
    return None


def _ensure_textbox_preview_ready(self, path: str):
    """텍스트 상자용 미리보기 동기화. 실패 시 warning 결과, 성공 시 preview 위젯."""
    preview = getattr(self, "preview_image", None)
    if preview is None:
        return None
    ensure = getattr(self, "_ensure_preview_access", None)
    ready = False
    if callable(ensure):
        result = ensure(path)
        if isinstance(result, tuple) and len(result) >= 1:
            ready = bool(result[0])
        else:
            ready = bool(result)
        if not ready:
            update = getattr(self, "_update_preview", None)
            if callable(update):
                update(path)
            if getattr(self, "_current_preview_doc", None) is None:
                return None
    else:
        update = getattr(self, "_update_preview", None)
        if callable(update):
            update(path)
    return preview


def _connect_textbox_preview_signals(self, preview) -> None:
    if getattr(self, "_textbox_region_signal_connected", False):
        return
    try:
        if hasattr(preview, "textPlacementMoved"):
            preview.textPlacementMoved.connect(self._on_text_placement_moved)
        if hasattr(preview, "textPlacementModeChanged"):
            preview.textPlacementModeChanged.connect(self._on_textbox_placement_mode_changed)
        # 레거시 영역 드래그도 유지
        if hasattr(preview, "regionSelected"):
            preview.regionSelected.connect(self._on_preview_region_selected_for_textbox)
        if hasattr(preview, "regionSelectModeChanged"):
            preview.regionSelectModeChanged.connect(self._on_textbox_region_mode_changed)
        self._textbox_region_signal_connected = True
    except Exception:
        pass


def _textbox_current_style(self) -> tuple[str, tuple, int, float]:
    text = ""
    if hasattr(self, "txt_textbox_content"):
        text = self.txt_textbox_content.text().strip()
    color = (0, 0, 0)
    if hasattr(self, "cmb_tb_color"):
        color = self.cmb_tb_color.currentData() or (0, 0, 0)
    fontsize = 14
    if hasattr(self, "spn_tb_fontsize"):
        fontsize = int(self.spn_tb_fontsize.value())
    # 최소 높이: 폰트가 잘리지 않도록
    min_h = max(28, int(fontsize * 1.6) + 8)
    return text, color, fontsize, float(min_h)


def action_start_textbox_region_select(self):
    """미리보기에 텍스트 상자를 띄우고 드래그로 위치를 옮긴다."""
    path = self.sel_textbox.get_path() if hasattr(self, "sel_textbox") else ""
    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))

    # 모듈 함수로 호출 (믹스인/테스트 더미 모두 호환)
    text, color, fontsize, min_h = _textbox_current_style(self)
    if not text:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_enter_text"))

    preview = _ensure_textbox_preview_ready(self, path)
    if preview is None or not hasattr(preview, "set_text_placement_mode"):
        return QMessageBox.warning(
            self, tm.get("warning"), tm.get("err_textbox_drag_preview_unavailable")
        )

    _connect_textbox_preview_signals(self, preview)

    # 토글 해제
    if hasattr(preview, "is_text_placement_mode") and preview.is_text_placement_mode():
        preview.set_text_placement_mode(False)
        if hasattr(self, "lbl_tb_drag_hint"):
            self.lbl_tb_drag_hint.setText(tm.get("hint_textbox_drag_idle"))
        return None

    x = float(self.spn_tb_x.value()) if hasattr(self, "spn_tb_x") else 100.0
    y = float(self.spn_tb_y.value()) if hasattr(self, "spn_tb_y") else 100.0
    w = float(self.spn_tb_w.value()) if hasattr(self, "spn_tb_w") else 200.0
    h = float(self.spn_tb_h.value()) if hasattr(self, "spn_tb_h") else min_h
    h = max(h, min_h)
    if hasattr(self, "spn_tb_h") and self.spn_tb_h.value() < min_h:
        self.spn_tb_h.setValue(int(min_h))

    # 미리보기 현재 페이지와 스핀 동기
    try:
        state = preview.capture_view_state() if hasattr(preview, "capture_view_state") else None
        if isinstance(state, dict) and "page" in state and hasattr(self, "spn_tb_page"):
            self.spn_tb_page.setValue(max(1, int(state["page"]) + 1))
    except Exception:
        pass

    rect_pts = (x, y, x + w, y + h)
    preview.set_text_placement_mode(
        True,
        text=text,
        rect_pts=rect_pts,
        color=color,
        fontsize=fontsize,
    )
    if hasattr(self, "lbl_tb_drag_hint"):
        self.lbl_tb_drag_hint.setText(tm.get("hint_textbox_place_active"))
    ToastWidget(tm.get("msg_textbox_place_started"), toast_type="info", duration=2800).show_toast(self)
    return None


def _on_text_placement_moved(self, page: int, x0: float, y0: float, x1: float, y1: float):
    """미리보기에서 박스를 옮긴 뒤 좌표 필드 반영."""
    w = max(10.0, abs(x1 - x0))
    h = max(10.0, abs(y1 - y0))
    top_left_x = min(x0, x1)
    top_left_y = min(y0, y1)

    if hasattr(self, "spn_tb_page"):
        page_spn = self.spn_tb_page
        if hasattr(page_spn, "blockSignals"):
            page_spn.blockSignals(True)
        page_spn.setValue(max(1, int(page)))
        if hasattr(page_spn, "blockSignals"):
            page_spn.blockSignals(False)
    # 드래그 이동 = 수동 위치 → 프리셋을 custom 으로
    _mark_textbox_preset_custom(self)
    _set_textbox_xywh(self, top_left_x, top_left_y, w, h)

    if hasattr(self, "lbl_tb_drag_hint"):
        self.lbl_tb_drag_hint.setText(
            tm.get("hint_textbox_drag_done", page, f"{top_left_x:.1f}", f"{top_left_y:.1f}")
        )


def _on_textbox_placement_mode_changed(self, enabled: bool):
    if not hasattr(self, "lbl_tb_drag_hint"):
        return
    if enabled:
        self.lbl_tb_drag_hint.setText(tm.get("hint_textbox_place_active"))
    else:
        current = self.lbl_tb_drag_hint.text()
        if current in (
            tm.get("hint_textbox_place_active"),
            tm.get("hint_textbox_drag_active"),
        ):
            self.lbl_tb_drag_hint.setText(tm.get("hint_textbox_drag_idle"))


def _sync_textbox_placement_overlay(self, *_args):
    """텍스트/스타일 변경 시 미리보기 박스 내용 갱신."""
    # 수동 좌표 편집 시 프리셋을 custom 으로 (프리셋 적용 중이 아닐 때만)
    sender = None
    try:
        sender = self.sender() if hasattr(self, "sender") else None
    except Exception:
        sender = None
    if sender is not None and sender is getattr(self, "cmb_tb_preset", None):
        pass
    elif sender in (
        getattr(self, "spn_tb_x", None),
        getattr(self, "spn_tb_y", None),
        getattr(self, "spn_tb_w", None),
        getattr(self, "spn_tb_h", None),
    ):
        _mark_textbox_preset_custom(self)

    preview = getattr(self, "preview_image", None)
    if preview is None or not hasattr(preview, "is_text_placement_mode"):
        return
    if not preview.is_text_placement_mode():
        return
    text, color, fontsize, min_h = _textbox_current_style(self)
    x = float(self.spn_tb_x.value()) if hasattr(self, "spn_tb_x") else 100.0
    y = float(self.spn_tb_y.value()) if hasattr(self, "spn_tb_y") else 100.0
    w = float(self.spn_tb_w.value()) if hasattr(self, "spn_tb_w") else 200.0
    h = max(float(self.spn_tb_h.value()) if hasattr(self, "spn_tb_h") else min_h, min_h)
    if hasattr(preview, "update_text_placement_content"):
        preview.update_text_placement_content(
            text=text or " ",
            rect_pts=(x, y, x + w, y + h),
            color=color,
            fontsize=fontsize,
        )


def _on_preview_region_selected_for_textbox(self, page: int, x0: float, y0: float, x1: float, y1: float):
    """(레거시) 고무줄 영역 선택 결과를 좌표에 반영."""
    if getattr(self, "_region_select_target", None) != "textbox":
        return
    _, _, fontsize, min_h = _textbox_current_style(self)
    w = max(40.0, abs(x1 - x0))
    h = max(min_h, abs(y1 - y0))
    top_left_x = min(x0, x1)
    top_left_y = min(y0, y1)

    if hasattr(self, "spn_tb_page"):
        self.spn_tb_page.setValue(max(1, int(page)))
    _mark_textbox_preset_custom(self)
    _set_textbox_xywh(self, top_left_x, top_left_y, w, h)

    if hasattr(self, "lbl_tb_drag_hint"):
        self.lbl_tb_drag_hint.setText(
            tm.get("hint_textbox_drag_done", page, f"{top_left_x:.1f}", f"{top_left_y:.1f}")
        )
    self._region_select_target = None
    # 영역 선택 후 바로 이동 가능 배치 모드로 전환
    preview = getattr(self, "preview_image", None)
    text, color, fontsize, _ = _textbox_current_style(self)
    if preview is not None and hasattr(preview, "set_text_placement_mode") and text:
        preview.set_text_placement_mode(
            True,
            text=text,
            rect_pts=(top_left_x, top_left_y, top_left_x + w, top_left_y + h),
            color=color,
            fontsize=fontsize,
        )
    ToastWidget(tm.get("msg_textbox_drag_applied"), toast_type="success", duration=2000).show_toast(self)


def _on_textbox_region_mode_changed(self, enabled: bool):
    if not hasattr(self, "lbl_tb_drag_hint"):
        return
    if enabled:
        self.lbl_tb_drag_hint.setText(tm.get("hint_textbox_drag_active"))


def action_insert_textbox(self):
    """텍스트 상자/선택 위치 워터마크 삽입"""
    path = self.sel_textbox.get_path()
    text = self.txt_textbox_content.text().strip()

    if not path:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_select_pdf"))
    if not text:
        return QMessageBox.warning(self, tm.get("info"), tm.get("msg_enter_text"))

    preview = getattr(self, "preview_image", None)
    if preview is not None:
        if hasattr(preview, "is_region_select_mode") and preview.is_region_select_mode():
            preview.set_region_select_mode(False)
        if hasattr(preview, "is_text_placement_mode") and preview.is_text_placement_mode():
            preview.set_text_placement_mode(False)

    page_num = self.spn_tb_page.value() - 1
    x = float(self.spn_tb_x.value())
    y = float(self.spn_tb_y.value())
    w = float(self.spn_tb_w.value()) if hasattr(self, "spn_tb_w") else 200.0
    h = float(self.spn_tb_h.value()) if hasattr(self, "spn_tb_h") else 50.0

    fontsize = self.spn_tb_fontsize.value()
    # 폰트보다 낮은 박스는 Worker 에서 조용히 실패하므로 UI에서도 최소 높이 보정
    min_h = max(28.0, float(fontsize) * 1.6 + 8.0)
    if h < min_h:
        h = min_h
        if hasattr(self, "spn_tb_h"):
            self.spn_tb_h.setValue(float(h))

    color = self.cmb_tb_color.currentData() or (0, 0, 0)
    if isinstance(color, (list, tuple)):
        color = tuple(float(c) for c in color[:3])
    else:
        color = (0.0, 0.0, 0.0)
    fontname = self.cmb_tb_font.currentData() if hasattr(self, "cmb_tb_font") else "cjk"
    opacity = (self.spn_tb_opacity.value() / 100.0) if hasattr(self, "spn_tb_opacity") else 1.0
    rotation = self.spn_tb_rotation.value() if hasattr(self, "spn_tb_rotation") else 0
    align = self.cmb_tb_align.currentData() if hasattr(self, "cmb_tb_align") else 0
    layer = self.cmb_tb_layer.currentData() if hasattr(self, "cmb_tb_layer") else "foreground"

    rect = [float(x), float(y), float(x + w), float(y + h)]

    s, _ = self._choose_save_file(tm.get("save"), "with_textbox.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker(
            "insert_textbox",
            file_path=path,
            output_path=s,
            page_num=page_num,
            rect=rect,
            text=text,
            fontsize=fontsize,
            color=color,
            fontname=fontname,
            opacity=opacity,
            rotation=rotation,
            align=align,
            layer=layer,
        )

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

    s, _ = self._choose_save_file(tm.get("save"), "with_annotation.pdf", "PDF (*.pdf)")
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
