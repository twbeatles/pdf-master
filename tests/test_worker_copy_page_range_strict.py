import pytest

from _deps import require_pyqt6_and_pymupdf
from src.core.optional_deps import fitz


def _make_pdf(path, texts):
    doc = fitz.open()
    for text in texts:
        page = doc.new_page(width=600, height=800)
        page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


def test_copy_page_invalid_range_hard_fails_and_no_output(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    target = tmp_path / "target.pdf"
    source = tmp_path / "source.pdf"
    out = tmp_path / "out.pdf"
    _make_pdf(target, ["TARGET_1"])
    _make_pdf(source, ["SOURCE_1", "SOURCE_2"])

    worker = WorkerThread(
        "copy_page_between_docs",
        file_path=str(target),
        source_path=str(source),
        page_range="abc",
        insert_at=-1,
        output_path=str(out),
    )
    errors = []
    worker.error_signal.connect(lambda msg: errors.append(msg))

    worker.copy_page_between_docs()

    assert errors
    assert any(("페이지 범위" in msg) or ("page range" in msg.lower()) for msg in errors)
    assert not out.exists()


def test_copy_page_valid_range_still_succeeds(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    target = tmp_path / "target.pdf"
    source = tmp_path / "source.pdf"
    out = tmp_path / "out.pdf"
    _make_pdf(target, ["TARGET_1"])
    _make_pdf(source, ["SOURCE_1", "SOURCE_2"])

    worker = WorkerThread(
        "copy_page_between_docs",
        file_path=str(target),
        source_path=str(source),
        page_range="2",
        insert_at=-1,
        output_path=str(out),
    )
    worker.copy_page_between_docs()

    assert out.exists()
    doc = fitz.open(str(out))
    texts = []
    for i in range(len(doc)):
        raw_text = doc[i].get_text()
        texts.append(raw_text.strip() if isinstance(raw_text, str) else "")
    doc.close()

    assert len(texts) == 2
    assert "TARGET_1" in texts[0]
    assert "SOURCE_2" in texts[1]
