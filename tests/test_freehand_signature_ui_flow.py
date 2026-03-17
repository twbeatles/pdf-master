import pytest

from _deps import require_pyqt6


class _ValueStub:
    def __init__(self, value):
        self._value = value

    def value(self):
        return self._value


class _TextStub:
    def __init__(self, text):
        self._text = text

    def text(self):
        return self._text


class _PathStub:
    def __init__(self, path):
        self._path = path

    def get_path(self):
        return self._path


class _ComboStub:
    def __init__(self, value):
        self._value = value

    def currentData(self):
        return self._value


def _build_dummy(path, strokes, page_value=0):
    from src.ui.main_window_tabs_advanced import MainWindowTabsAdvancedMixin

    class Dummy(MainWindowTabsAdvancedMixin):
        def __init__(self):
            self.sel_freehand_pdf = _PathStub(path)
            self.txt_freehand_strokes = _TextStub(strokes)
            self.spn_freehand_page = _ValueStub(page_value)
            self.spn_freehand_width = _ValueStub(3)
            self.cmb_freehand_color = _ComboStub((0, 0, 0))
            self.called = None

        def run_worker(self, mode, **kwargs):
            self.called = (mode, kwargs)

    return Dummy()


def test_parse_freehand_strokes_valid():
    require_pyqt6()
    dummy = _build_dummy("x.pdf", "10,10;20,20|30,30;40,40", page_value=0)

    parsed = dummy._parse_freehand_strokes("10,10;20,20|30,30;40,40")
    assert parsed == [
        [[10.0, 10.0], [20.0, 20.0]],
        [[30.0, 30.0], [40.0, 40.0]],
    ]


def test_parse_freehand_strokes_invalid_raises():
    require_pyqt6()
    dummy = _build_dummy("x.pdf", "10,10", page_value=0)

    with pytest.raises(ValueError):
        dummy._parse_freehand_strokes("10,10")


def test_action_add_freehand_signature_calls_worker_with_normalized_page(monkeypatch, tmp_path):
    require_pyqt6()
    import src.ui.main_window_tabs_advanced as adv_module

    src_pdf = tmp_path / "src.pdf"
    src_pdf.write_bytes(b"%PDF-1.7\n")
    out_pdf = tmp_path / "out.pdf"

    dummy = _build_dummy(str(src_pdf), "10,10;20,20|30,30;40,40", page_value=0)

    monkeypatch.setattr(
        adv_module.QFileDialog,
        "getSaveFileName",
        lambda *_args, **_kwargs: (str(out_pdf), "PDF (*.pdf)"),
    )
    monkeypatch.setattr(
        adv_module.QMessageBox,
        "warning",
        lambda *_args, **_kwargs: None,
    )

    dummy.action_add_freehand_signature()

    assert dummy.called is not None
    mode, kwargs = dummy.called
    assert mode == "add_freehand_signature"
    assert kwargs["page_num"] == -1
    assert kwargs["width"] == 3
    assert kwargs["strokes"]

