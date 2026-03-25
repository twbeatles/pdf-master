from _deps import require_pyqt6_and_pymupdf
from src.core.i18n import tm
from src.core.optional_deps import fitz


def _make_pdf(path, page_count=1):
    doc = fitz.open()
    for idx in range(page_count):
        page = doc.new_page(width=400, height=400)
        page.insert_text((72, 72), f"PAGE_{idx + 1}")
    doc.save(str(path))
    doc.close()


def test_add_sticky_note_rejects_negative_page_index(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    _make_pdf(src)

    worker = WorkerThread(
        "add_sticky_note",
        file_path=str(src),
        output_path=str(out),
        page_num=-1,
        content="memo",
    )
    errors = []
    worker.error_signal.connect(lambda msg: errors.append(msg))

    worker.add_sticky_note()

    assert errors == [tm.get("err_page_out_of_range", "-1", "1")]
    assert not out.exists()


def test_add_sticky_note_rejects_overflow_page_index(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    _make_pdf(src)

    worker = WorkerThread(
        "add_sticky_note",
        file_path=str(src),
        output_path=str(out),
        page_num=5,
        content="memo",
    )
    errors = []
    worker.error_signal.connect(lambda msg: errors.append(msg))

    worker.add_sticky_note()

    assert errors == [tm.get("err_page_out_of_range", "6", "1")]
    assert not out.exists()


def test_insert_blank_page_rejects_invalid_position(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    _make_pdf(src)

    worker = WorkerThread(
        "insert_blank_page",
        file_path=str(src),
        output_path=str(out),
        position=3,
    )
    errors = []
    worker.error_signal.connect(lambda msg: errors.append(msg))

    worker.insert_blank_page()

    assert errors == [tm.get("err_page_out_of_range", "4", "2")]
    assert not out.exists()


def test_duplicate_page_rejects_invalid_page_number(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    _make_pdf(src)

    worker = WorkerThread(
        "duplicate_page",
        file_path=str(src),
        output_path=str(out),
        page_num=9,
        count=1,
    )
    errors = []
    worker.error_signal.connect(lambda msg: errors.append(msg))

    worker.duplicate_page()

    assert errors == [tm.get("err_page_out_of_range", "10", "1")]
    assert not out.exists()
