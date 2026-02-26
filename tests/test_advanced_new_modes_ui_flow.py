import pytest


def _skip_if_missing_deps():
    try:
        import PyQt6  # noqa: F401
    except Exception:
        pytest.skip("PyQt6 not available")


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
    def __init__(self, text):
        self._text = text

    def text(self):
        return self._text


class _PlainTextStub:
    def __init__(self, text):
        self._text = text

    def toPlainText(self):
        return self._text


def _dummy_for_replace(target_path, source_path, target_page=3, source_page=1):
    from src.ui.main_window_tabs_advanced import MainWindowTabsAdvancedMixin

    class Dummy(MainWindowTabsAdvancedMixin):
        def __init__(self):
            self.sel_replace_target = _PathStub(target_path)
            self.sel_replace_source = _PathStub(source_path)
            self.spn_replace_target_page = _ValueStub(target_page)
            self.spn_replace_source_page = _ValueStub(source_page)
            self.called = None

        def run_worker(self, mode, **kwargs):
            self.called = (mode, kwargs)

    return Dummy()


def _dummy_for_set_bookmarks(pdf_path, text):
    from src.ui.main_window_tabs_advanced import MainWindowTabsAdvancedMixin

    class Dummy(MainWindowTabsAdvancedMixin):
        def __init__(self):
            self.sel_set_bookmarks = _PathStub(pdf_path)
            self.txt_set_bookmarks = _PlainTextStub(text)
            self.called = None

        def run_worker(self, mode, **kwargs):
            self.called = (mode, kwargs)

    return Dummy()


def _dummy_for_add_annotation(pdf_path, annot_type, text, page, point_text, rect_text):
    from src.ui.main_window_tabs_advanced import MainWindowTabsAdvancedMixin

    class Dummy(MainWindowTabsAdvancedMixin):
        def __init__(self):
            self.sel_add_annot = _PathStub(pdf_path)
            self.cmb_add_annot_type = _ComboStub(annot_type)
            self.txt_add_annot_text = _TextStub(text)
            self.spn_add_annot_page = _ValueStub(page)
            self.txt_add_annot_point = _TextStub(point_text)
            self.txt_add_annot_rect = _TextStub(rect_text)
            self.called = None

        def run_worker(self, mode, **kwargs):
            self.called = (mode, kwargs)

    return Dummy()


def test_parse_bookmark_lines_accepts_level_title_page_and_rejects_invalid():
    _skip_if_missing_deps()
    dummy = _dummy_for_set_bookmarks("x.pdf", "1|Intro|1")

    assert dummy._parse_bookmark_lines("1|Intro|1\n2|Background|3") == [
        [1, "Intro", 1],
        [2, "Background", 3],
    ]
    with pytest.raises(ValueError):
        dummy._parse_bookmark_lines("bad-format")


def test_action_replace_page_calls_worker_with_expected_payload(monkeypatch, tmp_path):
    _skip_if_missing_deps()
    import src.ui.main_window_tabs_advanced as adv_module

    target = tmp_path / "target.pdf"
    source = tmp_path / "source.pdf"
    out = tmp_path / "out.pdf"
    target.write_bytes(b"%PDF-1.7\n")
    source.write_bytes(b"%PDF-1.7\n")
    dummy = _dummy_for_replace(str(target), str(source), target_page=4, source_page=2)

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

    dummy.action_replace_page()

    assert dummy.called is not None
    mode, kwargs = dummy.called
    assert mode == "replace_page"
    assert kwargs["file_path"] == str(target)
    assert kwargs["replace_path"] == str(source)
    assert kwargs["target_page"] == 4
    assert kwargs["source_page"] == 2


def test_action_set_bookmarks_calls_worker_with_parsed_bookmarks(monkeypatch, tmp_path):
    _skip_if_missing_deps()
    import src.ui.main_window_tabs_advanced as adv_module

    pdf = tmp_path / "src.pdf"
    out = tmp_path / "bookmarks_out.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    dummy = _dummy_for_set_bookmarks(str(pdf), "1|Intro|1\n2|Details|2")

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

    dummy.action_set_bookmarks()

    assert dummy.called is not None
    mode, kwargs = dummy.called
    assert mode == "set_bookmarks"
    assert kwargs["bookmarks"] == [[1, "Intro", 1], [2, "Details", 2]]


def test_action_add_annotation_basic_text_mode_payload(monkeypatch, tmp_path):
    _skip_if_missing_deps()
    import src.ui.main_window_tabs_advanced as adv_module

    pdf = tmp_path / "src.pdf"
    out = tmp_path / "annot_out.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    dummy = _dummy_for_add_annotation(
        str(pdf),
        annot_type="text",
        text="note",
        page=2,
        point_text="120,240",
        rect_text="",
    )

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

    dummy.action_add_annotation_basic()

    assert dummy.called is not None
    mode, kwargs = dummy.called
    assert mode == "add_annotation"
    assert kwargs["page_num"] == 1
    assert kwargs["annot_type"] == "text"
    assert kwargs["point"] == [120.0, 240.0]


def test_action_add_annotation_basic_freetext_mode_payload(monkeypatch, tmp_path):
    _skip_if_missing_deps()
    import src.ui.main_window_tabs_advanced as adv_module

    pdf = tmp_path / "src.pdf"
    out = tmp_path / "annot_out.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    dummy = _dummy_for_add_annotation(
        str(pdf),
        annot_type="freetext",
        text="box note",
        page=1,
        point_text="",
        rect_text="10,20,210,120",
    )

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

    dummy.action_add_annotation_basic()

    assert dummy.called is not None
    mode, kwargs = dummy.called
    assert mode == "add_annotation"
    assert kwargs["annot_type"] == "freetext"
    assert kwargs["rect"] == [10.0, 20.0, 210.0, 120.0]
