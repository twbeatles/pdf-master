import pytest

from _deps import require_pyqt6_and_pymupdf
from src.core.optional_deps import fitz


def _make_pdf(path, page_count: int):
    doc = fitz.open()
    for index in range(page_count):
        page = doc.new_page(width=300, height=400)
        page.insert_text((72, 72), f"PAGE_{index + 1}")
    doc.save(str(path))
    doc.close()


def _page_rotations(path):
    doc = fitz.open(str(path))
    try:
        return [doc[i].rotation for i in range(len(doc))]
    finally:
        doc.close()


def test_rotate_only_selected_pages(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "rotated_selected.pdf"
    _make_pdf(src, page_count=3)

    worker = WorkerThread(
        "rotate",
        file_path=str(src),
        output_path=str(out),
        angle=90,
        page_indices=[1, 1],
    )

    worker.run()

    assert _page_rotations(out) == [0, 90, 0]


def test_rotate_all_pages_when_page_indices_missing(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "rotated_all.pdf"
    _make_pdf(src, page_count=2)

    worker = WorkerThread(
        "rotate",
        file_path=str(src),
        output_path=str(out),
        angle=180,
    )

    worker.run()

    assert _page_rotations(out) == [180, 180]
