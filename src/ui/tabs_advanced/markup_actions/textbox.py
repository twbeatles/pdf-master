from . import deps

def _textbox_page_size_pts(self) -> tuple[float, float]:
    """현재 대상 PDF 페이지 크기(pt). 실패 시 A4."""
    from ..textbox_presets import A4_HEIGHT_PT, A4_WIDTH_PT

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
            from ....core.optional_deps import fitz

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
    from ..textbox_presets import resolve_textbox_preset_xy

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
            deps.tm.get("hint_textbox_preset_applied", cmb.currentText(), page, f"{x:.1f}", f"{y:.1f}")
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
        if hasattr(preview, "textPlacementTextEdited"):
            preview.textPlacementTextEdited.connect(self._on_text_placement_text_edited)
        # 레거시 영역 드래그 / 교체 영역 선택
        if hasattr(preview, "regionSelected"):
            preview.regionSelected.connect(self._on_preview_region_selected_for_textbox)
        if hasattr(preview, "regionSelectModeChanged"):
            preview.regionSelectModeChanged.connect(self._on_textbox_region_mode_changed)
        self._textbox_region_signal_connected = True
    except Exception:
        pass

def _textbox_content_text(self) -> str:
    """QLineEdit / QTextEdit 공통 텍스트 추출."""
    widget = getattr(self, "txt_textbox_content", None)
    if widget is None:
        return ""
    if hasattr(widget, "toPlainText"):
        return str(widget.toPlainText() or "").strip()
    if hasattr(widget, "text"):
        return str(widget.text() or "").strip()
    return ""

def _set_textbox_content_text(self, text: str) -> None:
    widget = getattr(self, "txt_textbox_content", None)
    if widget is None:
        return
    if hasattr(widget, "blockSignals"):
        widget.blockSignals(True)
    try:
        if hasattr(widget, "setPlainText"):
            widget.setPlainText(text)
        elif hasattr(widget, "setText"):
            widget.setText(text)
    finally:
        if hasattr(widget, "blockSignals"):
            widget.blockSignals(False)

def _on_text_placement_text_edited(self, text: str) -> None:
    """오버레이 인라인 편집 결과를 본문 필드에 반영."""
    _set_textbox_content_text(self, text or "")
    if hasattr(self, "lbl_tb_drag_hint"):
        self.lbl_tb_drag_hint.setText(deps.tm.get("hint_textbox_inline_edited"))

def _textbox_style_kwargs(self) -> dict:
    """Worker/큐 공용 스타일 kwargs."""
    text = _textbox_content_text(self)
    fontsize = int(self.spn_tb_fontsize.value()) if hasattr(self, "spn_tb_fontsize") else 14
    color = (0.0, 0.0, 0.0)
    if hasattr(self, "cmb_tb_color"):
        raw = self.cmb_tb_color.currentData() or (0, 0, 0)
        if isinstance(raw, (list, tuple)):
            color = tuple(float(c) for c in raw[:3])
    fontname = self.cmb_tb_font.currentData() if hasattr(self, "cmb_tb_font") else "cjk"
    opacity = (self.spn_tb_opacity.value() / 100.0) if hasattr(self, "spn_tb_opacity") else 1.0
    rotation = self.spn_tb_rotation.value() if hasattr(self, "spn_tb_rotation") else 0
    align = self.cmb_tb_align.currentData() if hasattr(self, "cmb_tb_align") else 0
    layer = self.cmb_tb_layer.currentData() if hasattr(self, "cmb_tb_layer") else "foreground"
    return {
        "text": text,
        "fontsize": fontsize,
        "color": color,
        "fontname": fontname,
        "opacity": opacity,
        "rotation": rotation,
        "align": align,
        "layer": layer,
    }

def _textbox_current_rect_and_page(self) -> tuple[int, list[float]]:
    page_num = (self.spn_tb_page.value() - 1) if hasattr(self, "spn_tb_page") else 0
    x = float(self.spn_tb_x.value()) if hasattr(self, "spn_tb_x") else 100.0
    y = float(self.spn_tb_y.value()) if hasattr(self, "spn_tb_y") else 100.0
    w = float(self.spn_tb_w.value()) if hasattr(self, "spn_tb_w") else 200.0
    h = float(self.spn_tb_h.value()) if hasattr(self, "spn_tb_h") else 50.0
    fontsize = int(self.spn_tb_fontsize.value()) if hasattr(self, "spn_tb_fontsize") else 14
    text = _textbox_content_text(self)
    lines = max(1, text.count("\n") + 1) if text else 1
    min_h = max(28.0, float(fontsize) * 1.6 * lines + 8.0)
    if h < min_h:
        h = min_h
        if hasattr(self, "spn_tb_h"):
            self.spn_tb_h.setValue(float(h))
    return page_num, [float(x), float(y), float(x + w), float(y + h)]

