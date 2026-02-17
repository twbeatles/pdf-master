import pytest


def _skip_if_missing_deps():
    try:
        import PyQt6  # noqa: F401
        import fitz  # noqa: F401
    except Exception:
        pytest.skip("PyQt6 or PyMuPDF not available")


def test_cancel_sets_cancelled_error():
    _skip_if_missing_deps()
    from src.core.worker import WorkerThread, CancelledError

    w = WorkerThread("merge")
    w.cancel()
    with pytest.raises(CancelledError):
        w._check_cancelled()
