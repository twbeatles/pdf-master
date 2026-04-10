import os

from _deps import require_pyqt6_and_pymupdf
from src.core.optional_deps import fitz


def _make_pdf(path, page_count=2):
    doc = fitz.open()
    for index in range(page_count):
        page = doc.new_page(width=300, height=400)
        page.insert_text((72, 72), f"PAGE_{index + 1}")
    doc.save(str(path))
    doc.close()


def test_same_path_output_closes_and_restores_preview(tmp_path):
    require_pyqt6_and_pymupdf()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from src.core.worker import WorkerThread
    from src.ui.main_window_worker import MainWindowWorkerMixin

    src_pdf = tmp_path / "same.pdf"
    _make_pdf(src_pdf, page_count=3)

    class Dummy(MainWindowWorkerMixin):
        def __init__(self, path):
            self._current_preview_path = str(path)
            self._current_preview_doc = fitz.open(str(path))
            self._current_preview_page = 1
            self._current_preview_password = None
            self._preview_password_hint = None
            self._same_path_preview_restore = None
            self._preview_total_pages = len(self._current_preview_doc)
            self.rendered_pages = []
            self.reopened_paths = []

        def _close_preview_document(self):
            if self._current_preview_doc is not None:
                self._current_preview_doc.close()
            self._current_preview_doc = None

        def _update_preview(self, path):
            self.reopened_paths.append(path)
            self._current_preview_doc = fitz.open(path)
            self._current_preview_path = path
            self._preview_total_pages = len(self._current_preview_doc)
            self._current_preview_page = 0

        def _render_preview_page(self):
            self.rendered_pages.append(self._current_preview_page)

    dummy = Dummy(src_pdf)

    dummy._prepare_preview_for_same_path_output(
        "metadata_update",
        {"file_path": str(src_pdf), "output_path": str(src_pdf)},
    )

    assert dummy._current_preview_doc is None
    assert dummy._same_path_preview_restore is not None

    worker = WorkerThread(
        "metadata_update",
        file_path=str(src_pdf),
        output_path=str(src_pdf),
        metadata={"title": "Updated Title"},
    )
    worker.metadata_update()

    dummy._restore_preview_after_same_path_output()

    assert dummy.reopened_paths == [str(src_pdf)]
    assert dummy.rendered_pages == [1]
    assert dummy._current_preview_page == 1
    assert dummy._current_preview_doc is not None
    assert dummy._current_preview_doc.metadata.get("title") == "Updated Title"
