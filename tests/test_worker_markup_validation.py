import pytest


def _skip_if_missing_deps():
    try:
        import PyQt6  # noqa: F401
        import fitz  # noqa: F401
    except Exception:
        pytest.skip("PyQt6 or PyMuPDF not available")


def _make_pdf(path):
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=600, height=800)
    page.insert_text((72, 72), "hello markup")
    doc.save(str(path))
    doc.close()


def test_add_text_markup_invalid_type_emits_friendly_error(tmp_path):
    _skip_if_missing_deps()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    _make_pdf(src)

    worker = WorkerThread(
        "add_text_markup",
        file_path=str(src),
        output_path=str(out),
        search_term="hello",
        markup_type="bad_type",
    )
    errors = []
    worker.error_signal.connect(lambda msg: errors.append(msg))

    worker.add_text_markup()

    assert errors
    assert any(("markup" in msg.lower()) or ("마크업" in msg) for msg in errors)
    assert not out.exists()


def test_add_text_markup_valid_type_still_works(tmp_path):
    _skip_if_missing_deps()
    import fitz
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    _make_pdf(src)

    worker = WorkerThread(
        "add_text_markup",
        file_path=str(src),
        output_path=str(out),
        search_term="hello",
        markup_type="underline",
    )
    errors = []
    worker.error_signal.connect(lambda msg: errors.append(msg))

    worker.add_text_markup()

    assert not errors
    assert out.exists()

    doc = fitz.open(str(out))
    try:
        annots = list(doc[0].annots() or [])
        assert annots
    finally:
        doc.close()