def _textbox_resolve_output_path(self, path: str, *, destructive: bool = False) -> str | None:
    """same-path 체크 시 원본(확인 후), 아니면 저장 다이얼로그.

    destructive=True 이면 교체 등 파괴적 작업용 확인 문구를 사용한다.
    """
    same = False
    chk = getattr(self, "chk_tb_same_path", None)
    if chk is not None and hasattr(chk, "isChecked"):
        same = bool(chk.isChecked())
    if same:
        # 원본 덮어쓰기 확인 (실수 방지)
        key = (
            "msg_confirm_textbox_same_path_destructive"
            if destructive
            else "msg_confirm_textbox_same_path"
        )
        reply = deps.QMessageBox.question(
            self,
            deps.tm.get("confirm"),
            deps.tm.get(key),
            deps.QMessageBox.StandardButton.Yes | deps.QMessageBox.StandardButton.No,
        )
        if reply != deps.QMessageBox.StandardButton.Yes:
            return None
        return path
    s, _ = self._choose_save_file(deps.tm.get("save"), "with_textbox.pdf", "PDF (*.pdf)")
    return s or None

def _textbox_should_keep_placing(self) -> bool:
    chk = getattr(self, "chk_tb_keep_placing", None)
    return bool(chk is not None and hasattr(chk, "isChecked") and chk.isChecked())

def _textbox_session(self):
    from ..textbox_session import ensure_textbox_session

    return ensure_textbox_session(self)

def _clear_textbox_post_flags(self) -> None:
    """실패/취소/완료 후 잔존 플래그 제거 (다음 작업 부작용 방지)."""
    sess = _textbox_session(self)
    sess.clear_post_flags()
    sess.pending_extract = None
    # 레거시 속성 동기
    self._textbox_reopen_placement_after_success = False
    self._textbox_clear_queue_after_success = False

def _textbox_queue_ensure(self) -> list:
    return _textbox_session(self).queue

def _textbox_norm_path(path: str) -> str:
    from ..textbox_session import _norm_path

    return _norm_path(path)

def _textbox_sync_queue_ghost(self) -> None:
    """큐 고스트 오버레이를 미리보기에 반영."""
    preview = getattr(self, "preview_image", None)
    if preview is None or not hasattr(preview, "set_queue_ghost_boxes"):
        return
    sess = _textbox_session(self)
    preview.set_queue_ghost_boxes(sess.queue_snapshot())

def _textbox_queue_refresh_list(self) -> None:
    lst = getattr(self, "lst_tb_queue", None)
    q = _textbox_queue_ensure(self)
    if lst is not None and hasattr(lst, "clear"):
        lst.clear()
        for i, item in enumerate(q, start=1):
            page = int(item.get("page_num", 0)) + 1
            text = str(item.get("text", ""))[:40].replace("\n", " ")
            rect = item.get("rect") or [0, 0, 0, 0]
            stem = str(item.get("file_path", "") or "")
            if stem:
                import os

                stem = os.path.basename(stem)
            label = f"{i}. [{stem or '?'}] p{page} ({rect[0]:.0f},{rect[1]:.0f}) {text}"
            if hasattr(lst, "addItem"):
                lst.addItem(label)
    lbl = getattr(self, "lbl_tb_queue_count", None)
    if lbl is not None and hasattr(lbl, "setText"):
        lbl.setText(deps.tm.get("hint_textbox_queue_count", len(q)))
    _textbox_sync_queue_ghost(self)

def _textbox_current_style(self) -> tuple[str, tuple, int, float]:
    text = _textbox_content_text(self)
    color = (0, 0, 0)
    if hasattr(self, "cmb_tb_color"):
        color = self.cmb_tb_color.currentData() or (0, 0, 0)
    fontsize = 14
    if hasattr(self, "spn_tb_fontsize"):
        fontsize = int(self.spn_tb_fontsize.value())
    # 최소 높이: 폰트·줄 수가 잘리지 않도록
    lines = max(1, text.count("\n") + 1) if text else 1
    min_h = max(28, int(fontsize * 1.6 * lines) + 8)
    return text, color, fontsize, float(min_h)

