from pathlib import Path

from _deps import require_pyqt6_and_pymupdf
from src.core.optional_deps import fitz


def _make_pdf(path, page_texts):
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page(width=300, height=400)
        page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


def test_metadata_update_writes_updated_title(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "meta.pdf"
    _make_pdf(src, ["PAGE_1"])

    worker = WorkerThread(
        "metadata_update",
        file_path=str(src),
        output_path=str(out),
        metadata={"title": "Updated Title"},
    )
    worker.metadata_update()

    doc = fitz.open(str(out))
    try:
        assert doc.metadata.get("title") == "Updated Title"
    finally:
        doc.close()


def test_protect_and_decrypt_roundtrip(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    encrypted = tmp_path / "encrypted.pdf"
    decrypted = tmp_path / "decrypted.pdf"
    _make_pdf(src, ["PAGE_1"])

    protect_worker = WorkerThread(
        "protect",
        file_path=str(src),
        output_path=str(encrypted),
        password="secret",
    )
    protect_worker.protect()

    encrypted_doc = fitz.open(str(encrypted))
    try:
        assert encrypted_doc.is_encrypted
    finally:
        encrypted_doc.close()

    decrypt_worker = WorkerThread(
        "decrypt_pdf",
        file_path=str(encrypted),
        output_path=str(decrypted),
        password="secret",
    )
    decrypt_worker.decrypt_pdf()

    decrypted_doc = fitz.open(str(decrypted))
    try:
        assert not decrypted_doc.is_encrypted
        assert "PAGE_1" in decrypted_doc[0].get_text()
    finally:
        decrypted_doc.close()


def test_worker_uses_password_mapping_for_encrypted_input(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.path_utils import normalize_path_key
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    encrypted = tmp_path / "encrypted.pdf"
    rotated = tmp_path / "rotated.pdf"
    _make_pdf(src, ["PAGE_1"])

    protect_worker = WorkerThread(
        "protect",
        file_path=str(src),
        output_path=str(encrypted),
        password="secret",
    )
    protect_worker.protect()

    rotate_worker = WorkerThread(
        "rotate",
        file_path=str(encrypted),
        output_path=str(rotated),
        angle=90,
        passwords={normalize_path_key(str(encrypted)): "secret"},
    )
    errors = []
    rotate_worker.error_signal.connect(lambda msg: errors.append(msg))
    rotate_worker.rotate()

    assert not errors
    assert rotated.exists()


def test_reorder_rewrites_page_order(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "reordered.pdf"
    _make_pdf(src, ["ONE", "TWO", "THREE"])

    worker = WorkerThread(
        "reorder",
        file_path=str(src),
        output_path=str(out),
        page_order=[2, 0, 1],
    )
    worker.reorder()

    doc = fitz.open(str(out))
    try:
        assert [doc[i].get_text().strip() for i in range(len(doc))] == ["THREE", "ONE", "TWO"]
    finally:
        doc.close()


def test_split_by_pages_writes_individual_outputs(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out_dir = tmp_path / "split"
    out_dir.mkdir()
    _make_pdf(src, ["ONE", "TWO"])

    worker = WorkerThread(
        "split_by_pages",
        file_path=str(src),
        output_dir=str(out_dir),
        split_mode="each",
    )
    worker.split_by_pages()

    outputs = sorted(path.name for path in out_dir.glob("*.pdf"))
    assert outputs == ["src_page_1.pdf", "src_page_2.pdf"]


def test_split_by_pages_worker_run_uses_current_ui_contract(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out_dir = tmp_path / "split_run"
    out_dir.mkdir()
    _make_pdf(src, ["ONE", "TWO"])

    worker = WorkerThread(
        "split_by_pages",
        file_path=str(src),
        output_dir=str(out_dir),
        split_mode="each",
    )
    errors = []
    finished = []
    worker.error_signal.connect(lambda msg: errors.append(msg))
    worker.finished_signal.connect(lambda msg: finished.append(msg))

    worker.run()

    outputs = sorted(path.name for path in out_dir.glob("*.pdf"))
    assert not errors
    assert finished
    assert outputs == ["src_page_1.pdf", "src_page_2.pdf"]


def test_extract_markdown_writes_page_markers(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.md"
    _make_pdf(src, ["ALPHA", "BETA"])

    worker = WorkerThread(
        "extract_markdown",
        file_path=str(src),
        output_path=str(out),
    )
    worker.extract_markdown()

    markdown = out.read_text(encoding="utf-8")
    assert "# src.pdf" in markdown
    assert "## Page 1" in markdown
    assert "ALPHA" in markdown
    assert "## Page 2" in markdown
    assert "BETA" in markdown


def test_extract_markdown_honors_front_matter_and_marker_options(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.md"
    _make_pdf(src, ["ALPHA"])

    worker = WorkerThread(
        "extract_markdown",
        file_path=str(src),
        output_path=str(out),
        markdown_mode="text",
        include_front_matter=True,
        include_page_markers=False,
    )
    worker.extract_markdown()

    markdown = out.read_text(encoding="utf-8")
    assert markdown.startswith("---\n")
    assert 'file_name: "src.pdf"' in markdown
    assert "## Page" not in markdown
    assert "ALPHA" in markdown


def test_batch_compress_uses_default_save_profile(tmp_path, monkeypatch):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread
    from src.core.worker_runtime.save_profiles import DEFAULT_COMPRESSION_SAVE_PROFILE

    src = tmp_path / "src.pdf"
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    _make_pdf(src, ["PAGE_1"])

    save_calls = []

    def fake_atomic_save(self, doc, output_path, **kwargs):
        save_calls.append(kwargs.copy())
        doc.save(output_path)

    monkeypatch.setattr(WorkerThread, "_atomic_pdf_save", fake_atomic_save)

    worker = WorkerThread(
        "batch",
        files=[str(src)],
        output_dir=str(out_dir),
        operation="compress",
    )
    worker.batch()

    assert save_calls
    assert save_calls[0]["save_profile"] == DEFAULT_COMPRESSION_SAVE_PROFILE
    assert "garbage" not in save_calls[0]
    assert "deflate" not in save_calls[0]
