"""미리보기 포커스 모드 + 전체화면 호스트."""

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget

from ...core.i18n import tm
from ...core.settings import save_settings
from .fullscreen_host import PreviewFullscreenHost

logger = logging.getLogger(__name__)

# 포커스 시 좌측 최소 폭
_FOCUS_LEFT_MIN = 0
_FOCUS_PREVIEW_SHARE = 10_000


def _set_left_visible(left, visible: bool) -> None:
    if left is None:
        return
    setter = getattr(left, "setVisible", None)
    if callable(setter):
        setter(bool(visible))


def _is_preview_focus_mode(self) -> bool:
    return bool(getattr(self, "_preview_focus_mode", False))


def _is_preview_fullscreen(self) -> bool:
    host = getattr(self, "_preview_fullscreen_host", None)
    return host is not None and host.isVisible()


def _set_preview_focus_mode(self, enabled: bool) -> None:
    """좌측 작업 패널을 접고 미리보기를 확장(또는 복원)."""
    enabled = bool(enabled)
    # 전체화면 중이면 포커스 플래그만 갱신 (레이아웃은 호스트가 담당)
    if _is_preview_fullscreen(self):
        self._preview_focus_mode = enabled
        self.settings["preview_focus_mode"] = enabled
        _sync_preview_focus_chrome(self)
        return

    if _is_preview_focus_mode(self) == enabled:
        _sync_preview_focus_chrome(self)
        return

    splitter = getattr(self, "content_splitter", None)
    left = getattr(self, "_content_left_widget", None)
    if splitter is None:
        logger.warning("content_splitter missing; cannot toggle preview focus")
        return

    if enabled:
        try:
            sizes = list(splitter.sizes())
        except Exception:
            sizes = []
        if sizes and sum(sizes) > 0:
            self._splitter_sizes_before_focus = sizes
            self.settings["splitter_sizes_before_focus"] = sizes
        self._preview_focus_mode = True
        self.settings["preview_focus_mode"] = True

        try:
            splitter.setChildrenCollapsible(True)
        except Exception:
            pass
        _set_left_visible(left, False)
        try:
            total = max(1, splitter.width())
            splitter.setSizes([_FOCUS_LEFT_MIN, max(total, _FOCUS_PREVIEW_SHARE)])
        except Exception:
            logger.debug("Failed to expand splitter for focus mode", exc_info=True)
    else:
        self._preview_focus_mode = False
        self.settings["preview_focus_mode"] = False
        _set_left_visible(left, True)
        try:
            splitter.setChildrenCollapsible(False)
        except Exception:
            pass
        restore = getattr(self, "_splitter_sizes_before_focus", None)
        if not restore:
            restore = self.settings.get("splitter_sizes_before_focus")
        if isinstance(restore, (list, tuple)) and len(restore) >= 2:
            try:
                splitter.setSizes([int(restore[0]), int(restore[1])])
            except Exception:
                logger.debug("Failed to restore splitter sizes", exc_info=True)
        else:
            splitter.setSizes([650, 450])

    _sync_preview_focus_chrome(self)
    _persist_preview_layout_settings(self)
    _refresh_text_placement_after_layout(self)


def _toggle_preview_focus_mode(self) -> None:
    """F11 순환: 일반 → 포커스 → 전체화면 → 일반."""
    if _is_preview_fullscreen(self):
        _exit_preview_fullscreen(self, restore_focus=False)
        _set_preview_focus_mode(self, False)
        return
    if _is_preview_focus_mode(self):
        _enter_preview_fullscreen(self)
        return
    _set_preview_focus_mode(self, True)


def _enter_preview_fullscreen(self) -> None:
    """미리보기 위젯을 전체화면 호스트로 reparent."""
    if _is_preview_fullscreen(self):
        return
    preview = getattr(self, "preview_image", None)
    panel = getattr(self, "preview_panel", None)
    if preview is None or panel is None:
        return

    # 포커스 모드가 아니면 먼저 포커스로 (복원 크기 확보)
    if not _is_preview_focus_mode(self):
        _set_preview_focus_mode(self, True)

    host = getattr(self, "_preview_fullscreen_host", None)
    if host is None:
        host = PreviewFullscreenHost(self)
        # X/Esc: 포커스 유지. F11 cycle: 전체화면+포커스 해제(메인 순환과 동일).
        host.hostClosing.connect(lambda: _exit_preview_fullscreen(self, restore_focus=True))
        host.layoutCycleExitRequested.connect(lambda: _toggle_preview_focus_mode(self))
        host.placeTextboxRequested.connect(self.action_start_textbox_region_select)
        host.insertTextboxRequested.connect(self.action_insert_textbox)
        self._preview_fullscreen_host = host

    # 패널 레이아웃에서 제거
    layout = panel.layout()
    if layout is not None:
        layout.removeWidget(preview)
    self._preview_layout_parent = panel
    host.attach_preview(preview)
    host.showFullScreen()
    _sync_preview_focus_chrome(self)
    _refresh_text_placement_after_layout(self)