def action_start_textbox_region_select(self):
    """미리보기에 텍스트 상자를 띄우고 드래그로 위치를 옮긴다."""
    path = self.sel_textbox.get_path() if hasattr(self, "sel_textbox") else ""
    if not path:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("msg_select_pdf"))

    # 모듈 함수로 호출 (믹스인/테스트 더미 모두 호환)
    text, color, fontsize, min_h = _textbox_current_style(self)
    if not text:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("msg_enter_text"))

    preview = _ensure_textbox_preview_ready(self, path)
    if preview is None or not hasattr(preview, "set_text_placement_mode"):
        return deps.QMessageBox.warning(
            self, deps.tm.get("warning"), deps.tm.get("err_textbox_drag_preview_unavailable")
        )

    _connect_textbox_preview_signals(self, preview)

    # 토글 해제
    if hasattr(preview, "is_text_placement_mode") and preview.is_text_placement_mode():
        preview.set_text_placement_mode(False)
        if hasattr(self, "lbl_tb_drag_hint"):
            self.lbl_tb_drag_hint.setText(deps.tm.get("hint_textbox_drag_idle"))
        return None

    x = float(self.spn_tb_x.value()) if hasattr(self, "spn_tb_x") else 100.0
    y = float(self.spn_tb_y.value()) if hasattr(self, "spn_tb_y") else 100.0
    w = float(self.spn_tb_w.value()) if hasattr(self, "spn_tb_w") else 200.0
    h = float(self.spn_tb_h.value()) if hasattr(self, "spn_tb_h") else min_h
    h = max(h, min_h)
    if hasattr(self, "spn_tb_h") and self.spn_tb_h.value() < min_h:
        self.spn_tb_h.setValue(float(min_h))

    align = 0
    if hasattr(self, "cmb_tb_align"):
        align = int(self.cmb_tb_align.currentData() or 0)
    opacity = 1.0
    if hasattr(self, "spn_tb_opacity"):
        opacity = float(self.spn_tb_opacity.value()) / 100.0

    # 미리보기 현재 페이지와 스핀 동기
    try:
        state = preview.capture_view_state() if hasattr(preview, "capture_view_state") else None
        if isinstance(state, dict) and "page" in state and hasattr(self, "spn_tb_page"):
            self.spn_tb_page.setValue(max(1, int(state["page"]) + 1))
    except Exception:
        pass

    # 큰 미리보기에서 배치하기 쉽도록 포커스 모드 권장 진입
    if hasattr(self, "_set_preview_focus_mode") and not getattr(self, "_preview_focus_mode", False):
        try:
            self._set_preview_focus_mode(True)
        except Exception:
            pass

    rect_pts = (x, y, x + w, y + h)
    preview.set_text_placement_mode(
        True,
        text=text,
        rect_pts=rect_pts,
        color=color,
        fontsize=fontsize,
        align=align,
        opacity=opacity,
    )
    if hasattr(self, "lbl_tb_drag_hint"):
        self.lbl_tb_drag_hint.setText(deps.tm.get("hint_textbox_place_active"))
    deps.ToastWidget(deps.tm.get("msg_textbox_place_started"), toast_type="info", duration=2800).show_toast(self)
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
            deps.tm.get("hint_textbox_drag_done", page, f"{top_left_x:.1f}", f"{top_left_y:.1f}")
        )

def _on_textbox_placement_mode_changed(self, enabled: bool):
    if not hasattr(self, "lbl_tb_drag_hint"):
        return
    if enabled:
        self.lbl_tb_drag_hint.setText(deps.tm.get("hint_textbox_place_active"))
    else:
        current = self.lbl_tb_drag_hint.text()
        if current in (
            deps.tm.get("hint_textbox_place_active"),
            deps.tm.get("hint_textbox_drag_active"),
        ):
            self.lbl_tb_drag_hint.setText(deps.tm.get("hint_textbox_drag_idle"))

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
    align = 0
    if hasattr(self, "cmb_tb_align"):
        align = int(self.cmb_tb_align.currentData() or 0)
    opacity = 1.0
    if hasattr(self, "spn_tb_opacity"):
        opacity = float(self.spn_tb_opacity.value()) / 100.0
    if hasattr(preview, "update_text_placement_content"):
        preview.update_text_placement_content(
            text=text or " ",
            rect_pts=(x, y, x + w, y + h),
            color=color,
            fontsize=fontsize,
            align=align,
            opacity=opacity,
        )

