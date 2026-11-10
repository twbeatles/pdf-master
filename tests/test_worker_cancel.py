import pytest
from _deps import require_pyside6


def test_cancel_sets_cancelled_error():
    require_pyside6()
    from src.core.worker import CancelledError, WorkerThread

    w = WorkerThread("merge")
    w.cancel()
    with pytest.raises(CancelledError):
        w._check_cancelled()
