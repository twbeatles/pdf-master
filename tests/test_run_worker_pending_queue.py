import pytest

from _deps import require_pyqt6


class _SignalStub:
    def connect(self, *_args, **_kwargs):
        return None


class _RunningWorkerStub:
    def __init__(self, mode, **kwargs):
        self.mode = mode
        self.kwargs = kwargs
        self.progress_signal = _SignalStub()
        self.finished_signal = _SignalStub()
        self.error_signal = _SignalStub()
        self.cancelled_signal = _SignalStub()

    def start(self):
        return None

    def isRunning(self):
        return True

    def wait(self, _timeout):
        return False


def test_run_worker_queues_multiple_pending_requests(monkeypatch):
    require_pyqt6()
    import src.ui.main_window_worker as worker_module

    class _ToastStub:
        def __init__(self, *_args, **_kwargs):
            pass

        def show_toast(self, *_args, **_kwargs):
            return None

    class _ButtonStub:
        def setEnabled(self, _enabled):
            return None

    class _LabelStub:
        def setText(self, _text):
            return None

    class _ProgressBarStub:
        def setValue(self, _value):
            return None

    class _OverlayStub:
        def show_progress(self, *_args, **_kwargs):
            return None

        def hide_progress(self):
            return None

    class Dummy(worker_module.MainWindowWorkerMixin):
        def __init__(self):
            self.worker = _RunningWorkerStub("rotate", file_path="a.pdf", output_path="out.pdf")
            self._pending_workers = []
            self._cancel_pending = False
            self._cancel_handled = False
            self._pending_undo = None
            self.progress_bar = _ProgressBarStub()
            self.btn_open_folder = _ButtonStub()
            self.status_label = _LabelStub()
            self.progress_overlay = _OverlayStub()
            self.queued_calls = []

        def set_ui_busy(self, _busy):
            return None

        def _prepare_preview_for_same_path_output(self, *_args, **_kwargs):
            return None

        def _augment_worker_passwords_from_preview(self, *_args, **_kwargs):
            return None

        def _finalize_worker(self):
            return None

        def _run_pending_worker(self):
            return None

    monkeypatch.setattr(worker_module, "ToastWidget", _ToastStub)
    monkeypatch.setattr(worker_module.QMessageBox, "question", lambda *_args, **_kwargs: worker_module.QMessageBox.StandardButton.Yes)

    dummy = Dummy()
    dummy.run_worker("merge", file_paths=["a.pdf", "b.pdf"], output_path="merged.pdf")
    dummy.run_worker("compress", file_path="a.pdf", output_path="compressed.pdf")

    assert len(dummy._pending_workers) == 2
    assert dummy._pending_workers[0]["mode"] == "merge"
    assert dummy._pending_workers[1]["mode"] == "compress"


def test_run_pending_worker_pops_fifo_order(monkeypatch):
    require_pyqt6()
    from src.ui.window_worker import lifecycle as lifecycle_module

    calls = []

    class Dummy:
        worker = None
        _pending_workers = [
            {"mode": "merge", "output_path": "merged.pdf", "kwargs": {"file_paths": ["a.pdf"]}},
            {"mode": "compress", "output_path": "out.pdf", "kwargs": {"file_path": "a.pdf"}},
        ]

        def run_worker(self, mode, output_path=None, **kwargs):
            calls.append((mode, output_path, kwargs))

    monkeypatch.setattr(lifecycle_module.QTimer, "singleShot", lambda _delay, callback: callback())

    lifecycle_module._run_pending_worker(Dummy())

    assert len(calls) == 1
    assert calls[0][0] == "merge"
    assert len(Dummy._pending_workers) == 1
    assert Dummy._pending_workers[0]["mode"] == "compress"