import os
import pytest

from _deps import require_pyqt6_and_pymupdf
from src.core.optional_deps import fitz


def _make_pdf(path):
    doc = fitz.open()
    doc.new_page()
    doc.save(str(path))
    doc.close()


def _make_png(path):
    doc = fitz.open()
    doc.new_page(width=20, height=20)
    pix = doc[0].get_pixmap()
    pix.save(str(path))
    doc.close()


def test_preflight_rejects_missing_pdf_before_run(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    out = tmp_path / "out.pdf"
    worker = WorkerThread(
        "rotate",
        file_path=str(tmp_path / "missing.pdf"),
        output_path=str(out),
        angle=90,
    )
    errors = []
    worker.error_signal.connect(lambda msg: errors.append(msg))

    worker.run()

    assert errors
    assert any(("not found" in m.lower()) or ("찾을 수 없습니다" in m) for m in errors)
    assert not out.exists()


def test_preflight_rejects_oversized_non_pdf_input(tmp_path, monkeypatch):
    require_pyqt6_and_pymupdf()
    from src.core.constants import MAX_FILE_SIZE
    from src.core.worker import WorkerThread

    pdf = tmp_path / "src.pdf"
    sig = tmp_path / "sig.png"
    out = tmp_path / "out.pdf"
    _make_pdf(pdf)
    _make_png(sig)

    real_getsize = os.path.getsize

    def fake_getsize(path):
        if str(path) == str(sig):
            return MAX_FILE_SIZE + 1
        return real_getsize(path)

    monkeypatch.setattr(os.path, "getsize", fake_getsize)

    worker = WorkerThread(
        "insert_signature",
        file_path=str(pdf),
        signature_path=str(sig),
        output_path=str(out),
    )
    errors = []
    worker.error_signal.connect(lambda msg: errors.append(msg))

    worker.run()

    assert errors
    assert any(("max" in m.lower()) or ("최대" in m) for m in errors)
    assert not out.exists()


def test_preflight_rejects_too_small_pdf(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    tiny_pdf = tmp_path / "tiny.pdf"
    tiny_pdf.write_bytes(b"%PDF-1.7\n")
    out = tmp_path / "out.pdf"

    worker = WorkerThread(
        "rotate",
        file_path=str(tiny_pdf),
        output_path=str(out),
        angle=90,
    )
    errors = []
    worker.error_signal.connect(lambda msg: errors.append(msg))

    worker.run()

    assert errors
    assert any(("small" in m.lower()) or ("작" in m) for m in errors)
    assert not out.exists()


def test_preflight_rejects_missing_required_kwargs(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    _make_pdf(src)

    worker = WorkerThread(
        "delete_pages",
        file_path=str(src),
        output_path=str(out),
    )
    errors = []
    worker.error_signal.connect(lambda msg: errors.append(msg))

    worker.run()

    assert errors
    assert any("page_range" in m for m in errors)
    assert not out.exists()
