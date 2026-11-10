"""텍스트 상자 위치 프리셋 단위 테스트."""

from __future__ import annotations

from src.ui.tabs_advanced.textbox_presets import (
    A4_HEIGHT_PT,
    A4_WIDTH_PT,
    resolve_textbox_preset_xy,
)


def test_a4_top_left_margin():
    xy = resolve_textbox_preset_xy("top-left", A4_WIDTH_PT, A4_HEIGHT_PT, 200, 40, margin=36)
    assert xy is not None
    assert abs(xy[0] - 36) < 0.01
    assert abs(xy[1] - 36) < 0.01


def test_a4_top_right():
    w, h = 200.0, 40.0
    xy = resolve_textbox_preset_xy("top-right", A4_WIDTH_PT, A4_HEIGHT_PT, w, h, margin=36)
    assert xy is not None
    assert abs(xy[0] - (A4_WIDTH_PT - w - 36)) < 0.01
    assert abs(xy[1] - 36) < 0.01


def test_a4_bottom_center():
    w, h = 220.0, 40.0
    xy = resolve_textbox_preset_xy("bottom-center", A4_WIDTH_PT, A4_HEIGHT_PT, w, h, margin=36)
    assert xy is not None
    assert abs(xy[0] - (A4_WIDTH_PT - w) / 2) < 0.01
    assert abs(xy[1] - (A4_HEIGHT_PT - h - 36)) < 0.01


def test_a4_center():
    w, h = 100.0, 50.0
    xy = resolve_textbox_preset_xy("center", A4_WIDTH_PT, A4_HEIGHT_PT, w, h)
    assert xy is not None
    assert abs(xy[0] - (A4_WIDTH_PT - w) / 2) < 0.01
    assert abs(xy[1] - (A4_HEIGHT_PT - h) / 2) < 0.01


def test_custom_returns_none():
    assert resolve_textbox_preset_xy("custom", 595, 842, 100, 40) is None


def test_clamps_to_page():
    # 박스가 페이지보다 크면 0,0 근처로
    xy = resolve_textbox_preset_xy("bottom-right", 100, 100, 90, 90, margin=36)
    assert xy is not None
    assert xy[0] >= 0
    assert xy[1] >= 0
    assert xy[0] + 90 <= 100 + 0.01
    assert xy[1] + 90 <= 100 + 0.01


def test_apply_preset_sets_spins(monkeypatch):
    from src.ui.tabs_advanced import actions_markup as mod

    class Spin:
        def __init__(self, v):
            self._v = float(v)

        def value(self):
            return self._v

        def setValue(self, v):
            self._v = float(v)

        def blockSignals(self, *_a):
            return True

    class Combo:
        def __init__(self):
            self._data = "top-left"
            self._text = "좌상단"

        def currentData(self):
            return self._data

        def currentText(self):
            return self._text

        def blockSignals(self, *_a):
            return True

        def count(self):
            return 1

        def itemData(self, _i):
            return "custom"

        def setCurrentIndex(self, *_a):
            return None

    class Hint:
        def __init__(self):
            self.t = ""

        def setText(self, t):
            self.t = t

    class Dummy:
        def __init__(self):
            self.cmb_tb_preset = Combo()
            self.spn_tb_x = Spin(0)
            self.spn_tb_y = Spin(0)
            self.spn_tb_w = Spin(200)
            self.spn_tb_h = Spin(40)
            self.spn_tb_page = Spin(1)
            self.spn_tb_fontsize = Spin(14)
            self.cmb_tb_color = type("C", (), {"currentData": lambda s: (0, 0, 0)})()
            self.txt_textbox_content = type("T", (), {"text": lambda s: "hi"})()
            self.lbl_tb_drag_hint = Hint()
            self.sel_textbox = type("S", (), {"get_path": lambda s: ""})()
            self.preview_image = None

    d = Dummy()
    mod.action_apply_textbox_preset(d)
    assert abs(d.spn_tb_x.value() - 36.0) < 0.1
    assert abs(d.spn_tb_y.value() - 36.0) < 0.1
    assert "프리셋" in d.lbl_tb_drag_hint.t or "Preset" in d.lbl_tb_drag_hint.t or d.lbl_tb_drag_hint.t
