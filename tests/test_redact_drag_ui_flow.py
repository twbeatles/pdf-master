"""영역 교정 드래그 선택 UI 흐름."""

from __future__ import annotations

from src.ui.tabs_advanced import actions_markup as mod


def test_start_redact_region_select_enables_preview_mode(monkeypatch):
    calls = {"mode": None, "preview_path": None}

    class PathStub:
        def get_path(self):
            return "D:/docs/secret.pdf"

    class PreviewStub:
        def __init__(self):
            self._mode = False

            class _Sig:
                def connect(self, *_a, **_k):
                    return None

            self.regionSelected = _Sig()
            self.regionSelectModeChanged = _Sig()

        def is_region_select_mode(self):
            return self._mode

        def set_region_select_mode(self, enabled):
            self._mode = bool(enabled)
            calls["mode"] = self._mode

    class Hint:
        def __init__(self):
            self._t = ""

        def setText(self, t):
            self._t = t

        def text(self):
            return self._t

    class Dummy:
        def __init__(self):
            self.sel_redact = PathStub()
            self.preview_image = PreviewStub()
            self.lbl_redact_drag_hint = Hint()
            self._current_preview_doc = object()

        def _ensure_preview_access(self, path):
            calls["preview_path"] = path
            return True, None

    warnings = []
    monkeypatch.setattr(
        mod.QMessageBox,
        "warning",
        staticmethod(lambda *a, **k: warnings.append(a)),
    )

    class Toast:
        def __init__(self, *a, **k):
            pass

        def show_toast(self, *a, **k):
            pass

    # actions_markup 가 from ..widgets import ToastWidget 로 바인딩한 심볼을 패치
    monkeypatch.setattr(mod, "ToastWidget", Toast)

    dummy = Dummy()
    result = mod.action_start_redact_region_select(dummy)
    assert result is None
    assert calls["mode"] is True
    assert calls["preview_path"] == "D:/docs/secret.pdf"

    # 토글 해제
    mod.action_start_redact_region_select(dummy)
    assert calls["mode"] is False


def test_start_redact_region_select_requires_path(monkeypatch):
    warnings = []
    monkeypatch.setattr(
        mod.QMessageBox,
        "warning",
        staticmethod(lambda *a, **k: warnings.append(a)),
    )

    class Dummy:
        class Sel:
            def get_path(self):
                return ""

        sel_redact = Sel()

    mod.action_start_redact_region_select(Dummy())
    assert warnings
