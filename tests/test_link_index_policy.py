import pytest


def _skip_if_missing_deps():
    try:
        import PyQt6  # noqa: F401
        import fitz  # noqa: F401
    except Exception:
        pytest.skip("PyQt6 or PyMuPDF not available")


def _make_pdf(path, texts):
    import fitz

    doc = fitz.open()
    for text in texts:
        page = doc.new_page(width=600, height=800)
        page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


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


class _TextStub:
    def __init__(self, value):
        self._value = value

    def text(self):
        return self._value


def _build_dummy_for_page_link(pdf_path):
    from src.ui.main_window_tabs_advanced import MainWindowTabsAdvancedMixin

    class Dummy(MainWindowTabsAdvancedMixin):
        def __init__(self):
            self.sel_link = _PathStub(pdf_path)
            self.cmb_link_type = _ComboStub("page")
            self.spn_link_page = _ValueStub(2)
            self.spn_link_target = _ValueStub(3)
            self.txt_link_area = _TextStub("10,10,110,40")
            self.txt_link_url = _TextStub("")
            self.called = None

        def run_worker(self, mode, **kwargs):
            self.called = (mode, kwargs)

    return Dummy()


def test_action_add_hyperlink_normalizes_ui_target_to_zero_based(monkeypatch, tmp_path):
    _skip_if_missing_deps()
    import src.ui.main_window_tabs_advanced as adv_module

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    src.write_bytes(b"%PDF-1.7\n")

    dummy = _build_dummy_for_page_link(str(src))

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

    dummy.action_add_hyperlink()

    assert dummy.called is not None
    mode, kwargs = dummy.called
    assert mode == "add_link"
    assert kwargs["link_type"] == "page"
    assert kwargs["page_num"] == 1
    assert kwargs["target"] == 2


def test_worker_add_link_rejects_out_of_range_target_under_zero_based_policy(tmp_path):
    _skip_if_missing_deps()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    _make_pdf(src, ["P1", "P2"])

    worker = WorkerThread(
        "add_link",
        file_path=str(src),
        output_path=str(out),
        page_num=0,
        link_type="goto",
        target=2,
        rect=[50, 50, 150, 80],
    )
    errors = []
    worker.error_signal.connect(lambda msg: errors.append(msg))
    worker.add_link()

    assert errors
    assert any(("0-based" in msg) or ("페이지" in msg) for msg in errors)
    assert not out.exists()
