"""PROJECT_AUDIT 후속: blank-page 오판, visual_error, bookmarks 검증, queue 상한."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from _deps import require_pyqt6, require_pyqt6_and_pymupdf
from src.core.optional_deps import fitz


def test_is_blank_page_keeps_page_on_render_failure():
    require_pyqt6_and_pymupdf()
    from src.core.worker_ops import cleanup_ops

    page = MagicMock()
    page.get_text.return_value = ""
    page.get_images.return_value = []
    page.get_drawings.return_value = []
    page.get_pixmap.side_effect = RuntimeError("render boom")

    assert cleanup_ops._is_blank_page(page) is False


def test_compare_visual_error_not_silent(tmp_path, monkeypatch):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    left = tmp_path / "l.pdf"
    right = tmp_path / "r.pdf"
    for path in (left, right):
        doc = fitz.open()
        doc.new_page()
        doc.save(str(path))
        doc.close()

    report = tmp_path / "cmp.txt"
    worker = WorkerThread(
        "compare_pdfs",
        file_path1=str(left),
        file_path2=str(right),
        output_path=str(report),
        compare_mode="visual",
        generate_visual_diff=False,
    )

    # PyMuPDF Page 인스턴스 메서드 바인딩이 어려워 Matrix 생성 단계에서 실패 유도
    monkeypatch.setattr(
        fitz,
        "Matrix",
        MagicMock(side_effect=RuntimeError("pix fail")),
    )
    worker.compare_pdfs()

    payload = worker.result_payload
    assert int(payload.get("visual_error_count") or 0) >= 1
    statuses = [r.get("status") for r in payload.get("results", [])]
    assert "visual_error" in statuses
    text = report.read_text(encoding="utf-8")
    assert "visual_error" in text.lower() or "오류" in text or "error" in text.lower()


def test_set_bookmarks_rejects_invalid_structure(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "src.pdf"
    out = tmp_path / "out.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(str(src))
    doc.close()

    worker = WorkerThread(
        "set_bookmarks",
        file_path=str(src),
        output_path=str(out),
        bookmarks=[["bad"]],
    )
    errors: list[str] = []
    worker.error_signal.connect(lambda m: errors.append(m))
    worker.set_bookmarks()
    assert errors
    assert not out.exists()


def test_pending_worker_queue_cap(monkeypatch):
    require_pyqt6()
    import src.ui.window_worker.lifecycle as life

    class Host:
        def __init__(self):
            self._pending_workers = []
            self.toasts = []

    host = Host()

    class _Toast:
        def __init__(self, *a, **k):
            host.toasts.append((a, k))

        def show_toast(self, *_a, **_k):
            return None

    monkeypatch.setattr(life, "ToastWidget", _Toast)

    for i in range(life._MAX_PENDING_WORKERS):
        assert life._enqueue_pending_worker(host, f"mode_{i}") is True
    assert life._enqueue_pending_worker(host, "overflow") is False
    assert len(host._pending_workers) == life._MAX_PENDING_WORKERS
