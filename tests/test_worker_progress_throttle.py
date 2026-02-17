import pytest


def _skip_if_missing_deps():
    try:
        import PyQt6  # noqa: F401
        import fitz  # noqa: F401
    except Exception:
        pytest.skip("PyQt6 or PyMuPDF not available")


def test_emit_progress_if_due_throttles():
    _skip_if_missing_deps()
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
