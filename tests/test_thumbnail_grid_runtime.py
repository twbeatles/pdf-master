import os
from typing import Any, cast

from _deps import require_pyqt6_and_pymupdf
from src.core.optional_deps import fitz


def _make_pdf(path, page_count=1):
    doc = fitz.open()
    for index in range(page_count):
        page = doc.new_page(width=300, height=400)
        page.insert_text((72, 72), f"PAGE_{index + 1}")
    doc.save(str(path))
    doc.close()


def _make_encrypted_pdf(path, password="secret", page_count=1):
    doc = fitz.open()
    for index in range(page_count):
        page = doc.new_page(width=300, height=400)
        page.insert_text((72, 72), f"PAGE_{index + 1}")
    doc.save(
        str(path),
        encryption=fitz.PDF_ENCRYPT_AES_256,
        owner_pw=password,
        user_pw=password,
    )
    doc.close()


def test_thumbnail_grid_load_pdf_shows_encrypted_message_without_password(tmp_path):
    require_pyqt6_and_pymupdf()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication
    from src.core.i18n import tm
    from src.ui.thumbnail_grid import ThumbnailGridWidget

    app = QApplication.instance() or QApplication([])
    _ = app

    src_pdf = tmp_path / "locked.pdf"
    _make_encrypted_pdf(src_pdf)

    grid = ThumbnailGridWidget()
    try:
        grid.load_pdf(str(src_pdf))
        assert grid.loading_label.text() == tm.get("preview_encrypted")
        assert grid.get_selected_pages() == []
    finally:
        grid.close()


def test_thumbnail_loader_emits_loading_complete_once_without_password(tmp_path):
    require_pyqt6_and_pymupdf()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication
    from src.ui.thumbnail_grid import ThumbnailLoaderThread

    app = QApplication.instance() or QApplication([])
    _ = app

    src_pdf = tmp_path / "locked.pdf"
    _make_encrypted_pdf(src_pdf)

    calls = {"complete": 0, "ready": 0}
    loader = ThumbnailLoaderThread(str(src_pdf), [0])
    loader.loading_complete.connect(lambda: calls.__setitem__("complete", calls["complete"] + 1))
    loader.thumbnail_ready.connect(lambda *_args: calls.__setitem__("ready", calls["ready"] + 1))

    loader.run()

    assert calls == {"complete": 1, "ready": 0}


def test_thumbnail_loader_emits_loading_complete_once_with_password(tmp_path):
    require_pyqt6_and_pymupdf()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication
    from src.ui.thumbnail_grid import ThumbnailLoaderThread

    app = QApplication.instance() or QApplication([])
    _ = app

    src_pdf = tmp_path / "locked.pdf"
    _make_encrypted_pdf(src_pdf, page_count=2)

    calls = {"complete": 0, "ready": []}
    loader = ThumbnailLoaderThread(str(src_pdf), [0, 1], password="secret")
    loader.loading_complete.connect(lambda: calls.__setitem__("complete", calls["complete"] + 1))
    loader.thumbnail_ready.connect(lambda page_index, _pixmap: calls["ready"].append(page_index))

    loader.run()

    assert calls["complete"] == 1
    assert calls["ready"] == [0, 1]


def test_cleanup_loader_thread_does_not_force_terminate(tmp_path):
    require_pyqt6_and_pymupdf()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtWidgets import QApplication
    from src.ui.thumbnail_grid import ThumbnailGridWidget

    app = QApplication.instance() or QApplication([])
    _ = app

    class _DisconnectStub:
        def disconnect(self, *_args, **_kwargs):
            return None

    class _FinishedStub:
        def __init__(self):
            self.connected = []

        def connect(self, callback):
            self.connected.append(callback)

    class FakeThread:
        def __init__(self):
            self.thumbnail_ready = _DisconnectStub()
            self.progress = _DisconnectStub()
            self.loading_complete = _DisconnectStub()
            self.finished = _FinishedStub()
            self.cancel_calls = 0
            self.wait_calls = []
            self.terminate_calls = 0

        def isRunning(self):
            return True

        def cancel(self):
            self.cancel_calls += 1

        def wait(self, timeout):
            self.wait_calls.append(timeout)
            return False

        def terminate(self):
            self.terminate_calls += 1

        def deleteLater(self):
            return None

    grid = ThumbnailGridWidget()
    fake = FakeThread()
    try:
        grid._loader_thread = cast(Any, fake)
        grid._active_batch_indices = [0]
        grid._requested_indices = {0}
        grid._pending_indices = set()

        grid._cleanup_loader_thread()

        assert grid._loader_thread is None
        assert grid._pending_indices == {0}
        assert grid._requested_indices == set()
        assert grid._active_batch_indices == []
        assert fake.cancel_calls == 1
        assert fake.terminate_calls == 0
    finally:
        grid.close()
