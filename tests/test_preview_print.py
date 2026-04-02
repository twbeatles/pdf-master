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


def test_print_pdf_uses_qt_render_pipeline(monkeypatch, tmp_path):
    require_pyqt6_and_pymupdf()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.ui.window_preview import navigation

    src_pdf = tmp_path / "src.pdf"
    _make_pdf(src_pdf, page_count=3)

    real_qprinter = navigation.QPrinter
    real_qprintdialog = navigation.QPrintDialog

    class FakePrinter:
        PrinterMode = real_qprinter.PrinterMode
        PrintRange = real_qprinter.PrintRange
        Unit = real_qprinter.Unit
        last_instance = None

        def __init__(self, *_args, **_kwargs):
            FakePrinter.last_instance = self
            self.doc_name = None
            self.new_page_calls = 0

        def setDocName(self, name):
            self.doc_name = name

        def newPage(self):
            self.new_page_calls += 1
            return True

    class FakeDialog:
        DialogCode = real_qprintdialog.DialogCode

        def __init__(self, printer, _parent):
            self.printer = printer
            self.minmax = None
            self.options = []

        def setMinMax(self, start, end):
            self.minmax = (start, end)

        def setOption(self, option, enabled=True):
            self.options.append((option, enabled))

        def exec(self):
            return self.DialogCode.Accepted

    class FakePainter:
        instances = []

        def __init__(self):
            self.begin_calls = []
            self.ended = False
            FakePainter.instances.append(self)

        def begin(self, printer):
            self.begin_calls.append(printer)
            return True

        def end(self):
            self.ended = True

    rendered_pages = []
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
            self._current_preview_doc = fitz.open(str(src_pdf))
            self._current_preview_page = 1
            self.preview_label = _LabelStub()

        def _ensure_preview_access(self, path):
            assert path == str(src_pdf)
            return True, None

    monkeypatch.setattr(navigation, "QPrinter", FakePrinter)
    monkeypatch.setattr(navigation, "QPrintDialog", FakeDialog)
    monkeypatch.setattr(navigation, "QPainter", FakePainter)
    monkeypatch.setattr(navigation, "ToastWidget", _ToastStub)
    monkeypatch.setattr(navigation, "_collect_print_page_indices", lambda *_args, **_kwargs: [1, 2])
    monkeypatch.setattr(
        navigation,
        "_render_pdf_page_to_printer",
        lambda _printer, _painter, page: rendered_pages.append(page.number),
    )
    monkeypatch.setattr(
        navigation.QMessageBox,
        "warning",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("warning should not be shown")),
    )

    dummy = Dummy()
    try:
        navigation._print_pdf(dummy, str(src_pdf))
    finally:
        dummy._current_preview_doc.close()

    assert FakePrinter.last_instance is not None
    assert FakePrinter.last_instance.doc_name == src_pdf.name
    assert FakePrinter.last_instance.new_page_calls == 1
    assert rendered_pages == [1, 2]
    assert FakePainter.instances and FakePainter.instances[0].ended is True
    assert toasts == [navigation.tm.get("print_completed")]
