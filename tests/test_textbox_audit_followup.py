"""PROJECT_AUDIT 2026-08-03 후속 — 플래그 리셋·큐 경로·same-path 확인."""

from __future__ import annotations

from PyQt6.QtWidgets import QMessageBox

from src.ui.tabs_advanced import actions_markup as mod
from src.ui.tabs_advanced.markup_actions import deps as _deps


def test_clear_textbox_post_flags():
    class Dummy:
        def __init__(self):
            self._textbox_reopen_placement_after_success = True
            self._textbox_clear_queue_after_success = True

    d = Dummy()
    mod._clear_textbox_post_flags(d)
    assert d._textbox_reopen_placement_after_success is False
    assert d._textbox_clear_queue_after_success is False


def test_queue_add_stores_file_path(monkeypatch):
    class Spin:
        def __init__(self, v):
            self._v = v

        def value(self):
            return self._v

        def setValue(self, v):
            self._v = v

    class Dummy:
        def __init__(self):
            self.sel_textbox = type("S", (), {"get_path": lambda self: "D:/docs/a.pdf"})()
            self.txt_textbox_content = type("T", (), {"toPlainText": lambda self: "Hi"})()
            self.spn_tb_page = Spin(1)
            self.spn_tb_x = Spin(10.0)
            self.spn_tb_y = Spin(20.0)
            self.spn_tb_w = Spin(100.0)
            self.spn_tb_h = Spin(40.0)
            self.spn_tb_fontsize = Spin(14)
            self.cmb_tb_color = type("C", (), {"currentData": lambda self: (0, 0, 0)})()
            self.cmb_tb_font = type("F", (), {"currentData": lambda self: "helv"})()
            self.spn_tb_opacity = Spin(100)
            self.spn_tb_rotation = Spin(0)
            self.cmb_tb_align = type("A", (), {"currentData": lambda self: 0})()
            self.cmb_tb_layer = type("L", (), {"currentData": lambda self: "foreground"})()
            self.lst_tb_queue = type(
                "List",
                (),
                {
                    "clear": lambda self: setattr(self, "items", []),
                    "addItem": lambda self, x: getattr(self, "items", []).append(x)
                    if hasattr(self, "items")
                    else setattr(self, "items", [x]),
                    "items": [],
                },
            )()
            self.lbl_tb_queue_count = type("H", (), {"setText": lambda self, t: None})()
            self._textbox_queue = []

    monkeypatch.setattr(
        _deps,
        "ToastWidget",
        lambda *a, **k: type("T", (), {"show_toast": lambda *x, **y: None})(),
    )
    d = Dummy()
    mod.action_textbox_queue_add(d)
    assert d._textbox_queue[0]["file_path"] == "D:/docs/a.pdf"


def test_queue_commit_rejects_path_mismatch(monkeypatch):
    warnings = []

    class Dummy:
        def __init__(self):
            self.sel_textbox = type("S", (), {"get_path": lambda self: "D:/other.pdf"})()
            self._textbox_queue = [
                {
                    "file_path": "D:/docs/a.pdf",
                    "page_num": 0,
                    "rect": [0, 0, 10, 10],
                    "text": "x",
                }
            ]
            self.lst_tb_queue = None
            self.lbl_tb_queue_count = None

        def run_worker(self, *a, **k):
            raise AssertionError("must not run when paths mismatch")

    monkeypatch.setattr(
        _deps.QMessageBox,
        "warning",
        staticmethod(lambda *a, **k: warnings.append(a) or QMessageBox.StandardButton.Ok),
    )
    mod.action_textbox_queue_commit(Dummy())
    assert warnings


