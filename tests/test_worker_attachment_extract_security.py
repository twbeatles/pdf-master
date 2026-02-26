import os

import pytest


def _skip_if_missing_deps():
    try:
        import PyQt6  # noqa: F401
        import fitz  # noqa: F401
    except Exception:
        pytest.skip("PyQt6 or PyMuPDF not available")


def _make_pdf_with_attachments(path):
    import fitz

    doc = fitz.open()
    doc.new_page(width=400, height=400)
    doc.embfile_add("../evil.txt", b"one")
    doc.embfile_add("..\\evil.txt", b"two")
    doc.embfile_add("a?.txt", b"three")
    doc.embfile_add("a*.txt", b"four")
    doc.save(str(path))
    doc.close()


def test_extract_attachments_sanitizes_name_and_stays_in_output_dir(tmp_path):
    _skip_if_missing_deps()
    from src.core.worker import WorkerThread

    src = tmp_path / "with_attach.pdf"
    out_dir = tmp_path / "extract_out"
    _make_pdf_with_attachments(src)

    worker = WorkerThread("extract_attachments", file_path=str(src), output_dir=str(out_dir))
    errors = []
    worker.error_signal.connect(lambda msg: errors.append(msg))
    worker.extract_attachments()

    assert not errors
    files = sorted(p.name for p in out_dir.iterdir() if p.is_file())
    assert files == ["a_.txt", "a__1.txt", "evil.txt", "evil_1.txt"]

    out_dir_abs = out_dir.resolve()
    for name in files:
        p = (out_dir / name).resolve()
        assert os.path.commonpath([str(out_dir_abs), str(p)]) == str(out_dir_abs)
