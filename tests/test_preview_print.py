import os

from _deps import require_pyqt6_and_pymupdf
from src.core.optional_deps import fitz


def _make_pdf(path, page_count=3):
    doc = fitz.open()
    for index in range(page_count):
        page = doc.new_page(width=300, height=400)
        page.insert_text((72, 72), f"PAGE_{index + 1}")
    doc.save(str(path))
    doc.close()


class _PageRangesStub:
    def __init__(self, ranges):
        self._ranges = ranges

    def isEmpty(self):
        return not self._ranges

    def toRangeList(self):
        return list(self._ranges)


class _RangeStub:
    def __init__(self, start, end):
        self._start = start
        self._end = end

    def from_(self):
        return self._start

    def to(self):
        return self._end


def test_collect_print_page_indices_respects_page_ranges():
    require_pyqt6_and_pymupdf()
    import src.ui.window_preview.navigation as navigation

    class _PrinterStub:
        def printRange(self):
            return navigation.QPrinter.PrintRange.PageRange

        def pageRanges(self):
            return _PageRangesStub([_RangeStub(2, 3)])

        def fromPage(self):
            return 1

        def toPage(self):
            return 3

    assert navigation._collect_print_page_indices(_PrinterStub(), total_pages=5, current_page_index=0) == [1, 2]


def test_collect_print_page_indices_respects_current_page():
    require_pyqt6_and_pymupdf()
    import src.ui.window_preview.navigation as navigation

    class _PrinterStub:
        def printRange(self):
            return navigation.QPrinter.PrintRange.CurrentPage

    assert navigation._collect_print_page_indices(_PrinterStub(), total_pages=5, current_page_index=3) == [3]


def test_print_pdf_uses_qt_preview_pipeline(monkeypatch, tmp_path):
    require_pyqt6_and_pymupdf()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.ui.window_preview import navigation

    src_pdf = tmp_path / "src.pdf"
    _make_pdf(src_pdf, page_count=3)

    real_qprinter = navigation.QPrinter
    real_preview = navigation.QPrintPreviewDialog

    class FakePrinter:
        PrinterMode = real_qprinter.PrinterMode
        PrintRange = real_qprinter.PrintRange
        Unit = real_qprinter.Unit
        last_instance = None

        def __init__(self, *_args, **_kwargs):
            FakePrinter.last_instance = self
            self.doc_name = None

        def setDocName(self, name):
            self.doc_name = name

    class _SignalStub:
        def __init__(self):
            self.callback = None

        def connect(self, callback):
            self.callback = callback

    class FakeDialog:
        DialogCode = real_preview.DialogCode

        def __init__(self, printer, _parent):
            self.printer = printer
            self.paintRequested = _SignalStub()

        def setWindowTitle(self, _title):
            return None

        def exec(self):
            assert self.paintRequested.callback is not None
            self.paintRequested.callback(self.printer)
            return self.DialogCode.Accepted

    rendered = []
    toasts = []

    class _ToastStub:
        def __init__(self, message, **_kwargs):
            self.message = message

        def show_toast(self, _parent):
            toasts.append(self.message)

    class _LabelStub:
        def text(self):
            return "preview"

    class Dummy:
        def __init__(self):
            self._current_preview_page = 1
            self.preview_label = _LabelStub()

        def _ensure_preview_access(self, path):
            assert path == str(src_pdf)
            return True, None

    monkeypatch.setattr(navigation, "QPrinter", FakePrinter)
    monkeypatch.setattr(navigation, "QPrintPreviewDialog", FakeDialog)
    monkeypatch.setattr(navigation, "ToastWidget", _ToastStub)
    monkeypatch.setattr(
        navigation,
        "_paint_pdf_document",
        lambda _printer, path, password, current_page: rendered.append((path, password, current_page)),
    )
    monkeypatch.setattr(
        navigation.QMessageBox,
        "warning",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("warning should not be shown")),
    )

    dummy = Dummy()
    navigation._print_pdf(dummy, str(src_pdf))

    assert FakePrinter.last_instance is not None
    assert FakePrinter.last_instance.doc_name == src_pdf.name
    assert rendered == [(str(src_pdf), None, 1)]
    assert toasts == [navigation.tm.get("print_completed")]


def test_open_page_setup_uses_dialog(monkeypatch):
    require_pyqt6_and_pymupdf()
    import src.ui.window_preview.navigation as navigation

    real_qprinter = navigation.QPrinter

    class FakePrinter:
        PrinterMode = real_qprinter.PrinterMode

        def __init__(self, *_args, **_kwargs):
            return None

    called = {"count": 0}

    class FakeDialog:
        def __init__(self, printer, parent):
            assert printer is not None
            assert parent is not None

        def exec(self):
            called["count"] += 1
            return 1

    class Dummy:
        _current_preview_path = "sample.pdf"
        _preview_printer = None

    monkeypatch.setattr(navigation, "QPrinter", FakePrinter)
    monkeypatch.setattr(navigation, "QPageSetupDialog", FakeDialog)
    monkeypatch.setattr(
        navigation.QMessageBox,
        "warning",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("warning should not be shown")),
    )

    dummy = Dummy()
    navigation._open_page_setup(dummy)
    assert called["count"] == 1


def test_create_preview_printer_uses_fresh_instance_and_copies_setup(monkeypatch):
    require_pyqt6_and_pymupdf()
    import src.ui.window_preview.navigation as navigation

    real_qprinter = navigation.QPrinter

    created = []
    copied = []

    class FakePrinter:
        PrinterMode = real_qprinter.PrinterMode

        def __init__(self, *_args, **_kwargs):
            created.append(self)

    class Dummy:
        def __init__(self):
            self._preview_printer = object()

    monkeypatch.setattr(navigation, "QPrinter", FakePrinter)
    monkeypatch.setattr(
        navigation,
        "_copy_printer_setup_state",
        lambda source, target: copied.append((source, target)),
    )

    dummy = Dummy()
    printer = navigation._create_preview_printer(dummy)

    assert printer is created[0]
    assert printer is not dummy._preview_printer
    assert copied == [(dummy._preview_printer, printer)]
