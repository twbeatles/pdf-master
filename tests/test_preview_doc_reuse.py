import pytest

from _deps import require_pyqt6


class _DummyDoc:
    def __init__(self):
        self.closed = False

    def status(self):
        from PyQt6.QtPdf import QPdfDocument

        return QPdfDocument.Status.Ready

    def close(self):
        self.closed = True


class _PreviewWidgetStub:
    def __init__(self):
        self.document_value = None
        self.set_calls = []

    def set_document(self, document, path=""):
        self.document_value = document
        self.set_calls.append((document, path))

    def clear(self):
        if self.document_value is not None and hasattr(self.document_value, "close"):
            self.document_value.close()
        self.document_value = None

    def document(self):
        return self.document_value


def test_preview_doc_reuse_same_path():
    require_pyqt6()
    from src.ui.main_window_preview import MainWindowPreviewMixin

    class Dummy(MainWindowPreviewMixin):
        def __init__(self):
            self._current_preview_doc = None
            self._current_preview_path = ""
            self._current_preview_password = None
            self.preview_image = _PreviewWidgetStub()
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
    require_pyqt6()
    from src.ui.main_window_preview import MainWindowPreviewMixin

    class Dummy(MainWindowPreviewMixin):
        def __init__(self):
            self._current_preview_doc = None
            self._current_preview_path = ""
            self._current_preview_password = None
            self.preview_image = _PreviewWidgetStub()
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
