"""TextboxEditorSession + 큐 고스트 + extract_text_in_rect."""

from __future__ import annotations

from src.ui.tabs_advanced.textbox_session import TextboxEditorSession, ensure_textbox_session


def test_session_path_mismatch_and_commit_error():
    s = TextboxEditorSession()
    s.add_box({"file_path": "D:/a.pdf", "page_num": 0, "rect": [0, 0, 10, 10], "text": "x"})
    assert s.path_mismatch_with("D:/b.pdf") is True
    assert s.commit_path_error("D:/b.pdf") == "err_textbox_queue_path_mismatch"
    assert s.commit_path_error("D:/a.pdf") is None


def test_session_boxes_for_page():
    s = TextboxEditorSession()
    s.add_box({"file_path": "p.pdf", "page_num": 0, "rect": [1, 2, 3, 4], "text": "a"})
    s.add_box({"file_path": "p.pdf", "page_num": 1, "rect": [5, 6, 7, 8], "text": "b"})
    assert len(s.boxes_for_page(0)) == 1
    assert s.boxes_for_page(0)[0]["text"] == "a"


def test_ensure_session_absorbs_legacy_queue():
    class H:
        def __init__(self):
            self._textbox_queue = [{"file_path": "x.pdf", "page_num": 0, "rect": [0, 0, 1, 1], "text": "t"}]

    h = H()
    sess = ensure_textbox_session(h)
    assert len(sess.queue) == 1
    assert h._textbox_queue is sess.queue


def test_clear_post_flags_on_session():
    s = TextboxEditorSession(reopen_after_success=True, clear_queue_after_success=True)
    s.clear_post_flags()
    assert s.reopen_after_success is False
    assert s.clear_queue_after_success is False


def test_extract_text_in_rect_worker(tmp_path):
    from src.core.optional_deps import fitz
    from src.core.worker import WorkerThread

    if fitz is None or type(fitz.open).__name__ == "_MissingDependencyCallable":
        import pytest

        pytest.skip("PyMuPDF not available")

    src = tmp_path / "src.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "CLIPME", fontsize=14)
    doc.save(str(src))
    doc.close()

    worker = WorkerThread(
        "extract_text_in_rect",
        file_path=str(src),
        page_num=0,
        rect=[50, 50, 200, 100],
    )
    errors = []
    finished = []
    worker.error_signal.connect(lambda m: errors.append(m))
    worker.finished_signal.connect(lambda m: finished.append(m))
    worker.extract_text_in_rect()
    assert not errors, errors
    assert finished
    payload = getattr(worker, "result_payload", {}) or {}
    assert "CLIPME" in str(payload.get("text", ""))


def test_queue_ghost_overlay_set_items():
    from PyQt6.QtCore import QRect
    from PyQt6.QtWidgets import QApplication
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    from src.ui.preview_widget.queue_overlay import QueueGhostOverlay

    ov = QueueGhostOverlay()
    ov.set_items([(QRect(10, 10, 40, 20), "#1 hi")])
    assert ov.isVisible()
    assert len(ov._items) == 1
    ov.clear()
    assert not ov.isVisible()
    _ = app
