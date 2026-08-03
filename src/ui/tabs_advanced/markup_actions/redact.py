from . import deps

def action_start_redact_region_select(self):
    """미리보기에서 드래그로 교정 영역을 선택한다."""
    path = self.sel_redact.get_path() if hasattr(self, "sel_redact") else ""
    if not path:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("msg_select_pdf"))

    preview = getattr(self, "preview_image", None)
    if preview is None or not hasattr(preview, "set_region_select_mode"):
        return deps.QMessageBox.warning(self, deps.tm.get("warning"), deps.tm.get("err_redact_drag_preview_unavailable"))

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
                return deps.QMessageBox.warning(
                    self, deps.tm.get("warning"), deps.tm.get("err_redact_drag_preview_unavailable")
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
        self.lbl_redact_drag_hint.setText(deps.tm.get("hint_redact_drag_active"))
    deps.ToastWidget(deps.tm.get("msg_redact_drag_started"), toast_type="info", duration=2500).show_toast(self)
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
            deps.tm.get("hint_redact_drag_done", page, f"{x0:.1f}", f"{y0:.1f}", f"{x1:.1f}", f"{y1:.1f}")
        )
    self._region_select_target = None
    deps.ToastWidget(deps.tm.get("msg_redact_drag_applied"), toast_type="success", duration=2000).show_toast(self)

def _on_redact_region_mode_changed(self, enabled: bool):
    if not hasattr(self, "lbl_redact_drag_hint"):
        return
    if enabled:
        self.lbl_redact_drag_hint.setText(deps.tm.get("hint_redact_drag_active"))
    else:
        # 선택 완료 시 preview 가 mode off → regionSelected 순으로 방출하므로
        # 여기서 target 을 지우면 선택 콜백이 유실된다. target 은 적용/토글 취소에서만 정리.
        current = self.lbl_redact_drag_hint.text()
        if current == deps.tm.get("hint_redact_drag_active"):
            self.lbl_redact_drag_hint.setText(deps.tm.get("hint_redact_drag_idle"))

def action_redact_area(self):
    path = self.sel_redact.get_path()
    if not path:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("msg_select_pdf"))
    # 선택 모드 중이면 종료 (실행 시 혼선 방지)
    preview = getattr(self, "preview_image", None)
    if preview is not None and hasattr(preview, "is_region_select_mode") and preview.is_region_select_mode():
        preview.set_region_select_mode(False)

    raw = self.inp_redact_rect.text().strip() if hasattr(self, "inp_redact_rect") else ""
    if not raw:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("err_redact_area_required"))
    parts = [p.strip() for p in raw.replace(";", ",").split(",") if p.strip()]
    if len(parts) < 4:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("err_redact_area_invalid"))
    try:
        coords = [float(parts[i]) for i in range(4)]
    except ValueError:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("err_redact_area_invalid"))
    page = self.spn_redact_page.value() if hasattr(self, "spn_redact_page") else 1

    reply = deps.QMessageBox.warning(
        self,
        deps.tm.get("warning"),
        deps.tm.get("msg_confirm_redact_area", page, *coords[:4]),
        deps.QMessageBox.StandardButton.Yes | deps.QMessageBox.StandardButton.No,
    )
    if reply != deps.QMessageBox.StandardButton.Yes:
        return

    s, _ = self._choose_save_file(deps.tm.get("save"), "redacted_area.pdf", "PDF (*.pdf)")
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
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("msg_select_pdf"))
    if not term:
        return deps.QMessageBox.warning(self, deps.tm.get("info"), deps.tm.get("msg_enter_redact_text"))

    reply = deps.QMessageBox.warning(self, deps.tm.get("warning"), 
                               deps.tm.get("msg_confirm_redact").format(term),
                               deps.QMessageBox.StandardButton.Yes | deps.QMessageBox.StandardButton.No)
    if reply != deps.QMessageBox.StandardButton.Yes:
        return

    s, _ = self._choose_save_file(deps.tm.get("save"), "redacted.pdf", "PDF (*.pdf)")
    if s:
        self.run_worker("redact_text", file_path=path, output_path=s, search_term=term)