def _on_preview_region_selected_for_textbox(self, page: int, x0: float, y0: float, x1: float, y1: float):
    """고무줄 영역 선택 — textbox 배치 또는 textbox_replace 교체."""
    target = getattr(self, "_region_select_target", None)
    if target not in ("textbox", "textbox_replace"):
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
            deps.tm.get("hint_textbox_drag_done", page, f"{top_left_x:.1f}", f"{top_left_y:.1f}")
        )
    self._region_select_target = None

    # 실험: 영역 텍스트를 Worker로 추출 후 본문에 채움
    if target == "textbox_replace":
        path = self.sel_textbox.get_path() if hasattr(self, "sel_textbox") else ""
        page0 = max(0, int(page) - 1)
        rect = [top_left_x, top_left_y, top_left_x + w, top_left_y + h]
        sess = _textbox_session(self)
        sess.pending_extract = {"page_num": page0, "rect": rect, "path": path}
        if path and hasattr(self, "run_worker"):
            self.run_worker(
                "extract_text_in_rect",
                file_path=path,
                page_num=page0,
                rect=rect,
            )
        else:
            # 폴백: 동기 추출
            password = getattr(self, "_current_preview_password", None)
            extracted = _extract_text_in_rect_sync(
                path,
                page0,
                top_left_x,
                top_left_y,
                top_left_x + w,
                top_left_y + h,
                password=password if isinstance(password, str) else None,
            )
            if extracted:
                _set_textbox_content_text(self, extracted)
            deps.ToastWidget(deps.tm.get("msg_textbox_replace_region_ready"), toast_type="info", duration=2500).show_toast(self)
        return

    # 영역 선택 후 바로 이동 가능 배치 모드로 전환
    preview = getattr(self, "preview_image", None)
    text, color, fontsize, _ = _textbox_current_style(self)
    align = 0
    if hasattr(self, "cmb_tb_align"):
        align = int(self.cmb_tb_align.currentData() or 0)
    opacity = 1.0
    if hasattr(self, "spn_tb_opacity"):
        opacity = float(self.spn_tb_opacity.value()) / 100.0
    if preview is not None and hasattr(preview, "set_text_placement_mode") and text:
        preview.set_text_placement_mode(
            True,
            text=text,
            rect_pts=(top_left_x, top_left_y, top_left_x + w, top_left_y + h),
            color=color,
            fontsize=fontsize,
            align=align,
            opacity=opacity,
        )
    deps.ToastWidget(deps.tm.get("msg_textbox_drag_applied"), toast_type="success", duration=2000).show_toast(self)

def _extract_text_in_rect_sync(
    path: str,
    page_num: int,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    *,
    password: str | None = None,
) -> str:
    """짧은 클립 추출 — 암호 지원, 실패 시 빈 문자열.

    대용량 PDF에서 UI 스톨을 줄이기 위해 예외·타임아웃성 실패는 삼키고 빈 값을 반환한다.
    (전체 추출은 Worker 경로가 이상적이나, 드래그 직후 즉시 피드백용 경량 경로.)
    """
    if not path:
        return ""
    try:
        from ....core.optional_deps import fitz
    except Exception:
        return ""
    if fitz is None:
        return ""
    doc = None
    try:
        doc = fitz.open(path)
        if getattr(doc, "needs_pass", False) or getattr(doc, "is_encrypted", False):
            if password:
                try:
                    doc.authenticate(password)
                except Exception:
                    return ""
            else:
                return ""
        if page_num < 0 or page_num >= len(doc):
            return ""
        page = doc[page_num]
        clip = fitz.Rect(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
        return (page.get_text("text", clip=clip) or "").strip()
    except Exception:
        return ""
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass

def _on_textbox_region_mode_changed(self, enabled: bool):
    if not hasattr(self, "lbl_tb_drag_hint"):
        return
    if enabled:
        target = getattr(self, "_region_select_target", None)
        if target == "textbox_replace":
            self.lbl_tb_drag_hint.setText(deps.tm.get("hint_textbox_replace_drag_active"))
        else:
            self.lbl_tb_drag_hint.setText(deps.tm.get("hint_textbox_drag_active"))

def action_insert_textbox(self):
    """텍스트 상자 삽입 (same-path / 연속 배치 옵션 지원)."""
    path = self.sel_textbox.get_path() if hasattr(self, "sel_textbox") else ""
    style = _textbox_style_kwargs(self)
    text = style["text"]

    if not path:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("msg_select_pdf"))
    if not text:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("msg_enter_text"))

    preview = getattr(self, "preview_image", None)
    keep = _textbox_should_keep_placing(self)
    if preview is not None:
        if hasattr(preview, "is_region_select_mode") and preview.is_region_select_mode():
            preview.set_region_select_mode(False)
        # same-path 저장 전 미리보기가 닫히므로 배치는 항상 종료 후 성공 시 재개
        if hasattr(preview, "is_text_placement_mode") and preview.is_text_placement_mode():
            preview.set_text_placement_mode(False)

    page_num, rect = _textbox_current_rect_and_page(self)
    out = _textbox_resolve_output_path(self, path, destructive=False)
    if not out:
        return None

    sess = _textbox_session(self)
    sess.set_post_flags(reopen=keep, clear_queue=False)
    self._textbox_reopen_placement_after_success = sess.reopen_after_success
    self._textbox_clear_queue_after_success = sess.clear_queue_after_success
    self.run_worker(
        "insert_textbox",
        file_path=path,
        output_path=out,
        page_num=page_num,
        rect=rect,
        text=text,
        fontsize=style["fontsize"],
        color=style["color"],
        fontname=style["fontname"],
        opacity=style["opacity"],
        rotation=style["rotation"],
        align=style["align"],
        layer=style["layer"],
    )

