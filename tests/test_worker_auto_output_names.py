import os

from _deps import require_pyqt6_and_pymupdf
from src.core.optional_deps import fitz


def _make_pdf(path, text):
    doc = fitz.open()
    page = doc.new_page(width=400, height=400)
    page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


def test_convert_to_img_avoids_same_basename_collisions(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    first_dir = tmp_path / "a"
    second_dir = tmp_path / "b"
    out_dir = tmp_path / "img_out"
    first_dir.mkdir()
    second_dir.mkdir()
    out_dir.mkdir()

    pdf1 = first_dir / "same.pdf"
    pdf2 = second_dir / "same.pdf"
    _make_pdf(pdf1, "FIRST")
    _make_pdf(pdf2, "SECOND")

    worker = WorkerThread(
        "convert_to_img",
        file_paths=[str(pdf1), str(pdf2)],
        output_dir=str(out_dir),
        fmt="png",
        dpi=72,
    )
    errors = []
    worker.error_signal.connect(lambda msg: errors.append(msg))

    worker.convert_to_img()

    assert not errors
    files = sorted(p.name for p in out_dir.iterdir() if p.is_file())
    assert files == ["same__2_p001.png", "same_p001.png"]
    for name in files:
        assert (out_dir / name).stat().st_size > 0


def test_extract_text_avoids_existing_and_same_run_collisions(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    first_dir = tmp_path / "a"
    second_dir = tmp_path / "b"
    out_dir = tmp_path / "text_out"
    first_dir.mkdir()
    second_dir.mkdir()
    out_dir.mkdir()

    pdf1 = first_dir / "same.pdf"
    pdf2 = second_dir / "same.pdf"
    _make_pdf(pdf1, "FIRST")
    _make_pdf(pdf2, "SECOND")
    (out_dir / "same.txt").write_text("existing", encoding="utf-8")

    worker = WorkerThread(
        "extract_text",
        file_paths=[str(pdf1), str(pdf2)],
        output_dir=str(out_dir),
    )
    errors = []
    worker.error_signal.connect(lambda msg: errors.append(msg))

    worker.extract_text()

    assert not errors
    files = sorted(p.name for p in out_dir.iterdir() if p.is_file())
    assert files == ["same.txt", "same__2.txt", "same__3.txt"]
    assert "FIRST" in (out_dir / "same__2.txt").read_text(encoding="utf-8")
    assert "SECOND" in (out_dir / "same__3.txt").read_text(encoding="utf-8")
