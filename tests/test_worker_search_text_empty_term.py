import pytest

from _deps import require_pyqt6_and_pymupdf
from src.core.i18n import tm
from src.core.optional_deps import fitz


def _make_pdf(path):
    doc = fitz.open()
    page = doc.new_page(width=300, height=400)
    page.insert_text((72, 72), "HELLO")
    doc.save(str(path))
    doc.close()


def test_search_text_rejects_empty_term(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "search.txt"
    _make_pdf(src)

    worker = WorkerThread(
        "search_text",
        file_path=str(src),
        output_path=str(out),
        search_term="   ",
    )

    errors = []
    worker.error_signal.connect(lambda msg: errors.append(msg))
    worker.search_text()

    assert errors
    assert tm.get("err_search_term_required") in errors[-1]
    assert not out.exists()


def test_preflight_rejects_empty_search_term(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "search.txt"
    _make_pdf(src)

    worker = WorkerThread(
        "search_text",
        file_path=str(src),
        output_path=str(out),
        search_term="",
    )
    errors = []
    worker.error_signal.connect(lambda msg: errors.append(msg))

    worker.run()

    assert errors
    assert tm.get("err_search_term_required") in errors[-1]