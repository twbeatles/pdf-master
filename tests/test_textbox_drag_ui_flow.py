"""텍스트 상자 미리보기 배치·이동 UI 흐름."""

from __future__ import annotations

from src.ui.tabs_advanced import actions_markup as mod
from src.ui.tabs_advanced.markup_actions import deps as _deps


def test_start_textbox_placement_requires_text(monkeypatch):
    warnings = []
    monkeypatch.setattr(
        _deps.QMessageBox,
        "warning",
        staticmethod(lambda *a, **k: warnings.append(a)),
    )

    class Dummy:
        class Sel:
            def get_path(self):
                return "D:/docs/sample.pdf"

        class Txt:
            def text(self):
                return "   "

        sel_textbox = Sel()
        txt_textbox_content = Txt()

    mod.action_start_textbox_region_select(Dummy())
    assert warnings


def test_start_textbox_placement_enables_mode(monkeypatch):
    calls = {"placement": None, "kwargs": None}

    class PathStub:
        def get_path(self):
            return "D:/docs/sample.pdf"

    class PreviewStub:
        def __init__(self):
            self._mode = False

            class _Sig:
                def connect(self, *_a, **_k):
                    return None

            self.textPlacementMoved = _Sig()
            self.textPlacementModeChanged = _Sig()
            self.regionSelected = _Sig()
            self.regionSelectModeChanged = _Sig()

        def is_text_placement_mode(self):
            return self._mode

        def set_text_placement_mode(self, enabled, **kwargs):
            self._mode = bool(enabled)
            calls["placement"] = self._mode
            calls["kwargs"] = kwargs

        def capture_view_state(self):
            return {"page": 0}

        def is_region_select_mode(self):
            return False

        def set_region_select_mode(self, *_a, **_k):
            return None

    class Spin:
        def __init__(self, v):
            self._v = v

        def value(self):
            return self._v

        def setValue(self, v):
            self._v = int(v)

    class Combo:
        def currentData(self):
            return (0, 0, 0)

    class Hint:
        def __init__(self):
            self._t = ""

        def setText(self, t):
            self._t = t

        def text(self):
            return self._t

    class Dummy:
        def __init__(self):
            self.sel_textbox = PathStub()
            self.preview_image = PreviewStub()
            self.lbl_tb_drag_hint = Hint()
            self.txt_textbox_content = type("T", (), {"text": lambda self: "Hello"})()
            self.spn_tb_x = Spin(100)
            self.spn_tb_y = Spin(120)
            self.spn_tb_w = Spin(200)
            self.spn_tb_h = Spin(40)
            self.spn_tb_page = Spin(1)
            self.spn_tb_fontsize = Spin(14)
            self.cmb_tb_color = Combo()
            self._current_preview_doc = object()

        def _ensure_preview_access(self, path):
            return True, None

    class Toast:
        def __init__(self, *a, **k):
            pass

        def show_toast(self, *a, **k):
            pass

    monkeypatch.setattr(_deps, "ToastWidget", Toast)

    dummy = Dummy()
    result = mod.action_start_textbox_region_select(dummy)
    assert result is None
    assert calls["placement"] is True
    assert calls["kwargs"]["text"] == "Hello"
    assert calls["kwargs"]["rect_pts"][0] == 100.0

    # 토글 해제
    mod.action_start_textbox_region_select(dummy)
    assert calls["placement"] is False


def test_text_placement_moved_fills_fields():
    class Spin:
        def __init__(self, value=0):
            self._v = float(value)

        def setValue(self, v):
            self._v = float(v)

        def value(self):
            return self._v

        def blockSignals(self, *_a):
            return True

    class Hint:
        def __init__(self):
            self._t = ""

        def setText(self, t):
            self._t = t

    class Dummy:
        def __init__(self):
            self.spn_tb_page = Spin(1)
            self.spn_tb_x = Spin(0)
            self.spn_tb_y = Spin(0)
            self.spn_tb_w = Spin(0)
            self.spn_tb_h = Spin(0)
            self.lbl_tb_drag_hint = Hint()
            self.cmb_tb_preset = None

    dummy = Dummy()
    mod._on_text_placement_moved(dummy, 2, 80.0, 100.0, 180.0, 220.0)
    assert dummy.spn_tb_page.value() == 2
    assert abs(dummy.spn_tb_x.value() - 80) < 0.01
    assert abs(dummy.spn_tb_y.value() - 100) < 0.01
    assert abs(dummy.spn_tb_w.value() - 100) < 0.01
    assert abs(dummy.spn_tb_h.value() - 120) < 0.01


def test_textbox_content_text_supports_plain_and_line():
    class Plain:
        def toPlainText(self):
            return "  multi\nline  "

    class Line:
        def text(self):
            return "  single  "

    class Dummy:
        def __init__(self, w):
            self.txt_textbox_content = w

    assert mod._textbox_content_text(Dummy(Plain())) == "multi\nline"
    assert mod._textbox_content_text(Dummy(Line())) == "single"



def test_start_textbox_region_select_requires_path(monkeypatch):
    warnings = []
    monkeypatch.setattr(
        _deps.QMessageBox,
        "warning",
        staticmethod(lambda *a, **k: warnings.append(a)),
    )

    class Dummy:
        class Sel:
            def get_path(self):
                return ""

        sel_textbox = Sel()

    mod.action_start_textbox_region_select(Dummy())
    assert warnings


def test_textbox_region_selected_ignores_other_target(monkeypatch):
    class Spin:
        def __init__(self):
            self._v = 1
            self.calls = 0

        def setValue(self, v):
            self.calls += 1
            self._v = int(v)

        def value(self):
            return self._v

    class Dummy:
        def __init__(self):
            self._region_select_target = "redact"
            self.spn_tb_page = Spin()
            self.spn_tb_x = Spin()
            self.spn_tb_y = Spin()
            self.spn_tb_w = Spin()
            self.spn_tb_h = Spin()
            self.spn_tb_fontsize = type("S", (), {"value": lambda self: 14})()
            self.txt_textbox_content = type("T", (), {"text": lambda self: "x"})()
            self.cmb_tb_color = type("C", (), {"currentData": lambda self: (0, 0, 0)})()

    class Toast:
        def __init__(self, *a, **k):
            raise AssertionError("toast must not fire for wrong target")

        def show_toast(self, *a, **k):
            pass

    monkeypatch.setattr(_deps, "ToastWidget", Toast)

    dummy = Dummy()
    mod._on_preview_region_selected_for_textbox(dummy, 1, 10.0, 20.0, 30.0, 40.0)
    assert dummy.spn_tb_page.calls == 0
    assert dummy._region_select_target == "redact"


def test_redact_region_selected_ignores_textbox_target(monkeypatch):
    class Spin:
        def __init__(self):
            self.calls = 0

        def setValue(self, *_a, **_k):
            self.calls += 1

    class Dummy:
        def __init__(self):
            self._region_select_target = "textbox"
            self.spn_redact_page = Spin()
            self.inp_redact_rect = type("I", (), {"setText": lambda *a, **k: None})()

    class Toast:
        def __init__(self, *a, **k):
            raise AssertionError("toast must not fire for wrong target")

        def show_toast(self, *a, **k):
            pass

    monkeypatch.setattr(_deps, "ToastWidget", Toast)

    dummy = Dummy()
    mod._on_preview_region_selected_for_redact(dummy, 1, 1.0, 2.0, 3.0, 4.0)
    assert dummy.spn_redact_page.calls == 0
