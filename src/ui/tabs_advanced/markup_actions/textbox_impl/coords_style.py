"""텍스트상자 UI 액션 구현 (SOLID 분할)."""
from __future__ import annotations

from .. import deps

def _textbox_page_size_pts(self) -> tuple[float, float]:
    """현재 대상 PDF 페이지 크기(pt). 실패 시 A4."""
    from ...textbox_presets import A4_HEIGHT_PT, A4_WIDTH_PT

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
            from .....core.optional_deps import fitz

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
    from ...textbox_presets import resolve_textbox_preset_xy

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
    # placement 와 순환 import 방지
    from .placement import _sync_textbox_placement_overlay

    _sync_textbox_placement_overlay(self)

    if hasattr(self, "lbl_tb_drag_hint"):
        page = int(self.spn_tb_page.value()) if hasattr(self, "spn_tb_page") else 1
        self.lbl_tb_drag_hint.setText(
            deps.tm.get("hint_textbox_preset_applied", cmb.currentText(), page, f"{x:.1f}", f"{y:.1f}")
        )
    return None

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
    from ...textbox_session import ensure_textbox_session

    return ensure_textbox_session(self)

def _clear_textbox_post_flags(self) -> None:
    """실패/취소/완료 후 잔존 플래그 제거 (다음 작업 부작용 방지)."""
    sess = _textbox_session(self)
    sess.clear_post_flags()
    sess.pending_extract = None
    # 레거시 속성 동기
    self._textbox_reopen_placement_after_success = False
    self._textbox_clear_queue_after_success = False

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
