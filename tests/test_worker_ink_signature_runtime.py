from _deps import require_pyqt6_and_pymupdf
from src.core.i18n import tm
from src.core.optional_deps import fitz


def _make_pdf(path, page_count=1):
    doc = fitz.open()
    for idx in range(page_count):
        page = doc.new_page(width=500, height=700)
        page.insert_text((72, 72), f"PAGE_{idx + 1}")
    doc.save(str(path))
    doc.close()


def _make_png(path):
    doc = fitz.open()
    doc.new_page(width=40, height=20)
    pix = doc[0].get_pixmap()
    pix.save(str(path))
    doc.close()


def test_add_ink_annotation_saves_annotation(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    _make_pdf(src)

    worker = WorkerThread(
        "add_ink_annotation",
        file_path=str(src),
        output_path=str(out),
        page_num=0,
        points=[[10, 10], [30, 40], [60, 20]],
        color=(0, 0, 1),
        width=2,
    )
    errors = []
    worker.error_signal.connect(lambda msg: errors.append(msg))

    worker.add_ink_annotation()

    assert not errors
    doc = fitz.open(str(out))
    assert doc[0].first_annot is not None
    doc.close()


def test_add_freehand_signature_saves_annotation_on_last_page_sentinel(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    _make_pdf(src, page_count=2)

    worker = WorkerThread(
        "add_freehand_signature",
        file_path=str(src),
        output_path=str(out),
        page_num=-1,
        strokes=[[[10, 10], [30, 40]], [[50, 50], [80, 30]]],
        color=(0, 0, 0),
        width=3,
    )
    errors = []
    worker.error_signal.connect(lambda msg: errors.append(msg))

    worker.add_freehand_signature()

    assert not errors
    doc = fitz.open(str(out))
    assert doc[0].first_annot is None
    assert doc[1].first_annot is not None
    doc.close()


def test_add_ink_annotation_invalid_points_emit_friendly_error(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    _make_pdf(src)

    worker = WorkerThread(
        "add_ink_annotation",
        file_path=str(src),
        output_path=str(out),
        page_num=0,
        points=[["bad", "value"], [10, 20]],
    )
    errors = []
    worker.error_signal.connect(lambda msg: errors.append(msg))

    worker.add_ink_annotation()

    assert errors == [tm.get("msg_invalid_stroke_format")]
    assert not out.exists()


def test_insert_signature_last_page_sentinel_targets_last_page(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    sig = tmp_path / "sig.png"
    out = tmp_path / "out.pdf"
    _make_pdf(src, page_count=2)
    _make_png(sig)

    worker = WorkerThread(
        "insert_signature",
        file_path=str(src),
        output_path=str(out),
        signature_path=str(sig),
        page_num=-1,
        position="bottom_right",
    )
    errors = []
    worker.error_signal.connect(lambda msg: errors.append(msg))

    worker.insert_signature()

    assert not errors
    doc = fitz.open(str(out))
    assert not doc[0].get_images(full=True)
    assert doc[1].get_images(full=True)
    doc.close()
