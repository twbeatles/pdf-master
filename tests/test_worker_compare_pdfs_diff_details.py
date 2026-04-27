from _deps import require_pyqt6_and_pymupdf
from src.core.optional_deps import fitz


def _make_text_pdf(path, lines):
    doc = fitz.open()
    page = doc.new_page(width=500, height=700)
    y = 72
    for line in lines:
        page.insert_text((72, y), line)
        y += 28
    doc.save(str(path))
    doc.close()


def test_compare_pdfs_detects_line_order_changes(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    out = tmp_path / "comparison.txt"
    _make_text_pdf(first, ["alpha", "beta"])
    _make_text_pdf(second, ["beta", "alpha"])

    worker = WorkerThread(
        "compare_pdfs",
        file_path1=str(first),
        file_path2=str(second),
        output_path=str(out),
    )
    errors = []
    worker.error_signal.connect(lambda msg: errors.append(msg))

    worker.compare_pdfs()

    assert not errors
    text = out.read_text(encoding="utf-8")
    assert "## 페이지 1" in text
    assert "alpha" in text
    assert "beta" in text
    assert any(marker in text for marker in ("- 추가:", "- 삭제:", "- 변경:"))
    assert worker.result_payload["diff_count"] == 1
    assert worker.result_payload["report_path"] == str(out)
    assert worker.result_payload["results"][0]["page"] == 1


def test_compare_pdfs_optional_visual_diff_and_duplicate_detection(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    first = tmp_path / "first_dup.pdf"
    second = tmp_path / "second_dup.pdf"
    out_no_visual = tmp_path / "comparison_no_visual.txt"
    out_visual = tmp_path / "comparison_visual.txt"
    _make_text_pdf(first, ["alpha", "alpha", "beta"])
    _make_text_pdf(second, ["alpha", "beta"])

    worker_no_visual = WorkerThread(
        "compare_pdfs",
        file_path1=str(first),
        file_path2=str(second),
        output_path=str(out_no_visual),
        generate_visual_diff=False,
    )
    worker_no_visual.compare_pdfs()
    assert not (tmp_path / "comparison_no_visual_visual_diff.pdf").exists()

    worker_visual = WorkerThread(
        "compare_pdfs",
        file_path1=str(first),
        file_path2=str(second),
        output_path=str(out_visual),
        generate_visual_diff=True,
    )
    worker_visual.compare_pdfs()

    text = out_visual.read_text(encoding="utf-8")
    visual_diff = tmp_path / "comparison_visual_visual_diff.pdf"
    assert "## 페이지 1" in text
    assert any(marker in text for marker in ("- 추가:", "- 삭제:", "- 변경:"))
    assert visual_diff.exists()
    assert worker_visual.result_payload["diff_count"] == 1
    assert worker_visual.result_payload["visual_diff_path"] == str(visual_diff)
    assert worker_visual.result_payload["results"][0]["status"] == "diff"

    diff_doc = fitz.open(str(visual_diff))
    assert len(diff_doc) == 1
    diff_doc.close()


def test_compare_pdfs_reuses_password_mapping_for_encrypted_inputs(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.path_utils import normalize_path_key
    from src.core.worker import WorkerThread

    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    first_locked = tmp_path / "first_locked.pdf"
    second_locked = tmp_path / "second_locked.pdf"
    out = tmp_path / "comparison.txt"
    _make_text_pdf(first, ["alpha"])
    _make_text_pdf(second, ["beta"])

    for src, locked in ((first, first_locked), (second, second_locked)):
        worker = WorkerThread("protect", file_path=str(src), output_path=str(locked), password="secret")
        worker.protect()

    worker = WorkerThread(
        "compare_pdfs",
        file_path1=str(first_locked),
        file_path2=str(second_locked),
        output_path=str(out),
        passwords={
            normalize_path_key(str(first_locked)): "secret",
            normalize_path_key(str(second_locked)): "secret",
        },
    )
    errors = []
    worker.error_signal.connect(lambda msg: errors.append(msg))
    worker.compare_pdfs()

    assert not errors
    assert out.exists()
    assert worker.result_payload["diff_count"] == 1