def test_same_path_requires_confirm(monkeypatch):
    runs = {}
    answers = {"n": 0}

    def question(*a, **k):
        answers["n"] += 1
        return QMessageBox.StandardButton.Yes

    class Spin:
        def __init__(self, v):
            self._v = v

        def value(self):
            return self._v

        def setValue(self, v):
            self._v = v

    class Dummy:
        def __init__(self):
            self.sel_textbox = type("S", (), {"get_path": lambda self: "D:/a.pdf"})()
            self.txt_textbox_content = type("T", (), {"toPlainText": lambda self: "Hi"})()
            self.spn_tb_page = Spin(1)
            self.spn_tb_x = Spin(1.0)
            self.spn_tb_y = Spin(2.0)
            self.spn_tb_w = Spin(50.0)
            self.spn_tb_h = Spin(30.0)
            self.spn_tb_fontsize = Spin(12)
            self.cmb_tb_color = type("C", (), {"currentData": lambda self: (0, 0, 0)})()
            self.cmb_tb_font = type("F", (), {"currentData": lambda self: "cjk"})()
            self.spn_tb_opacity = Spin(100)
            self.spn_tb_rotation = Spin(0)
            self.cmb_tb_align = type("A", (), {"currentData": lambda self: 0})()
            self.cmb_tb_layer = type("L", (), {"currentData": lambda self: "foreground"})()
            self.chk_tb_same_path = type("K", (), {"isChecked": lambda self: True})()
            self.chk_tb_keep_placing = type("K", (), {"isChecked": lambda self: False})()
            self.preview_image = None

        def _choose_save_file(self, *a, **k):
            raise AssertionError("dialog must not open")

        def run_worker(self, mode, **kwargs):
            runs["mode"] = mode
            runs["kwargs"] = kwargs

    monkeypatch.setattr(_deps.QMessageBox, "question", staticmethod(question))
    monkeypatch.setattr(
        _deps,
        "ToastWidget",
        lambda *a, **k: type("T", (), {"show_toast": lambda *x, **y: None})(),
    )
    mod.action_insert_textbox(Dummy())
    assert answers["n"] >= 1
    assert runs["kwargs"]["output_path"] == "D:/a.pdf"


def test_same_path_cancel_skips_worker(monkeypatch):
    runs = []

    class Spin:
        def __init__(self, v):
            self._v = v

        def value(self):
            return self._v

        def setValue(self, v):
            self._v = v

    class Dummy:
        def __init__(self):
            self.sel_textbox = type("S", (), {"get_path": lambda self: "D:/a.pdf"})()
            self.txt_textbox_content = type("T", (), {"toPlainText": lambda self: "Hi"})()
            self.spn_tb_page = Spin(1)
            self.spn_tb_x = Spin(1.0)
            self.spn_tb_y = Spin(2.0)
            self.spn_tb_w = Spin(50.0)
            self.spn_tb_h = Spin(30.0)
            self.spn_tb_fontsize = Spin(12)
            self.cmb_tb_color = type("C", (), {"currentData": lambda self: (0, 0, 0)})()
            self.cmb_tb_font = type("F", (), {"currentData": lambda self: "cjk"})()
            self.spn_tb_opacity = Spin(100)
            self.spn_tb_rotation = Spin(0)
            self.cmb_tb_align = type("A", (), {"currentData": lambda self: 0})()
            self.cmb_tb_layer = type("L", (), {"currentData": lambda self: "foreground"})()
            self.chk_tb_same_path = type("K", (), {"isChecked": lambda self: True})()
            self.chk_tb_keep_placing = type("K", (), {"isChecked": lambda self: False})()
            self.preview_image = None

        def run_worker(self, *a, **k):
            runs.append(1)

    monkeypatch.setattr(
        _deps.QMessageBox,
        "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No),
    )
    mod.action_insert_textbox(Dummy())
    assert runs == []


def test_set_ui_busy_disables_focus_and_host_actions():
    from src.ui.window_worker import lifecycle as life

    class Btn:
        def __init__(self):
            self.enabled = True

        def setEnabled(self, v):
            self.enabled = bool(v)

    class Host:
        def __init__(self):
            self.enabled = True

        def set_actions_enabled(self, v):
            self.enabled = bool(v)

    class App:
        def __init__(self):
            self.tabs = Btn()
            self.btn_open_folder = Btn()
            self._app_shortcuts = []
            self._menu_open_action = None
            self.btn_focus_place_textbox = Btn()
            self.btn_focus_insert_textbox = Btn()
            self.b_tb_drag = Btn()
            self.btn_preview_focus = Btn()
            self._preview_fullscreen_host = Host()

        def setEnabled_tabs(self, v):
            self.tabs.setEnabled(v)

    # tabs needs setEnabled
    app = App()
    app.tabs.setEnabled = app.tabs.setEnabled  # already
    life.set_ui_busy(app, True)
    assert app.btn_focus_insert_textbox.enabled is False
    assert app._preview_fullscreen_host.enabled is False
    life.set_ui_busy(app, False)
    assert app.btn_focus_insert_textbox.enabled is True
