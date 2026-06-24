import pytest

from _deps import require_pyqt6_and_pymupdf
from src.core.i18n import tm
from src.core.optional_deps import fitz


def _make_pdf(path, text="BASE"):
    doc = fitz.open()
    page = doc.new_page(width=500, height=700)
    page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


@pytest.mark.parametrize("operation", ["watermark", "encrypt"])
def test_batch_rejects_missing_option(tmp_path, operation):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    _make_pdf(src, "ORIGINAL")

    worker = WorkerThread(
        "batch",
        files=[str(src)],
        output_dir=str(tmp_path),
        operation=operation,
        option="",
    )

    messages = []
    errors = []
    worker.finished_signal.connect(lambda msg: messages.append(msg))
    worker.error_signal.connect(lambda msg: errors.append(msg))

    worker.batch()

    assert errors
    assert tm.get("err_batch_option_required", operation) in errors[-1]
    assert not messages
    assert not (tmp_path / "src_processed.pdf").exists()


@pytest.mark.parametrize("operation", ["watermark", "encrypt"])
def test_preflight_rejects_missing_batch_option(tmp_path, operation):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    _make_pdf(src)

    worker = WorkerThread(
        "batch",
        files=[str(src)],
        output_dir=str(tmp_path),
        operation=operation,
    )
    errors = []
    worker.error_signal.connect(lambda msg: errors.append(msg))

    worker.run()

    assert errors
    assert tm.get("err_batch_option_required", operation) in errors[-1]