def _exit_preview_fullscreen(self, *, restore_focus: bool = True) -> None:
    """전체화면 호스트에서 미리보기를 패널로 복귀."""
    if getattr(self, "_preview_fullscreen_exiting", False):
        return
    host = getattr(self, "_preview_fullscreen_host", None)
    preview = getattr(self, "preview_image", None)
    panel = getattr(self, "preview_panel", None)
    if host is None:
        return

    self._preview_fullscreen_exiting = True
    try:
        detached = host.detach_preview()
        if detached is None:
            detached = preview

        if panel is not None and detached is not None:
            layout = panel.layout()
            if layout is not None:
                bar = getattr(self, "preview_focus_bar", None)
                insert_at = layout.count()
                if bar is not None:
                    for i in range(layout.count()):
                        item = layout.itemAt(i)
                        if item is not None and item.widget() is bar:
                            insert_at = i
                            break
                layout.insertWidget(insert_at, detached, 1)
            detached.setParent(panel)
            detached.show()

        # hostClosing 재진입 방지 후 창 닫기
        if host.isVisible():
            try:
                host.blockSignals(True)
                host.close()
            finally:
                host.blockSignals(False)

        if not restore_focus:
            pass

        _sync_preview_focus_chrome(self)
        _refresh_text_placement_after_layout(self)
    finally:
        self._preview_fullscreen_exiting = False


def _sync_preview_focus_chrome(self) -> None:
    """포커스/전체화면 버튼 라벨·미니 툴바 표시 동기화."""
    focused = _is_preview_focus_mode(self)
    fullscreen = _is_preview_fullscreen(self)
    btn = getattr(self, "btn_preview_focus", None)
    if btn is not None:
        if fullscreen:
            btn.setText(tm.get("btn_preview_fullscreen_exit"))
            btn.setToolTip(tm.get("tooltip_preview_fullscreen_exit"))
        elif focused:
            btn.setText(tm.get("btn_preview_focus_exit"))
            btn.setToolTip(tm.get("tooltip_preview_focus_exit"))
        else:
            btn.setText(tm.get("btn_preview_focus_enter"))
            btn.setToolTip(tm.get("tooltip_preview_focus_enter"))

    bar = getattr(self, "preview_focus_bar", None)
    if bar is not None:
        bar.setVisible(focused or fullscreen)

    panel = getattr(self, "preview_panel", None)
    if panel is not None and hasattr(panel, "setTitle"):
        if fullscreen:
            panel.setTitle(tm.get("preview_title_fullscreen"))
        elif focused:
            panel.setTitle(tm.get("preview_title_focus"))
        else:
            panel.setTitle(tm.get("preview_title"))


def _on_preview_focus_escape(self) -> None:
    """Esc: 인라인 편집 → 배치 → 영역선택 → 전체화면 → 포커스."""
    preview = getattr(self, "preview_image", None)
    if preview is not None:
        # 인라인 텍스트 편집 중이면 오버레이가 Esc를 소비 — 배치 모드 유지
        overlay = getattr(preview, "_text_placement_overlay", None)
        if overlay is not None and getattr(overlay, "is_editing", None):
            if callable(overlay.is_editing) and overlay.is_editing():
                overlay.cancel_inline_edit()
                return
        if hasattr(preview, "is_text_placement_mode") and preview.is_text_placement_mode():
            preview.set_text_placement_mode(False)
            return
        if hasattr(preview, "is_region_select_mode") and preview.is_region_select_mode():
            preview.set_region_select_mode(False)
            return
    if _is_preview_fullscreen(self):
        _exit_preview_fullscreen(self, restore_focus=True)
        return
    if _is_preview_focus_mode(self):
        _set_preview_focus_mode(self, False)


def _restore_preview_focus_on_startup(self) -> None:
    """설정에 포커스 모드가 켜져 있으면 기동 후 적용 (전체화면은 복원하지 않음)."""
    if bool(self.settings.get("preview_focus_mode", False)):
        _set_preview_focus_mode(self, True)


def _persist_preview_layout_settings(self) -> None:
    if hasattr(self, "_schedule_settings_save"):
        self._schedule_settings_save()
    else:
        save_settings(self.settings)


def _refresh_text_placement_after_layout(self) -> None:
    preview = getattr(self, "preview_image", None)
    if preview is not None and hasattr(preview, "is_text_placement_mode"):
        if preview.is_text_placement_mode() and hasattr(preview, "update_text_placement_content"):
            try:
                preview.update_text_placement_content()
            except Exception:
                logger.debug("text placement refresh after layout change failed", exc_info=True)


__all__ = [
    "_is_preview_focus_mode",
    "_is_preview_fullscreen",
    "_set_preview_focus_mode",
    "_toggle_preview_focus_mode",
    "_enter_preview_fullscreen",
    "_exit_preview_fullscreen",
    "_sync_preview_focus_chrome",
    "_on_preview_focus_escape",
    "_restore_preview_focus_on_startup",
]
