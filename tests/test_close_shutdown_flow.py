from _deps import require_pyqt6


def test_shutdown_worker_for_close_waits_without_force_when_worker_stops():
    require_pyqt6()
    from src.ui.main_window import _shutdown_worker_for_close

    class Worker:
        def __init__(self):
            self.cancel_calls = 0
            self.wait_calls = []
            self.terminate_calls = 0

        def isRunning(self):
            return True

        def cancel(self):
            self.cancel_calls += 1

        def wait(self, timeout):
            self.wait_calls.append(timeout)
            return True

        def terminate(self):
            self.terminate_calls += 1

    worker = Worker()

    assert _shutdown_worker_for_close(parent=None, worker=worker) is True
    assert worker.cancel_calls == 1
    assert worker.wait_calls == [3000]
    assert worker.terminate_calls == 0


def test_shutdown_worker_for_close_requires_user_confirmation_before_terminate(monkeypatch):
    require_pyqt6()
    import src.ui.main_window as main_window_module

    class Worker:
        def __init__(self):
            self.cancel_calls = 0
            self.wait_calls = []
            self.terminate_calls = 0

        def isRunning(self):
            return True

        def cancel(self):
            self.cancel_calls += 1

        def wait(self, timeout):
            self.wait_calls.append(timeout)
            return timeout == 1000

        def terminate(self):
            self.terminate_calls += 1

    worker = Worker()

    monkeypatch.setattr(
        main_window_module.QMessageBox,
        "warning",
        lambda *_args, **_kwargs: main_window_module.QMessageBox.StandardButton.Cancel,
    )
    assert main_window_module._shutdown_worker_for_close(parent=None, worker=worker) is False
    assert worker.terminate_calls == 0

    monkeypatch.setattr(
        main_window_module.QMessageBox,
        "warning",
        lambda *_args, **_kwargs: main_window_module.QMessageBox.StandardButton.Close,
    )
    assert main_window_module._shutdown_worker_for_close(parent=None, worker=worker) is True
    assert worker.terminate_calls == 1
    assert worker.wait_calls[-1] == 1000
