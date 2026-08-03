"""미리보기 포커스 모드 토글 단위 검증."""

from __future__ import annotations

from src.ui.window_preview import focus as focus_mod


class _StubWidget:
    def __init__(self):
        self.visible = True

    def setVisible(self, v):
        self.visible = bool(v)


class _StubSplitter:
    def __init__(self):
        self._sizes = [650, 450]
        self.collapsible = False
        self._w = 1100

    def sizes(self):
        return list(self._sizes)

    def setSizes(self, sizes):
        self._sizes = [int(s) for s in sizes]

    def setChildrenCollapsible(self, v):
        self.collapsible = bool(v)

    def width(self):
        return self._w


class _StubBtn:
    def __init__(self):
        self._text = ""
        self._tip = ""

    def setText(self, t):
        self._text = t

    def setToolTip(self, t):
        self._tip = t

    def text(self):
        return self._text


class _StubBar:
    def __init__(self):
        self.visible = False

    def setVisible(self, v):
        self.visible = bool(v)


class _StubPanel:
    def __init__(self):
        self.title = ""

    def setTitle(self, t):
        self.title = t


class _Host:
    def __init__(self):
        self.settings = {"preview_focus_mode": False}
        self.content_splitter = _StubSplitter()
        self._content_left_widget = _StubWidget()
        self._preview_focus_mode = False
        self._splitter_sizes_before_focus = None
        self.btn_preview_focus = _StubBtn()
        self.preview_focus_bar = _StubBar()
        self.preview_panel = _StubPanel()
        self.preview_image = None
        self._saves = 0

    def _schedule_settings_save(self):
        self._saves += 1


def test_toggle_focus_hides_left_and_restores(monkeypatch):
    monkeypatch.setattr(focus_mod.tm, "get", lambda key, *a: key)

    host = _Host()
    focus_mod._set_preview_focus_mode(host, True)
    assert host._preview_focus_mode is True
    assert host._content_left_widget.visible is False
    assert host.preview_focus_bar.visible is True
    assert host.settings["preview_focus_mode"] is True
    assert host._splitter_sizes_before_focus == [650, 450]
    assert host.btn_preview_focus.text() == "btn_preview_focus_exit"

    focus_mod._set_preview_focus_mode(host, False)
    assert host._preview_focus_mode is False
    assert host._content_left_widget.visible is True
    assert host.preview_focus_bar.visible is False
    assert host.content_splitter.sizes() == [650, 450]
    assert host.btn_preview_focus.text() == "btn_preview_focus_enter"


def test_escape_exits_placement_before_focus(monkeypatch):
    monkeypatch.setattr(focus_mod.tm, "get", lambda key, *a: key)

    class Preview:
        def __init__(self):
            self.place = True
            self.region = False
            self._text_placement_overlay = None

        def is_text_placement_mode(self):
            return self.place

        def set_text_placement_mode(self, enabled):
            self.place = bool(enabled)

        def is_region_select_mode(self):
            return self.region

        def set_region_select_mode(self, enabled):
            self.region = bool(enabled)

    host = _Host()
    host.preview_image = Preview()
    focus_mod._set_preview_focus_mode(host, True)

    focus_mod._on_preview_focus_escape(host)
    assert host.preview_image.place is False
    assert host._preview_focus_mode is True

    focus_mod._on_preview_focus_escape(host)
    assert host._preview_focus_mode is False


def test_toggle_cycles_to_fullscreen_flag(monkeypatch):
    """포커스 중 F11은 전체화면 진입을 시도한다 (호스트 생성은 스텁)."""
    monkeypatch.setattr(focus_mod.tm, "get", lambda key, *a: key)
    entered = {"v": False}

    def fake_enter(self):
        entered["v"] = True
        self._preview_fullscreen_host = type(
            "H",
            (),
            {"isVisible": lambda self: True},
        )()

    monkeypatch.setattr(focus_mod, "_enter_preview_fullscreen", fake_enter)
    host = _Host()
    focus_mod._set_preview_focus_mode(host, True)
    focus_mod._toggle_preview_focus_mode(host)
    assert entered["v"] is True
