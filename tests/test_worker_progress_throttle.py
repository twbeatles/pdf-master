import pytest

from _deps import require_pyqt6


def test_emit_progress_if_due_throttles():
    require_pyqt6()
    from src.core.worker import WorkerThread

    worker = WorkerThread("merge")
    emitted = []
    worker.progress_signal.connect(lambda value: emitted.append(value))

    for value in range(0, 101):
        worker._emit_progress_if_due(value, min_step=10, min_interval_ms=10_000)

    assert emitted
    assert emitted[0] == 0
    assert emitted[-1] == 100
    assert len(emitted) <= 11
