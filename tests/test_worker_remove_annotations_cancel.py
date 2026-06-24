import pytest

from _deps import require_pyqt6_and_pymupdf
from src.core.optional_deps import fitz


def _make_pdf_with_annotations(path, page_count=4):
    doc = fitz.open()
    for index in range(page_count):
        page = doc.new_page(width=300, height=400)
        page.insert_text((72, 72), f"PAGE_{index + 1}")
        annot = page.add_text_annot((72, 72), f"NOTE_{index + 1}")
        annot.update()
    doc.save(str(path))
    doc.close()


def _cancel_after(call_limit):
    calls = {"count": 0}

    def _inner():
        calls["count"] += 1
        if calls["count"] >= call_limit:
            from src.core.worker import CancelledError

            raise CancelledError("cancel")

    return _inner


def test_remove_annotations_checks_cancellation_inside_page_loop(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import CancelledError, WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "clean.pdf"
    _make_pdf_with_annotations(src, page_count=4)

    worker = WorkerThread("remove_annotations", file_path=str(src), output_path=str(out))
    worker._check_cancelled = _cancel_after(2)

    with pytest.raises(CancelledError):
        worker.remove_annotations()

    assert not out.exists()