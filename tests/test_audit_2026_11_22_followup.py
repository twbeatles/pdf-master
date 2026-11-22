"""2026-11-22 One-Shot 감사 후속 회귀 테스트 (ISSUE-001~006)."""

from __future__ import annotations

from _deps import require_pyside6_and_pymupdf


def _make_image(tmp_path):
    require_pyside6_and_pymupdf()
    from src.core.optional_deps import fitz

    doc = fitz.open()
    doc.new_page(width=100, height=100)
    pix = doc[0].get_pixmap()
    img = tmp_path / "sample.png"
    pix.save(str(img))
    doc.close()
    return img


def _make_text_pdf(path, texts):
    require_pyside6_and_pymupdf()
    from src.core.optional_deps import fitz

    doc = fitz.open()
    for text in texts:
        page = doc.new_page(width=300, height=300)
        page.insert_text((40, 100), text)
    doc.save(str(path))
    doc.close()


def test_images_to_pdf_rejects_missing_files_key(tmp_path):
    require_pyside6_and_pymupdf()
    from src.core.worker import WorkerThread

    out = tmp_path / "out.pdf"
    worker = WorkerThread("images_to_pdf", output_path=str(out))
    errors: list[str] = []
    finished: list[str] = []
    worker.error_signal.connect(errors.append)
    worker.finished_signal.connect(finished.append)
    worker.run()
    assert errors and not finished
    assert not out.exists()


def test_images_to_pdf_rejects_missing_output_path(tmp_path):
    require_pyside6_and_pymupdf()
    from src.core.worker import WorkerThread

    img = _make_image(tmp_path)
    worker = WorkerThread("images_to_pdf", files=[str(img)])
    errors: list[str] = []
    finished: list[str] = []
    worker.error_signal.connect(errors.append)
    worker.finished_signal.connect(finished.append)
    worker.run()
    assert errors and not finished


def test_compare_text_extraction_failure_isolated_per_page(tmp_path, monkeypatch):
    require_pyside6_and_pymupdf()
    from src.core.optional_deps import fitz
    from src.core.worker import WorkerThread

    left = tmp_path / "l.pdf"
    right = tmp_path / "r.pdf"
    _make_text_pdf(left, ["alpha one", "alpha two"])
    _make_text_pdf(right, ["alpha one", "BETA two"])
    report = tmp_path / "cmp.txt"
    worker = WorkerThread(
        "compare_pdfs",
        file_path1=str(left),
        file_path2=str(right),
        output_path=str(report),
        compare_mode="text",
    )
    monkeypatch.setattr(
        fitz.Page,
        "get_text",
        lambda self, *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("text boom")
        ),
    )
    finished: list[str] = []
    errors: list[str] = []
    worker.finished_signal.connect(finished.append)
    worker.error_signal.connect(errors.append)
    worker.compare_pdfs()
    assert finished and not errors
    payload = worker.result_payload
    assert int(payload.get("text_error_count") or 0) == 2
    assert {r.get("status") for r in payload.get("results", [])} == {"text_error"}
    text = report.read_text(encoding="utf-8")
    assert "text_error" in text


def test_compare_diff_block_failure_isolated_per_page(tmp_path, monkeypatch):
    require_pyside6_and_pymupdf()
    from src.core.worker import WorkerThread
    from src.core.worker_ops.compare.ops import WorkerCompareOpsMixin

    left = tmp_path / "l.pdf"
    right = tmp_path / "r.pdf"
    _make_text_pdf(left, ["same line"])
    _make_text_pdf(right, ["different line"])
    report = tmp_path / "cmp.txt"
    worker = WorkerThread(
        "compare_pdfs",
        file_path1=str(left),
        file_path2=str(right),
        output_path=str(report),
        compare_mode="text",
    )

    def _boom(self, page1, page2):
        raise RuntimeError("blocks boom")

    monkeypatch.setattr(WorkerCompareOpsMixin, "_collect_page_diff_blocks", _boom)
    finished: list[str] = []
    errors: list[str] = []
    worker.finished_signal.connect(finished.append)
    worker.error_signal.connect(errors.append)
    worker.compare_pdfs()
    assert finished and not errors
    payload = worker.result_payload
    assert int(payload.get("text_error_count") or 0) >= 1
    assert report.exists()
