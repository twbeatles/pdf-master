"""텍스트 상자 큐·same-path·영역 교체 UI/Worker 회귀."""

from __future__ import annotations

from src.ui.tabs_advanced import actions_markup as mod
from src.ui.tabs_advanced.markup_actions import deps as _deps


def test_queue_add_and_clear():
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
            self.txt_textbox_content = type("T", (), {"toPlainText": lambda self: "Hello"})()
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
                    "addItem": lambda self, x: self.items.append(x),
                    "items": [],
                },
            )()
            self.lbl_tb_queue_count = type("H", (), {"setText": lambda self, t: setattr(self, "t", t)})()
            self._textbox_queue = []

        def show_toast(self, *a, **k):
            pass

    class Toast:
        def __init__(self, *a, **k):
            pass

        def show_toast(self, *a, **k):
            pass

    # deps 경로 사용 (구현 모듈이 deps.ToastWidget 참조)
    _deps.ToastWidget = Toast  # type: ignore[attr-defined]

    d = Dummy()
    mod.action_textbox_queue_add(d)
    assert len(d._textbox_queue) == 1
    assert d._textbox_queue[0]["text"] == "Hello"
    assert d._textbox_queue[0]["page_num"] == 0

    mod.action_textbox_queue_clear(d)
    assert d._textbox_queue == []


def test_insert_textbox_same_path_skips_dialog(monkeypatch):
    from PyQt6.QtWidgets import QMessageBox

    runs = {}

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
            self.spn_tb_page = Spin(2)
            self.spn_tb_x = Spin(1.0)
            self.spn_tb_y = Spin(2.0)
            self.spn_tb_w = Spin(50.0)
            self.spn_tb_h = Spin(30.0)
            self.spn_tb_fontsize = Spin(12)
            self.cmb_tb_color = type("C", (), {"currentData": lambda self: (0, 0, 0)})()
            self.cmb_tb_font = type("F", (), {"currentData": lambda self: "cjk"})()
            self.spn_tb_opacity = Spin(80)
            self.spn_tb_rotation = Spin(0)
            self.cmb_tb_align = type("A", (), {"currentData": lambda self: 1})()
            self.cmb_tb_layer = type("L", (), {"currentData": lambda self: "foreground"})()
            self.chk_tb_same_path = type("K", (), {"isChecked": lambda self: True})()
            self.chk_tb_keep_placing = type("K", (), {"isChecked": lambda self: True})()
            self.preview_image = None

        def _choose_save_file(self, *a, **k):
            raise AssertionError("save dialog must not open for same-path")

        def run_worker(self, mode, **kwargs):
            runs["mode"] = mode
            runs["kwargs"] = kwargs

    monkeypatch.setattr(
        _deps.QMessageBox,
        "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes),
    )
    monkeypatch.setattr(_deps, "ToastWidget", lambda *a, **k: type("T", (), {"show_toast": lambda *x, **y: None})())
    d = Dummy()
    mod.action_insert_textbox(d)
    assert runs["mode"] == "insert_textbox"
    assert runs["kwargs"]["output_path"] == "D:/a.pdf"
    assert d._textbox_reopen_placement_after_success is True


def test_insert_textboxes_worker(tmp_path):
    from src.core.optional_deps import fitz
    from src.core.worker import WorkerThread

    if fitz is None or not hasattr(fitz, "open") or type(fitz.open).__name__ == "_MissingDependencyCallable":
        import pytest

        pytest.skip("PyMuPDF not available")

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(str(src))
    doc.close()

    worker = WorkerThread(
        "insert_textboxes",
        file_path=str(src),
        output_path=str(out),
        boxes=[
            {
                "page_num": 0,
                "rect": [50, 50, 250, 90],
                "text": "One",
                "fontsize": 14,
                "color": (0, 0, 0),
                "fontname": "helv",
                "opacity": 1.0,
                "rotation": 0,
                "align": 0,
                "layer": "foreground",
            },
            {
                "page_num": 0,
                "rect": [50, 120, 250, 160],
                "text": "Two",
                "fontsize": 14,
                "color": (0, 0, 0),
                "fontname": "helv",
                "opacity": 1.0,
                "rotation": 0,
                "align": 0,
                "layer": "foreground",
            },
        ],
    )
    errors = []
    finished = []
    worker.error_signal.connect(lambda m: errors.append(m))
    worker.finished_signal.connect(lambda m: finished.append(m))
    worker.insert_textboxes()
    assert not errors, errors
    assert finished
    assert out.exists()
    result = fitz.open(str(out))
    try:
        text = result[0].get_text("text")
        assert "One" in text
        assert "Two" in text
    finally:
        result.close()


def test_replace_text_in_rect_worker(tmp_path):
    from src.core.optional_deps import fitz
    from src.core.worker import WorkerThread

    if fitz is None or not hasattr(fitz, "open") or type(fitz.open).__name__ == "_MissingDependencyCallable":
        import pytest

        pytest.skip("PyMuPDF not available")

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "OLDTEXT", fontsize=14)
    doc.save(str(src))
    doc.close()

    worker = WorkerThread(
        "replace_text_in_rect",
        file_path=str(src),
        output_path=str(out),
        page_num=0,
        rect=[60, 50, 200, 100],
        text="NEWTEXT",
        fontsize=14,
        color=(0, 0, 0),
        fontname="helv",
        opacity=1.0,
        rotation=0,
        align=0,
        layer="foreground",
    )
    errors = []
    finished = []
    worker.error_signal.connect(lambda m: errors.append(m))
    worker.finished_signal.connect(lambda m: finished.append(m))
    worker.replace_text_in_rect()
    assert not errors, errors
    assert finished
    result = fitz.open(str(out))
    try:
        text = result[0].get_text("text")
        assert "NEWTEXT" in text
    finally:
        result.close()
