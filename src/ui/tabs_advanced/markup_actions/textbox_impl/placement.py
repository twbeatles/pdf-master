"""텍스트상자 UI 액션 구현 (SOLID 분할)."""
from __future__ import annotations

from .. import deps
from .coords_style import (
    _mark_textbox_preset_custom,
    _set_textbox_content_text,
    _set_textbox_xywh,
    _textbox_current_style,
    _textbox_session,
)

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
        from .....core.optional_deps import fitz
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
