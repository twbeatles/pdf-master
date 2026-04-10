import pytest

from _deps import require_pyqt6


class _PathStub:
    def __init__(self, path):
        self._path = path

    def get_path(self):
        return self._path


class _ValueStub:
    def __init__(self, value):
        self._value = value

    def value(self):
        return self._value


class _ComboStub:
    def __init__(self, value):
        self._value = value

    def currentData(self):
        return self._value


def _dummy_adv(pdf_path, sig_path, page_value):
    from src.ui.main_window_tabs_advanced import MainWindowTabsAdvancedMixin

    class Dummy(MainWindowTabsAdvancedMixin):
        def __init__(self):
            self.sel_sig_pdf = _PathStub(pdf_path)
            self.sel_sig_img = _PathStub(sig_path)
            self.spn_sig_page = _ValueStub(page_value)
            self.cmb_sig_pos = _ComboStub("bottom_right")
            self.called = None

        def run_worker(self, mode, **kwargs):
            self.called = (mode, kwargs)

        def _choose_save_file(self, title, default_name, file_filter):
            import src.ui.main_window_tabs_advanced as adv_module

            return adv_module.QFileDialog.getSaveFileName(self, title, default_name, file_filter)

    return Dummy()


def test_normalize_page_input_helper():
    require_pyqt6()
    dummy = _dummy_adv("a.pdf", "b.png", 1)

    assert dummy._normalize_page_input(0, last_page_value=0) == -1
    assert dummy._normalize_page_input(1, last_page_value=0) == 0
    assert dummy._normalize_page_input(3, last_page_value=0) == 2


def test_insert_signature_action_uses_1_based_ui_and_0_based_worker(monkeypatch, tmp_path):
    require_pyqt6()
    import src.ui.main_window_tabs_advanced as adv_module

    pdf = tmp_path / "a.pdf"
    sig = tmp_path / "s.png"
    out = tmp_path / "out.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    sig.write_bytes(b"fake")

    dummy = _dummy_adv(str(pdf), str(sig), page_value=3)

    monkeypatch.setattr(
        adv_module.QFileDialog,
        "getSaveFileName",
        lambda *_args, **_kwargs: (str(out), "PDF (*.pdf)"),
    )
    monkeypatch.setattr(
        adv_module.QMessageBox,
        "warning",
        lambda *_args, **_kwargs: None,
    )

    dummy.action_insert_signature()

    assert dummy.called is not None
    mode, kwargs = dummy.called
    assert mode == "insert_signature"
    assert kwargs["page_num"] == 2

