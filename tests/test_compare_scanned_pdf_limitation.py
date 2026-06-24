import pytest

from _deps import require_pyqt6_and_pymupdf
from src.core.optional_deps import fitz


def _make_image_only_pdf(path):
    doc = fitz.open()
    page = doc.new_page(width=200, height=200)
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 80, 40), 1)
    pix.clear_with(255)
    page.insert_image(page.rect, pixmap=pix)
    doc.save(str(path))
    doc.close()


def test_compare_reports_identical_for_image_only_pdfs_with_different_pixels(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    left = tmp_path / "left.pdf"
    right = tmp_path / "right.pdf"
    _make_image_only_pdf(left)
    _make_image_only_pdf(right)

    report_path = tmp_path / "compare.txt"
    worker = WorkerThread(
        "compare_pdfs",
        file_path1=str(left),
        file_path2=str(right),
        output_path=str(report_path),
    )

    worker.compare_pdfs()

    assert report_path.exists()
    assert worker.result_payload.get("diff_count") == 0
    assert worker.result_payload.get("results") == []