import os

import pytest

from _deps import require_pyqt6_and_pymupdf
from src.core.optional_deps import fitz


def _make_pdf(path, page_count=3):
    doc = fitz.open()
    for index in range(page_count):
        page = doc.new_page(width=300, height=400)
        page.insert_text((72, 72), f"PAGE_{index + 1}")
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


def test_split_checks_cancellation_inside_page_loop(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import CancelledError, WorkerThread

    src = tmp_path / "src.pdf"
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    _make_pdf(src, page_count=4)

    worker = WorkerThread("split", file_path=str(src), output_dir=str(out_dir), page_range="1-4")
    worker._check_cancelled = _cancel_after(2)

    with pytest.raises(CancelledError):
        worker.split()

    assert not any(out_dir.iterdir())


def test_get_form_fields_checks_cancellation_inside_page_loop(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import CancelledError, WorkerThread

    src = tmp_path / "src.pdf"
    _make_pdf(src, page_count=4)

    worker = WorkerThread("get_form_fields", file_path=str(src))
    worker._check_cancelled = _cancel_after(2)

    with pytest.raises(CancelledError):
        worker.get_form_fields()


def test_fill_form_checks_cancellation_inside_page_loop(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import CancelledError, WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "filled.pdf"
    _make_pdf(src, page_count=4)

    worker = WorkerThread(
        "fill_form",
        file_path=str(src),
        output_path=str(out),
        field_values={"field": "value"},
    )
    worker._check_cancelled = _cancel_after(2)

    with pytest.raises(CancelledError):
        worker.fill_form()

    assert not out.exists()


def test_add_freehand_signature_checks_cancellation_before_save(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import CancelledError, WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "signed.pdf"
    _make_pdf(src, page_count=1)

    worker = WorkerThread(
        "add_freehand_signature",
        file_path=str(src),
        output_path=str(out),
        page_num=0,
        strokes=[
            [[10, 10], [20, 20]],
            [[30, 30], [40, 40]],
        ],
    )
    worker._check_cancelled = _cancel_after(2)

    with pytest.raises(CancelledError):
        worker.add_freehand_signature()

    assert not out.exists()