def action_textbox_queue_add(self):
    """현재 좌표·텍스트를 다중 삽입 큐에 추가 (파일 경로 고정)."""
    path = self.sel_textbox.get_path() if hasattr(self, "sel_textbox") else ""
    style = _textbox_style_kwargs(self)
    if not path:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("msg_select_pdf"))
    if not style["text"]:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("msg_enter_text"))
    page_num, rect = _textbox_current_rect_and_page(self)
    sess = _textbox_session(self)
    if sess.path_mismatch_with(path):
        reply = deps.QMessageBox.question(
            self,
            deps.tm.get("confirm"),
            deps.tm.get("msg_confirm_textbox_queue_path_mismatch"),
            deps.QMessageBox.StandardButton.Yes | deps.QMessageBox.StandardButton.No,
        )
        if reply != deps.QMessageBox.StandardButton.Yes:
            return None
        sess.clear_queue()
    item = {
        "file_path": path,
        "page_num": page_num,
        "rect": rect,
        **style,
    }
    n = sess.add_box(item)
    self._textbox_queue = sess.queue
    _textbox_queue_refresh_list(self)
    deps.ToastWidget(deps.tm.get("msg_textbox_queued", n), toast_type="success", duration=1800).show_toast(self)
    return None

def action_textbox_queue_clear(self):
    sess = _textbox_session(self)
    sess.clear_queue()
    self._textbox_queue = sess.queue
    _textbox_queue_refresh_list(self)

def action_textbox_queue_commit(self):
    """큐에 쌓인 텍스트 상자를 일괄 삽입."""
    path = self.sel_textbox.get_path() if hasattr(self, "sel_textbox") else ""
    sess = _textbox_session(self)
    q = sess.queue_snapshot()
    if not path:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("msg_select_pdf"))
    err_key = sess.commit_path_error(path)
    if err_key:
        return deps.QMessageBox.warning(self, deps.tm.get("error" if err_key != "err_textbox_queue_empty" else "info"), deps.tm.get(err_key))
    queued_path = str(q[0].get("file_path", "") or "")
    out = _textbox_resolve_output_path(self, queued_path, destructive=False)
    if not out:
        return None
    keep = _textbox_should_keep_placing(self)
    sess.set_post_flags(reopen=keep, clear_queue=True)
    self._textbox_reopen_placement_after_success = sess.reopen_after_success
    self._textbox_clear_queue_after_success = sess.clear_queue_after_success
    self.run_worker(
        "insert_textboxes",
        file_path=queued_path,
        output_path=out,
        boxes=q,
    )
    return None

