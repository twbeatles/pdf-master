import pytest

from _deps import require_pyqt6


def test_cancel_sets_cancelled_error():
    require_pyqt6()
    from src.core.worker import WorkerThread, CancelledError

    w = WorkerThread("merge")
    w.cancel()
    with pytest.raises(CancelledError):
        w._check_cancelled()
