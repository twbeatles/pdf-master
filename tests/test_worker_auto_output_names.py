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


def test_convert_to_img_routes_through_atomic_pixmap_save(tmp_path, monkeypatch):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out_dir = tmp_path / "img_out"
    out_dir.mkdir()
    _make_pdf(src, "IMG")

    calls = []
    original = WorkerThread._atomic_pixmap_save

    def spy_atomic_pixmap_save(self, pixmap, output_path):
        calls.append(output_path)
        return original(self, pixmap, output_path)

    monkeypatch.setattr(WorkerThread, "_atomic_pixmap_save", spy_atomic_pixmap_save)

    worker = WorkerThread(
        "convert_to_img",
        file_paths=[str(src)],
        output_dir=str(out_dir),
        fmt="png",
        dpi=72,
    )
    worker.convert_to_img()

    assert len(calls) == 1
    assert (out_dir / "src_p001.png").exists()
    assert not list(out_dir.glob(".pdf_master_*"))


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


def test_extract_text_routes_through_atomic_text_save(tmp_path, monkeypatch):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "src.txt"
    _make_pdf(src, "TEXT")

    calls = []
    original = WorkerThread._atomic_text_save

    def spy_atomic_text_save(self, output_path, text, *, encoding="utf-8", newline=None):
        calls.append((output_path, text))
        return original(self, output_path, text, encoding=encoding, newline=newline)

    monkeypatch.setattr(WorkerThread, "_atomic_text_save", spy_atomic_text_save)

    worker = WorkerThread(
        "extract_text",
        file_path=str(src),
        output_path=str(out),
    )
    worker.extract_text()

    assert len(calls) == 1
    assert calls[0][0] == str(out)
    assert "TEXT" in out.read_text(encoding="utf-8")
    assert worker.kwargs["created_output_paths"] == [str(out.resolve())]
