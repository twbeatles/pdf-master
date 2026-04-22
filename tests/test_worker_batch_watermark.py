import pytest

from _deps import require_pyqt6_and_pymupdf
from src.core.optional_deps import fitz


def _make_pdf(path, text="BASE"):
    doc = fitz.open()
    page = doc.new_page(width=500, height=700)
    page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


def test_batch_watermark_generates_output(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    _make_pdf(src, "ORIGINAL")

    worker = WorkerThread(
        "batch",
        files=[str(src)],
        output_dir=str(tmp_path),
        operation="watermark",
        option="BATCH_WM",
    )

    messages = []
    errors = []
    worker.finished_signal.connect(lambda msg: messages.append(msg))
    worker.error_signal.connect(lambda msg: errors.append(msg))

    worker.batch()

    out = tmp_path / "src_processed.pdf"
    assert out.exists()
    doc = fitz.open(str(out))
    text = doc[0].get_text()
    doc.close()

    assert "BATCH_WM" in text
    assert messages
    assert "1/1" in messages[-1]
    assert not errors


def test_batch_reports_failed_file_reasons(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread
    from src.core.i18n import tm

    src = tmp_path / "ok.pdf"
    _make_pdf(src, "OK")
    missing = tmp_path / "missing.pdf"

    worker = WorkerThread(
        "batch",
        files=[str(src), str(missing)],
        output_dir=str(tmp_path),
        operation="watermark",
        option="WM",
    )

    messages = []
    worker.finished_signal.connect(lambda msg: messages.append(msg))
    worker.batch()

    assert messages
    result = messages[-1]
    assert "1/2" in result
    assert tm.get("msg_batch_failed_header").strip() in result
    assert "missing.pdf" in result


def test_batch_avoids_output_name_collisions_for_same_basename(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    folder_a = tmp_path / "a"
    folder_b = tmp_path / "b"
    folder_a.mkdir()
    folder_b.mkdir()
    first = folder_a / "same.pdf"
    second = folder_b / "same.pdf"
    _make_pdf(first, "FIRST")
    _make_pdf(second, "SECOND")

    worker = WorkerThread(
        "batch",
        files=[str(first), str(second)],
        output_dir=str(tmp_path),
        operation="watermark",
        option="WM",
    )

    worker.batch()

    assert (tmp_path / "same_processed.pdf").exists()
    assert (tmp_path / "same_processed__2.pdf").exists()

