import pytest

from _deps import require_pyqt6_and_pymupdf
from src.core.optional_deps import fitz


def _make_pdf(path):
    doc = fitz.open()
    doc.new_page(width=400, height=400)
    doc.save(str(path))
    doc.close()


def _make_pdf_with_attachment(path):
    doc = fitz.open()
    doc.new_page(width=400, height=400)
    doc.embfile_add("sample.txt", b"hello-attachment")
    doc.save(str(path))
    doc.close()


def test_get_form_fields_sets_result_payload(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "plain.pdf"
    _make_pdf(src)

    worker = WorkerThread("get_form_fields", file_path=str(src))
    worker.get_form_fields()

    assert "result_fields" in worker.kwargs
    assert isinstance(worker.kwargs["result_fields"], list)
    assert isinstance(worker.result_payload.get("fields"), list)


def test_list_attachments_sets_result_payload(tmp_path):
    require_pyqt6_and_pymupdf()
    from src.core.worker import WorkerThread

    src = tmp_path / "with_attach.pdf"
    _make_pdf_with_attachment(src)

    worker = WorkerThread("list_attachments", file_path=str(src))
    worker.list_attachments()

    payload = worker.kwargs.get("result_attachments")
    assert isinstance(payload, list)
    assert len(payload) == 1
    assert payload[0]["name"] == "sample.txt"
    assert isinstance(worker.result_payload.get("attachments"), list)


def test_worker_on_success_consumes_form_fields_payload(monkeypatch):
    require_pyqt6_and_pymupdf()
    from src.ui.main_window_worker import MainWindowWorkerMixin
    import src.ui.main_window_worker as worker_ui_module

    infos = []

    class DummyLabel:
        def setText(self, *_args, **_kwargs):
            return None

    class DummyProgressBar:
        def setValue(self, *_args, **_kwargs):
            return None

    class DummyButton:
        def setVisible(self, *_args, **_kwargs):
            return None

        def setEnabled(self, *_args, **_kwargs):
            return None

    class DummyOverlay:
        def hide_progress(self):
            return None

    class DummyList:
        def __init__(self):
            self.items = []

        def clear(self):
            self.items = []

        def count(self):
            return len(self.items)

        def addItem(self, item):
            self.items.append(item)

    class DummyWorker:
        def __init__(self):
            self.mode = "get_form_fields"
            self.result_payload = {
                "fields": [
                    {
                        "name": "customer_name",
                        "value": "Alice",
                        "type": "Text",
                        "page": 1,
                    }
                ]
            }
            self.kwargs = {
                "result_fields": [
                    {
                        "name": "customer_name",
                        "value": "Alice",
                        "type": "Text",
                        "page": 1,
                    }
                ]
            }

        def isRunning(self):
            return False

    class Dummy(MainWindowWorkerMixin):
        def __init__(self):
            self.worker = DummyWorker()
            self._last_output_path = None
            self._has_output = False
            self.status_label = DummyLabel()
            self.progress_bar = DummyProgressBar()
            self.btn_open_folder = DummyButton()
            self.progress_overlay = DummyOverlay()
            self.form_fields_list = DummyList()
            self._form_field_data = {}

        def sender(self):
            return None

        def set_ui_busy(self, *_args, **_kwargs):
            return None

        def _finalize_worker(self):
            return None

        def _run_pending_worker(self):
            return None

    class DummyToast:
        def __init__(self, *_args, **_kwargs):
            pass

        def show_toast(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(worker_ui_module, "ToastWidget", DummyToast)
    monkeypatch.setattr(
        worker_ui_module.QMessageBox,
        "information",
        lambda *_args, **_kwargs: infos.append((_args, _kwargs)),
    )
    monkeypatch.setattr(worker_ui_module.QTimer, "singleShot", lambda *_args, **_kwargs: None)

    dummy = Dummy()
    dummy.on_success("done")

    assert dummy._form_field_data.get("customer_name") == "Alice"
    assert dummy.form_fields_list.count() == 1