def action_start_textbox_replace_region(self):
    """실험: 영역 드래그 후 기존 텍스트 교체 준비."""
    path = self.sel_textbox.get_path() if hasattr(self, "sel_textbox") else ""
    if not path:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("msg_select_pdf"))
    preview = _ensure_textbox_preview_ready(self, path)
    if preview is None or not hasattr(preview, "set_region_select_mode"):
        return deps.QMessageBox.warning(
            self, deps.tm.get("warning"), deps.tm.get("err_textbox_drag_preview_unavailable")
        )
    _connect_textbox_preview_signals(self, preview)
    if preview.is_region_select_mode() and getattr(self, "_region_select_target", None) == "textbox_replace":
        preview.set_region_select_mode(False)
        self._region_select_target = None
        if hasattr(self, "lbl_tb_drag_hint"):
            self.lbl_tb_drag_hint.setText(deps.tm.get("hint_textbox_drag_idle"))
        return None
    if hasattr(preview, "is_text_placement_mode") and preview.is_text_placement_mode():
        preview.set_text_placement_mode(False)
    self._region_select_target = "textbox_replace"
    preview.set_region_select_mode(True)
    if hasattr(self, "lbl_tb_drag_hint"):
        self.lbl_tb_drag_hint.setText(deps.tm.get("hint_textbox_replace_drag_active"))
    deps.ToastWidget(deps.tm.get("msg_textbox_replace_drag_started"), toast_type="info", duration=2500).show_toast(self)
    return None

def action_replace_text_in_rect(self):
    """선택된 영역(좌표)의 기존 내용을 교정 후 새 텍스트 삽입."""
    path = self.sel_textbox.get_path() if hasattr(self, "sel_textbox") else ""
    style = _textbox_style_kwargs(self)
    if not path:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("msg_select_pdf"))
    if not style["text"]:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("msg_enter_text"))
    page_num, rect = _textbox_current_rect_and_page(self)
    out = _textbox_resolve_output_path(self, path, destructive=True)
    if not out:
        return None
    reply = deps.QMessageBox.question(
        self,
        deps.tm.get("confirm"),
        deps.tm.get("msg_confirm_replace_text_in_rect"),
        deps.QMessageBox.StandardButton.Yes | deps.QMessageBox.StandardButton.No,
    )
    if reply != deps.QMessageBox.StandardButton.Yes:
        return None
    preview = getattr(self, "preview_image", None)
    if preview is not None:
        if hasattr(preview, "is_region_select_mode") and preview.is_region_select_mode():
            preview.set_region_select_mode(False)
        if hasattr(preview, "is_text_placement_mode") and preview.is_text_placement_mode():
            preview.set_text_placement_mode(False)
    sess = _textbox_session(self)
    keep = _textbox_should_keep_placing(self)
    sess.set_post_flags(reopen=keep, clear_queue=False)
    self._textbox_reopen_placement_after_success = sess.reopen_after_success
    self._textbox_clear_queue_after_success = sess.clear_queue_after_success
    self.run_worker(
        "replace_text_in_rect",
        file_path=path,
        output_path=out,
        page_num=page_num,
        rect=rect,
        text=style["text"],
        fontsize=style["fontsize"],
        color=style["color"],
        fontname=style["fontname"],
        opacity=style["opacity"],
        rotation=style["rotation"],
        align=style["align"],
        layer=style["layer"],
    )
    return None

def _on_textbox_worker_success(self) -> None:
    """삽입/교체 성공 후 큐 정리 및 연속 배치 재개."""
    sess = _textbox_session(self)
    clear_q = bool(sess.clear_queue_after_success) or bool(
        getattr(self, "_textbox_clear_queue_after_success", False)
    )
    reopen = bool(sess.reopen_after_success) or bool(
        getattr(self, "_textbox_reopen_placement_after_success", False)
    )
    # 성공 시에도 플래그는 즉시 소비 (재진입 방지)
    _clear_textbox_post_flags(self)
    if clear_q:
        sess.clear_queue()
        self._textbox_queue = sess.queue
        _textbox_queue_refresh_list(self)
    if reopen and _textbox_should_keep_placing(self):
        from PyQt6.QtCore import QTimer

        QTimer.singleShot(150, lambda: action_start_textbox_region_select(self))

def _on_extract_text_in_rect_success(self, payload: dict) -> None:
    """extract_text_in_rect Worker 결과 → 본문 필드 반영."""
    text = str(payload.get("text", "") or "")
    if text:
        _set_textbox_content_text(self, text)
    sess = _textbox_session(self)
    sess.pending_extract = None
    deps.ToastWidget(deps.tm.get("msg_textbox_replace_region_ready"), toast_type="info", duration=2500).show_toast(self)
