import pytest


def _skip_if_missing_deps():
    try:
        import PyQt6  # noqa: F401
        import fitz  # noqa: F401
    except Exception:
        pytest.skip("PyQt6 or PyMuPDF not available")


class _DummyDoc:
    def __init__(self):
        self.closed = False

    def __len__(self):
        return 1

    def close(self):
        self.closed = True


def test_preview_doc_reuse_same_path():
    _skip_if_missing_deps()
    from src.ui.main_window_preview import MainWindowPreviewMixin

    class Dummy(MainWindowPreviewMixin):
        def __init__(self):
            self._current_preview_doc = None
            self._current_preview_path = ""
            self._current_preview_password = None
            self.open_calls = 0
            self.docs = []

        def _open_preview_document(self, _path: str):
            self.open_calls += 1
            doc = _DummyDoc()
            self.docs.append(doc)
            return doc, None

    dummy = Dummy()
    doc1, state1 = dummy._ensure_preview_document("a.pdf")
    doc2, state2 = dummy._ensure_preview_document("a.pdf")

    assert state1 is None
    assert state2 is None
    assert doc1 is doc2
    assert dummy.open_calls == 1


def test_preview_doc_reopen_on_path_change():
    _skip_if_missing_deps()
    from src.ui.main_window_preview import MainWindowPreviewMixin

    class Dummy(MainWindowPreviewMixin):
        def __init__(self):
            self._current_preview_doc = None
            self._current_preview_path = ""
            self._current_preview_password = None
            self.open_calls = 0
            self.docs = []

        def _open_preview_document(self, _path: str):
            self.open_calls += 1
            doc = _DummyDoc()
            self.docs.append(doc)
            return doc, None

    dummy = Dummy()
    first_doc, _ = dummy._ensure_preview_document("a.pdf")
    second_doc, _ = dummy._ensure_preview_document("b.pdf")

    assert dummy.open_calls == 2
    assert first_doc is not second_doc
    assert first_doc.closed is True
