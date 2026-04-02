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
