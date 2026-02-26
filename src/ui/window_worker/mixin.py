from .lifecycle import (
    _cleanup_cancelled_worker,
    _finalize_worker,
    _on_progress_update,
    _on_worker_cancelled,
    _reset_progress_if_idle,
    _run_pending_worker,
    set_ui_busy,
)


class MainWindowWorkerMixin:
    _on_progress_update = _on_progress_update
    _on_worker_cancelled = _on_worker_cancelled
    _cleanup_cancelled_worker = _cleanup_cancelled_worker
    set_ui_busy = set_ui_busy
    _finalize_worker = _finalize_worker
    _run_pending_worker = _run_pending_worker
    _reset_progress_if_idle = _reset_progress_if_idle
